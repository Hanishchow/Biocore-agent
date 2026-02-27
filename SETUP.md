# BioCore — Setup Guide

There are **two ways** to run BioCore. Choose the one that fits you.

---

## Option A — Full n8n Workflow (no local server needed)

Everything runs inside n8n. Best if you just want to import and go.

### Steps

1. Open your n8n instance
2. Go to **Workflows → Import from file**
3. Import `n8n/biocore_workflow.json`
4. Open the **"BioCore AI Agent"** node
5. Find the line `const NVIDIA_API_KEY = 'YOUR_NVIDIA_API_KEY';`
6. Replace `YOUR_NVIDIA_API_KEY` with your real key from https://integrate.api.nvidia.com
7. **Save** and **Activate** the workflow
8. Test with a POST to your webhook URL (see [Testing](#testing))

> ⚠️ **Never commit your real API key to GitHub.** Edit it only inside n8n, not in the JSON file.

---

## Option B — Bridge Workflow + Local Python Agent

n8n handles the webhook and routing. A local Python Flask app does the heavy lifting (PubChem, PDB, NVIDIA). Exposed via ngrok tunnel.

### Requirements

- Python 3.9+
- ngrok account (free tier works): https://ngrok.com
- n8n instance

### Steps

#### 1. Set up the Python agent

```bash
cd agent/
pip install -r requirements.txt

# Copy the env template and fill in your key
cp ../.env.example .env
# Edit .env and set NVIDIA_API_KEY=nvapi-...

python biocore_agent.py
# Should print: Listening on http://0.0.0.0:5000
```

#### 2. Start ngrok

```bash
ngrok http 5000
```

Copy the Forwarding URL — it looks like:
```
https://abc123.ngrok-free.app
```

#### 3. Import the bridge workflow into n8n

1. Import `n8n/biocore_bridge_workflow.json`
2. Open the **"Bridge to BioCore Agent"** node
3. Replace the URL with your ngrok URL:
   ```
   https://YOUR-NGROK-URL.ngrok-free.app/biocore
   ```
4. Save and Activate

---

## Testing

Send a POST request to your n8n webhook URL.

### Minimal test (curl)

```bash
curl -X POST https://your-n8n-instance.com/webhook/biocore-analyze \
  -H "Content-Type: application/json" \
  -d '{
    "compound_name": "ibuprofen",
    "pdb_id": "1EQG"
  }'
```

### Full test with docking results

```bash
curl -X POST https://your-n8n-instance.com/webhook/biocore-analyze \
  -H "Content-Type: application/json" \
  -d '{
    "compound_name": "ibuprofen",
    "pdb_id": "1EQG",
    "docking_results": {
      "poses": [
        { "rank": 1, "affinity_kcal_mol": -8.4, "rmsd": 0.0 },
        { "rank": 2, "affinity_kcal_mol": -7.9, "rmsd": 1.2 }
      ]
    }
  }'
```

### Health check (Option B only)

```bash
curl http://localhost:5000/health
```

---

## Expected Response

```json
{
  "status": "success",
  "meta": {
    "compound_queried": "ibuprofen",
    "pdb_id_queried": "1EQG",
    "model_used": "NVIDIABuild-Autogen-12"
  },
  "report": "## STEP 1 — COMPOUND PROFILING\n\n..."
}
```

---

## Payload Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `compound_name` | string | Yes* | Common or IUPAC name e.g. `"ibuprofen"` |
| `cid` | number | Yes* | PubChem CID (alternative to compound_name) |
| `pdb_id` | string | Yes | 4-character PDB accession e.g. `"1EQG"` |
| `docking_results` | object | No | AutoDock / Vina output data |
| `swissdock_results` | object | No | SwissDock output data |
| `pymol_data` | object | No | PyMOL session metadata |

*Provide either `compound_name` or `cid`, not both required.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Validation failed` | Check `compound_name`/`cid` and `pdb_id` are in the body |
| `PubChem returned no results` | Try using the CID instead of the name |
| `NVIDIA API error 401` | Your API key is wrong or expired |
| `NVIDIA API error 429` | Rate limited — wait and retry |
| `fetch() to NVIDIA failed` | Check n8n has outbound internet access |
| ngrok tunnel closed | Restart `ngrok http 5000` and update the URL in n8n |
