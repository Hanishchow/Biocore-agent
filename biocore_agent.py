#!/usr/bin/env python3
"""
BioCore External Agent
======================
Runs locally. Called by n8n via ngrok tunnel.
Fetches data from PubChem + RCSB PDB, then runs the
7-step BioCore analysis using the NVIDIA API.

Usage:
  1. Copy .env.example → .env and fill in your NVIDIA_API_KEY
  2. pip install -r requirements.txt
  3. python biocore_agent.py
  4. In a separate terminal: ngrok http 5000
  5. Paste the ngrok URL into the n8n bridge workflow
"""

import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ── Config (loaded from .env) ─────────────────────────────────
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_MODEL   = os.environ.get("NVIDIA_MODEL", "NVIDIABuild-Autogen-12")
NVIDIA_URL     = "https://integrate.api.nvidia.com/v1/chat/completions"
PORT           = int(os.environ.get("PORT", 5000))

if not NVIDIA_API_KEY:
    print("⚠️  WARNING: NVIDIA_API_KEY not set. Copy .env.example → .env and add your key.")

# ── BioCore System Prompt ─────────────────────────────────────
SYSTEM_PROMPT = """You are BioCore, a specialized biochemistry and biophysics AI agent. Execute the full 7-step analysis protocol on every payload.

STEP 1 - COMPOUND PROFILING: Extract IUPAC name, CID, molecular formula, MW, exact mass, SMILES, InChI, XLogP3, TPSA, HBD/HBA counts, rotatable bonds, heavy atom count, formal charge. Evaluate Lipinski Ro5, Veber rules, Ghose filter. Identify functional groups. Predict solubility class. Flag ADMET concerns.

STEP 2 - PROTEIN TARGET PROFILING: Extract PDB ID, protein name, organism, resolution in Angstroms, experimental method, R-free. Classify resolution quality. Identify protein family. Note UniProt IDs and disease associations. Flag co-crystallized ligands.

STEP 3 - DOCKING RESULT ANALYSIS: For each pose report affinity in kcal/mol, rank, RMSD. Classify: below -10 very strong, -7 to -10 strong, -5 to -7 moderate, above -5 weak. Compute Kd via deltaG = RT ln(Kd). Predict interaction types.

STEP 4 - INTERACTION MECHANISM: Describe bonding events, conformational changes, reversible vs covalent binding, functional effect. Model thermodynamic landscape. Predict pH and ionic strength effects. Reason about kon and koff.

STEP 5 - THEORETICAL TO PRACTICAL BRIDGE: Estimate IC50 from Kd. Predict cell permeability from TPSA and logP. Flag CYP450 liabilities. Recommend validation technique. Flag off-target concerns.

STEP 6 - PYMOL VISUALIZATION: Provide exact PyMOL commands. Surface representation, residue labels, color scheme: receptor grey cartoon, ligand element-colored sticks, H-bonds yellow dashes. Distance measurement commands.

STEP 7 - SYNTHESIS REPORT with mandatory sections:
[COMPOUND SUMMARY] [TARGET SUMMARY] [DOCKING VERDICT] [MECHANISTIC ANALYSIS] [THEORETICAL TO PRACTICAL TRANSLATION] [LIMITATIONS AND CAVEATS] [RECOMMENDED NEXT STEPS]

Rules: Never hallucinate data not in the payload. Always cite the biochemical principle behind each conclusion. Quantify everything with delta-G, Kd, IC50, RMSD, distances in Angstroms. Flag uncertainty. Use markdown headers, tables, code blocks, bold for critical values. Begin STEP 1 immediately with no preamble."""


# ── PubChem ───────────────────────────────────────────────────
def fetch_pubchem(compound_name=None, cid=None):
    """Fetch compound data from PubChem PUG REST API."""
    try:
        props = (
            "IUPACName,MolecularFormula,MolecularWeight,ExactMass,"
            "CanonicalSMILES,InChI,InChIKey,XLogP,TPSA,"
            "HBondDonorCount,HBondAcceptorCount,RotatableBondCount,"
            "HeavyAtomCount,Charge,Complexity"
        )
        if cid:
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/{props}/JSON"
        else:
            encoded = requests.utils.quote(compound_name)
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded}/property/{props}/JSON"

        res = requests.get(url, timeout=15)
        raw = res.json()

        if "PropertyTable" not in raw or not raw["PropertyTable"]["Properties"]:
            return {"_error": f"PubChem returned no results for: {compound_name or cid}"}

        p = raw["PropertyTable"]["Properties"][0]
        return {
            "cid":               p.get("CID"),
            "iupac_name":        p.get("IUPACName", "N/A"),
            "molecular_formula": p.get("MolecularFormula", "N/A"),
            "molecular_weight":  p.get("MolecularWeight"),
            "exact_mass":        p.get("ExactMass"),
            "canonical_smiles":  p.get("CanonicalSMILES", "N/A"),
            "inchi":             p.get("InChI", "N/A"),
            "inchikey":          p.get("InChIKey", "N/A"),
            "xlogp3":            p.get("XLogP"),
            "tpsa":              p.get("TPSA"),
            "hb_donors":         p.get("HBondDonorCount"),
            "hb_acceptors":      p.get("HBondAcceptorCount"),
            "rotatable_bonds":   p.get("RotatableBondCount"),
            "heavy_atoms":       p.get("HeavyAtomCount"),
            "charge":            p.get("Charge"),
            "complexity":        p.get("Complexity"),
        }
    except Exception as e:
        return {"_error": f"PubChem fetch failed: {str(e)}"}


# ── RCSB PDB ──────────────────────────────────────────────────
def fetch_pdb(pdb_id):
    """Fetch protein structure data from RCSB PDB REST API."""
    try:
        entry_url  = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
        entity_url = f"https://data.rcsb.org/rest/v1/core/polymer_entity/{pdb_id}/1"

        entry_res  = requests.get(entry_url,  timeout=15)
        entity_res = requests.get(entity_url, timeout=15)
        entry  = entry_res.json()
        entity = entity_res.json() if entity_res.status_code == 200 else {}

        if "struct" not in entry:
            return {"_error": f"No PDB data found for ID: {pdb_id}"}

        info    = entry.get("rcsb_entry_info", {})
        exptl   = (entry.get("exptl") or [{}])[0]
        refine  = (entry.get("refine") or [{}])[0]
        struct  = entry.get("struct", {})
        rcsb_e  = entity.get("rcsb_polymer_entity", {})
        e_ids   = entity.get("rcsb_entity_container_identifiers", {})

        res_list   = info.get("resolution_combined", [])
        resolution = res_list[0] if res_list else refine.get("ls_d_res_high")

        if resolution is None:        quality = "unknown"
        elif resolution < 2.0:        quality = "excellent (< 2.0 Å)"
        elif resolution < 2.5:        quality = "good (2.0–2.5 Å)"
        elif resolution < 3.0:        quality = "moderate (2.5–3.0 Å)"
        else:                         quality = "limited (> 3.0 Å)"

        return {
            "pdb_id":              pdb_id,
            "title":               struct.get("title", "N/A"),
            "protein_name":        rcsb_e.get("pdbx_description", struct.get("title", "N/A")),
            "experimental_method": exptl.get("method", info.get("experimental_method", "N/A")),
            "resolution_angstrom": resolution,
            "resolution_quality":  quality,
            "r_free":              refine.get("ls_rfactor_rfree"),
            "r_work":              refine.get("ls_rfactor_rwork"),
            "polymer_chains":      info.get("polymer_entity_count"),
            "nonpolymer_count":    info.get("nonpolymer_entity_count", 0),
            "has_ligand":          (info.get("nonpolymer_entity_count") or 0) > 0,
            "deposited_atoms":     info.get("deposited_atom_count"),
            "uniprot_ids":         e_ids.get("uniprot_ids", []),
        }
    except Exception as e:
        return {"_error": f"PDB fetch failed: {str(e)}"}


# ── NVIDIA API ────────────────────────────────────────────────
def call_nvidia(payload):
    """Send assembled payload to NVIDIA API and return the report."""
    user_message = (
        "BIOCORE ANALYSIS PAYLOAD:\n\n"
        + json.dumps(payload, indent=2)
        + "\n\nExecute Steps 1 through 7 in full."
    )

    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
    }

    body = {
        "model":       NVIDIA_MODEL,
        "temperature": 0.1,
        "max_tokens":  4096,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
    }

    res  = requests.post(NVIDIA_URL, headers=headers, json=body, timeout=120)
    data = res.json()

    if not res.ok:
        raise Exception(f"NVIDIA API error {res.status_code}: {json.dumps(data)}")

    return data["choices"][0]["message"]["content"]


# ── Routes ────────────────────────────────────────────────────
@app.route("/biocore", methods=["POST"])
def biocore_agent():
    """
    Main endpoint — called by n8n bridge workflow.

    Expected JSON body:
    {
      "compound_name": "ibuprofen",   // or use cid
      "cid": 3672,                    // optional, PubChem CID
      "pdb_id": "1EQG",              // required, 4-char PDB ID
      "docking_results": {...},       // optional
      "swissdock_results": {...},     // optional
      "pymol_data": {...}             // optional
    }
    """
    try:
        body = request.get_json()
        if not body:
            return jsonify({"status": "error", "message": "No JSON body received"}), 400

        compound_name   = body.get("compound_name")
        cid             = body.get("cid")
        pdb_id          = (body.get("pdb_id") or "").upper().strip()
        docking_results = body.get("docking_results")
        swissdock       = body.get("swissdock_results")
        pymol_data      = body.get("pymol_data")

        # Validate
        if not compound_name and not cid:
            return jsonify({"status": "error", "message": "Provide compound_name or cid"}), 400
        if not pdb_id or len(pdb_id) != 4:
            return jsonify({"status": "error", "message": "Provide a valid 4-char pdb_id e.g. 1EQG"}), 400
        if not NVIDIA_API_KEY:
            return jsonify({"status": "error", "message": "NVIDIA_API_KEY not configured on server"}), 500

        print(f"\n[BioCore] Compound: {compound_name or cid}  |  Target: {pdb_id}")

        print("[BioCore] → Fetching PubChem...")
        compound = fetch_pubchem(compound_name=compound_name, cid=cid)

        print("[BioCore] → Fetching RCSB PDB...")
        target = fetch_pdb(pdb_id)

        payload = {
            "compound":  compound,
            "target":    target,
            "docking":   docking_results,
            "swissdock": swissdock,
            "pymol":     pymol_data,
        }

        print("[BioCore] → Calling NVIDIA API...")
        report = call_nvidia(payload)
        print("[BioCore] ✓ Done!")

        return jsonify({
            "status": "success",
            "meta": {
                "compound_queried": compound_name or cid,
                "pdb_id_queried":   pdb_id,
                "model_used":       NVIDIA_MODEL,
            },
            "report": report,
        }), 200

    except Exception as e:
        print(f"[BioCore] ERROR: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":     "BioCore agent running",
        "model":      NVIDIA_MODEL,
        "api_key_set": bool(NVIDIA_API_KEY),
    }), 200


# ── Entry point ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 52)
    print("  BioCore External Agent")
    print(f"  Listening on http://0.0.0.0:{PORT}")
    print(f"  Model: {NVIDIA_MODEL}")
    print(f"  API key set: {'YES' if NVIDIA_API_KEY else 'NO ⚠️'}")
    print("=" * 52)
    app.run(host="0.0.0.0", port=PORT, debug=False)
