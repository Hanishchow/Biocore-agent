# 🧬 BioCore — Biochemistry & Biophysics Analysis Agent

BioCore is an AI-powered biochemistry pipeline that performs a **7-step analysis** of any compound–protein interaction. It pulls live data from **PubChem** and **RCSB PDB**, then runs a deep analysis via the **NVIDIA API**.

---

## What It Does

Given a compound (e.g. ibuprofen) and a protein target (e.g. PDB: 1EQG), BioCore automatically:

| Step | Analysis |
|------|----------|
| 1 | **Compound profiling** — IUPAC name, SMILES, MW, XLogP3, TPSA, Lipinski Ro5, ADMET flags |
| 2 | **Protein target profiling** — resolution, method, R-free, UniProt IDs, co-crystallized ligands |
| 3 | **Docking result analysis** — affinity (kcal/mol), Kd calculation, pose ranking |
| 4 | **Interaction mechanism** — H-bonds, hydrophobics, conformational changes, ΔG landscape |
| 5 | **Theoretical → practical bridge** — IC50 estimate, CYP450 flags, cell permeability |
| 6 | **PyMOL visualization commands** — ready-to-run scripts |
| 7 | **Synthesis report** — structured markdown with verdict and next steps |

---

## Architecture

```
POST /webhook/biocore-analyze
        │
        ▼
  ┌─────────────┐
  │   n8n        │  Validate → Fetch PubChem → Fetch PDB → AI Agent → Return
  └─────────────┘
        │  (Option B only — bridge to local agent via ngrok)
        ▼
  ┌─────────────┐
  │ Flask Agent │  biocore_agent.py running on localhost:5000
  └─────────────┘
        │
        ▼
  NVIDIA API  (7-step BioCore analysis)
```

---

## Quick Start

**Option A** — Everything in n8n (simplest):
1. Import `n8n/biocore_workflow.json` into n8n
2. Set your `NVIDIA_API_KEY` inside the Code node
3. Activate & send a POST request

**Option B** — Local Python agent + ngrok:
1. `cd agent && pip install -r requirements.txt`
2. Copy `.env.example` → `.env`, add your `NVIDIA_API_KEY`
3. `python biocore_agent.py`
4. `ngrok http 5000` → paste URL into n8n bridge workflow

→ Full instructions in [`docs/SETUP.md`](docs/SETUP.md)

---

## Example Request

```bash
curl -X POST https://your-n8n.com/webhook/biocore-analyze \
  -H "Content-Type: application/json" \
  -d '{
    "compound_name": "ibuprofen",
    "pdb_id": "1EQG",
    "docking_results": {
      "poses": [
        { "rank": 1, "affinity_kcal_mol": -8.4, "rmsd": 0.0 }
      ]
    }
  }'
```

---

## File Structure

```
biocore/
├── n8n/
│   ├── biocore_workflow.json        # Main workflow (all inside n8n)
│   └── biocore_bridge_workflow.json # Bridge workflow (→ local agent)
├── agent/
│   ├── biocore_agent.py             # Flask agent (Option B)
│   └── requirements.txt
├── docs/
│   └── SETUP.md                     # Full setup guide
├── .env.example                     # API key template
├── .gitignore
└── README.md
```

---

## APIs Used

| Service | Purpose | Cost |
|---------|---------|------|
| [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest) | Compound properties | Free |
| [RCSB PDB REST](https://data.rcsb.org) | Protein structure data | Free |
| [NVIDIA API](https://integrate.api.nvidia.com) | BioCore AI analysis | Paid (key required) |

---

## Security

- **Never** put your real `NVIDIA_API_KEY` in the JSON workflow files before pushing to GitHub
- Use `.env` locally (already in `.gitignore`)
- In n8n, set the key inside the node editor — it stays in your n8n instance only

---

## License

MIT
