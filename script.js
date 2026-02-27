/**
 * BioCore Dashboard — script.js
 * Handles form validation, API calls, loading states, and report rendering.
 */

// ── Constants ─────────────────────────────────────────────────
const STORAGE_KEY_WEBHOOK = 'biocore_webhook_url';

// ── DOM refs ──────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const dom = {
  projectName:    $('projectName'),
  projectDesc:    $('projectDesc'),
  compoundName:   $('compoundName'),
  cid:            $('cid'),
  pdbId:          $('pdbId'),
  dockingJson:    $('dockingJson'),
  swissdockJson:  $('swissdockJson'),
  pymolJson:      $('pymolJson'),
  webhookUrl:     $('webhookUrl'),
  btnRun:         $('btnRun'),
  statusDot:      $('statusDot'),
  statusLabel:    $('statusLabel'),
  emptyState:     $('emptyState'),
  loadingState:   $('loadingState'),
  resultState:    $('resultState'),
  errorState:     $('errorState'),
  outputActions:  $('outputActions'),
  resultMeta:     $('resultMeta'),
  resultBody:     $('resultBody'),
  errorMsg:       $('errorMsg'),
  dockingToggle:  $('dockingToggle'),
  dockingBody:    $('dockingBody'),
  dockingChevron: $('dockingChevron'),
};

// ── State ─────────────────────────────────────────────────────
let lastReport = '';
let loadingTimer = null;

// ── Init ──────────────────────────────────────────────────────
(function init() {
  // Restore saved webhook URL
  const saved = localStorage.getItem(STORAGE_KEY_WEBHOOK);
  if (saved) dom.webhookUrl.value = saved;

  // PDB input: auto-uppercase
  dom.pdbId.addEventListener('input', () => {
    dom.pdbId.value = dom.pdbId.value.toUpperCase();
  });

  // Collapsible docking section
  dom.dockingToggle.addEventListener('click', () => {
    const isOpen = dom.dockingBody.classList.toggle('open');
    dom.dockingChevron.classList.toggle('open', isOpen);
  });

  // Save webhook URL on change
  dom.webhookUrl.addEventListener('input', () => {
    localStorage.setItem(STORAGE_KEY_WEBHOOK, dom.webhookUrl.value.trim());
  });
})();

// ── Validation ────────────────────────────────────────────────
function validate() {
  const errors = [];

  const compoundName = dom.compoundName.value.trim();
  const cid          = dom.cid.value.trim();
  const pdbId        = dom.pdbId.value.trim();
  const webhookUrl   = dom.webhookUrl.value.trim();
  const projectName  = dom.projectName.value.trim();

  if (!projectName)            errors.push('Analysis Name is required.');
  if (!compoundName && !cid)   errors.push('Provide a Compound Name or PubChem CID.');
  if (!pdbId || pdbId.length !== 4) errors.push('PDB Accession must be exactly 4 characters (e.g. 1EQG).');
  if (!webhookUrl)             errors.push('n8n Webhook URL is required.');

  // Validate optional JSON fields
  ['dockingJson', 'swissdockJson', 'pymolJson'].forEach(key => {
    const val = dom[key].value.trim();
    if (val) {
      try { JSON.parse(val); }
      catch (e) { errors.push(`${key.replace('Json', '')} data is not valid JSON.`); }
    }
  });

  return errors;
}

// ── Build payload ─────────────────────────────────────────────
function buildPayload() {
  const payload = {
    analysis_name:    dom.projectName.value.trim(),
    analysis_description: dom.projectDesc.value.trim() || undefined,
    pdb_id:           dom.pdbId.value.trim().toUpperCase(),
  };

  const compoundName = dom.compoundName.value.trim();
  const cid          = dom.cid.value.trim();
  if (compoundName) payload.compound_name = compoundName;
  if (cid)          payload.cid           = parseInt(cid, 10);

  const dockRaw      = dom.dockingJson.value.trim();
  const swissRaw     = dom.swissdockJson.value.trim();
  const pymolRaw     = dom.pymolJson.value.trim();
  if (dockRaw)   payload.docking_results  = JSON.parse(dockRaw);
  if (swissRaw)  payload.swissdock_results = JSON.parse(swissRaw);
  if (pymolRaw)  payload.pymol_data        = JSON.parse(pymolRaw);

  return payload;
}

// ── UI state helpers ──────────────────────────────────────────
function showOnly(id) {
  ['emptyState', 'loadingState', 'resultState', 'errorState'].forEach(s => {
    $(s).style.display = s === id ? (s === 'resultState' ? 'block' : 'flex') : 'none';
  });
}

function setStatus(label, state) {
  dom.statusLabel.textContent = label;
  dom.statusDot.className = 'status-dot' + (state ? ' ' + state : '');
}

// ── Loading animation ─────────────────────────────────────────
const loadingMessages = [
  { id: 'ls1', label: 'Fetching PubChem data…',    delay: 0    },
  { id: 'ls2', label: 'Fetching RCSB PDB data…',   delay: 2500 },
  { id: 'ls3', label: 'Running 7-step AI analysis…', delay: 5000 },
  { id: 'ls4', label: 'Generating report…',         delay: 12000 },
];

function startLoadingAnimation() {
  loadingMessages.forEach(m => {
    const el = $(m.id);
    el.className = 'lstep';
    el.textContent = m.label;
  });
  let current = 0;
  const advance = () => {
    if (current > 0) $(loadingMessages[current - 1].id).className = 'lstep done';
    if (current < loadingMessages.length) {
      $(loadingMessages[current].id).className = 'lstep active';
      current++;
    }
  };
  advance();
  loadingTimer = setInterval(() => {
    const next = loadingMessages[current];
    if (next) setTimeout(advance, next.delay - (current > 0 ? loadingMessages[current-1].delay : 0));
  }, 2500);
}

function stopLoadingAnimation() {
  clearInterval(loadingTimer);
  loadingTimer = null;
}

// ── Markdown renderer (simple) ────────────────────────────────
function renderMarkdown(text) {
  const div = document.createElement('div');

  // Escape HTML
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Code blocks
  html = html.replace(/```[\w]*\n?([\s\S]*?)```/g, (_, code) =>
    `<pre><code>${code.trimEnd()}</code></pre>`
  );

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  // Italic
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // Horizontal rule
  html = html.replace(/^---$/gm, '<hr style="border-color:var(--border);margin:16px 0">');

  div.innerHTML = html;
  return div;
}

// ── Main: Run analysis ────────────────────────────────────────
async function runAnalysis() {
  // Validate
  const errors = validate();
  if (errors.length) {
    alert('Please fix the following:\n\n• ' + errors.join('\n• '));
    return;
  }

  const webhookUrl = dom.webhookUrl.value.trim();
  const payload    = buildPayload();

  // Lock UI
  dom.btnRun.disabled = true;
  dom.outputActions.style.display = 'none';
  showOnly('loadingState');
  setStatus('Running…', 'loading');
  startLoadingAnimation();

  try {
    const res = await fetch(webhookUrl, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });

    const data = await res.json();
    stopLoadingAnimation();

    if (!res.ok || data.status === 'error') {
      throw new Error(data.message || data.error || `HTTP ${res.status}`);
    }

    // Success
    lastReport = data.report || JSON.stringify(data, null, 2);
    renderResult(data, payload);
    showOnly('resultState');
    dom.outputActions.style.display = 'flex';
    setStatus('Complete', '');

  } catch (err) {
    stopLoadingAnimation();
    dom.errorMsg.textContent = err.message || 'Unknown error. Check the console for details.';
    showOnly('errorState');
    setStatus('Error', 'error');
    console.error('[BioCore]', err);
  } finally {
    dom.btnRun.disabled = false;
  }
}

// ── Render result ─────────────────────────────────────────────
function renderResult(data, payload) {
  // Meta bar
  const meta = data.meta || {};
  dom.resultMeta.innerHTML = `
    <div class="meta-item">
      <span class="meta-key">Analysis</span>
      <span class="meta-val">${escHtml(payload.analysis_name)}</span>
    </div>
    <div class="meta-item">
      <span class="meta-key">Compound</span>
      <span class="meta-val">${escHtml(meta.compound_queried || payload.compound_name || payload.cid || '—')}</span>
    </div>
    <div class="meta-item">
      <span class="meta-key">Target (PDB)</span>
      <span class="meta-val">${escHtml(meta.pdb_id_queried || payload.pdb_id)}</span>
    </div>
    <div class="meta-item">
      <span class="meta-key">Model</span>
      <span class="meta-val">${escHtml(meta.model_used || '—')}</span>
    </div>
    ${meta.tokens_used ? `
    <div class="meta-item">
      <span class="meta-key">Tokens</span>
      <span class="meta-val">${(meta.tokens_used.total_tokens || 0).toLocaleString()}</span>
    </div>` : ''}
  `;

  // Report body
  dom.resultBody.innerHTML = '';
  if (data.report) {
    dom.resultBody.appendChild(renderMarkdown(data.report));
  } else {
    dom.resultBody.textContent = JSON.stringify(data, null, 2);
  }
}

// ── Utility ───────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ── Copy report ───────────────────────────────────────────────
function copyReport() {
  if (!lastReport) return;
  navigator.clipboard.writeText(lastReport).then(() => {
    const btn = document.querySelector('.btn-copy');
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    btn.style.color = 'var(--green)';
    setTimeout(() => {
      btn.textContent = orig;
      btn.style.color = '';
    }, 1500);
  });
}

// ── Download report ───────────────────────────────────────────
function downloadReport() {
  if (!lastReport) return;
  const name   = dom.projectName.value.trim().replace(/[^a-z0-9]/gi, '_').toLowerCase() || 'biocore_report';
  const blob   = new Blob([lastReport], { type: 'text/markdown' });
  const url    = URL.createObjectURL(blob);
  const a      = document.createElement('a');
  a.href       = url;
  a.download   = `${name}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Clear form ────────────────────────────────────────────────
function clearForm() {
  dom.projectName.value  = '';
  dom.projectDesc.value  = '';
  dom.compoundName.value = '';
  dom.cid.value          = '';
  dom.pdbId.value        = '';
  dom.dockingJson.value  = '';
  dom.swissdockJson.value = '';
  dom.pymolJson.value    = '';
  showOnly('emptyState');
  dom.outputActions.style.display = 'none';
  setStatus('Ready', '');
  lastReport = '';
}
