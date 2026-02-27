# BioCore Dashboard

A clean browser-based dashboard for the BioCore biochemistry analysis pipeline. Fill in the form, hit **Run**, and get your 7-step report directly in the browser.

## Features

- Analysis name + description for every run
- Compound input (name or PubChem CID)
- Protein target PDB accession
- Optional docking / SwissDock / PyMOL JSON inputs
- Live loading steps while analysis runs
- Markdown-rendered report with copy + download buttons
- Webhook URL saved in browser (no re-entering)

## Setup

1. Make sure your **BioCore n8n workflow** is active and you have a webhook URL
2. Open `index.html` in a browser (no server needed)
3. Paste your webhook URL in the **n8n Webhook** field — it saves automatically
4. Fill in your compound and PDB ID and click **Run BioCore Analysis**

## Files

```
biocore-dashboard/
├── index.html   — layout and form structure
├── style.css    — all styling (sci-fi dark theme)
└── script.js    — validation, API calls, rendering
```

## Example Input

| Field | Example |
|-------|---------|
| Analysis Name | `Ibuprofen vs COX-2 binding study` |
| Description | `AutoDock Vina run #4, comparing top 3 poses` |
| Compound Name | `ibuprofen` |
| PDB Accession | `1EQG` |
| n8n Webhook | `https://your-n8n.com/webhook/biocore-analyze` |

## Related

This dashboard works with the BioCore n8n workflow in the main `biocore/` repo.
