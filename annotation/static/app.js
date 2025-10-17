const state = {
  emailHashes: [],
  index: 0,
  runId: null,
  judgment: null,  // {pass_fail, judged_at, updated_at} for current email
  annotations: [],
  failureModes: [],
  labelers: [],
};

function qs(selector) {
  const el = document.querySelector(selector);
  if (!el) throw new Error(`Missing element ${selector}`);
  return el;
}

const elements = {
  runIdInput: qs('#run-id-input'),
  loadRunBtn: qs('#load-run-btn'),
  runId: qs('#run-id'),
  llmSummary: qs('#llm-summary'),
  llmCommitments: qs('#llm-commitments'),
  position: qs('#email-position'),
  labelerSelect: qs('#labeler-select'),
  newLabelerBtn: qs('#new-labeler-btn'),
  prevBtn: qs('#prev-btn'),
  nextBtn: qs('#next-btn'),
  judgmentStatus: qs('#judgment-status'),
  addNoteBtn: qs('#add-note-btn'),
  failureBtn: qs('#failure-btn'),
  emailSubject: qs('#email-subject'),
  metadataChips: qs('#metadata-chips'),
  emailBody: qs('#email-body'),
  annotationList: qs('#annotation-list'),
  selectedFailureModes: qs('#selected-failure-modes'),
  noteDialog: qs('#note-dialog'),
  noteForm: qs('#note-form'),
  noteText: qs('#note-text'),
  failureDialog: qs('#failure-dialog'),
  failureForm: qs('#failure-form'),
  failureSelect: qs('#failure-select'),
  failureName: qs('#failure-name'),
  failureDefinition: qs('#failure-definition'),
};

async function fetchJSON(url, options = {}) {
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `HTTP ${resp.status}`);
  }
  return resp.json();
}

async function loadContext(runIdOverride = null) {
  const url = runIdOverride ? `/api/context?run_id=${encodeURIComponent(runIdOverride)}` : '/api/context';
  const data = await fetchJSON(url);
  state.runId = data.run_id;
  state.emailHashes = data.email_hashes || data.email_ids || [];
  let labelers = data.labelers || [];

  if (!labelers.length) {
    const firstName = prompt('No labelers found. Enter your name to start annotating.');
    if (!firstName) {
      alert('Labeler name is required.');
      return;
    }
    const created = await fetchJSON('/api/labelers', {
      method: 'POST',
      body: JSON.stringify({ name: firstName }),
    });
    labelers = [[created.labeler_id, created.name]];
  }


state.labelers = labelers;
elements.runId.textContent = state.runId;
if (runIdOverride) {
  elements.runIdInput.value = runIdOverride;
} else if (!elements.runIdInput.value) {
  elements.runIdInput.value = state.runId;
}
  populateLabelers();
  if (!elements.labelerSelect.value && state.labelers.length) {
    elements.labelerSelect.value = state.labelers[0][0];
  }
  state.index = 0;
  updatePosition();
  if (state.emailHashes.length) {
    await loadEmail(state.emailHashes[state.index]);
  }
}

function updatePosition() {
  if (!state.emailHashes.length) {
    elements.position.textContent = '0 / 0';
    return;
  }
  elements.position.textContent = `${state.index + 1} / ${state.emailHashes.length}`;
}

function populateLabelers() {
  elements.labelerSelect.innerHTML = '';
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = '— select labeler —';
  elements.labelerSelect.appendChild(placeholder);
  for (const [labelerId, name] of state.labelers) {
    const opt = document.createElement('option');
    opt.value = labelerId;
    opt.textContent = name || labelerId;
    elements.labelerSelect.appendChild(opt);
  }
}

async function loadEmail(emailHash) {
  const labelerId = elements.labelerSelect.value;
  if (!labelerId) {
    return;
  }
  const data = await fetchJSON(`/api/email/${encodeURIComponent(emailHash)}?labeler_id=${encodeURIComponent(labelerId)}`);
  const email = data.email;
  state.judgment = data.judgment;  // {pass_fail, judged_at, updated_at} or null
  state.annotations = data.annotations;
  state.failureModes = data.available_failure_modes || [];

  elements.emailSubject.textContent = email.subject || '(no subject)';
  elements.metadataChips.innerHTML = '';

  // Only show essential email metadata with fallbacks
  const metadata = email.metadata || {};

  const fromValue = metadata.from_email || metadata.from_raw;
  const toValue = metadata.to_emails || metadata.to_raw;
  const ccValue = metadata.cc_emails || metadata.cc_raw;

  if (fromValue) {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = `From: ${fromValue}`;
    elements.metadataChips.appendChild(chip);
  }

  if (toValue) {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = `To: ${toValue}`;
    elements.metadataChips.appendChild(chip);
  }

  if (ccValue) {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = `Cc: ${ccValue}`;
    elements.metadataChips.appendChild(chip);
  }

  elements.emailBody.innerHTML = formatBody(email.body || '');

  const summaryText = email.summary ?? metadata.llm_summary ?? '—';
  elements.llmSummary.textContent = summaryText && summaryText.length ? summaryText : '—';
  const commitments = email.commitments ?? metadata.llm_commitments ?? [];
  elements.llmCommitments.innerHTML = '';
  if (commitments && commitments.length) {
    commitments.forEach(item => {
      const li = document.createElement('li');
      li.textContent = item;
      elements.llmCommitments.appendChild(li);
    });
  } else {
    const li = document.createElement('li');
    li.textContent = 'No commitments extracted.';
    elements.llmCommitments.appendChild(li);
  }

  renderJudgment();
  renderAnnotations();
  renderSelectedFailureModes(data.failure_modes || []);
  populateFailureSelect();
}

function renderJudgment() {
  // Remove existing judgment classes from email body
  elements.emailBody.classList.remove('judgment-pass', 'judgment-fail');

  if (!state.judgment) {
    elements.judgmentStatus.textContent = 'No judgment yet. Press Z (pass) or X (fail).';
    elements.judgmentStatus.className = '';
    return;
  }

  const status = state.judgment.pass_fail ? 'PASS ✓' : 'FAIL ✗';
  const className = state.judgment.pass_fail ? 'pass' : 'fail';
  const timestamp = new Date(state.judgment.judged_at).toLocaleString();

  // Update judgment status display
  elements.judgmentStatus.textContent = `${status} (${timestamp})`;
  elements.judgmentStatus.className = className;

  // Highlight email body background
  elements.emailBody.classList.add(`judgment-${className}`);
}

function formatBody(body) {
  const escaped = body
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return escaped
    .split('\n')
    .map(line => (line.startsWith('>') ? `<blockquote>${line}</blockquote>` : line))
    .join('\n');
}

function renderAnnotations() {
  elements.annotationList.innerHTML = '';
  if (!state.annotations.length) {
    const empty = document.createElement('li');
    empty.textContent = 'No notes yet. Press N to add one.';
    elements.annotationList.appendChild(empty);
    return;
  }
  state.annotations.forEach(annotation => {
    const item = document.createElement('li');
    item.className = 'annotation-item';

    const header = document.createElement('header');
    header.innerHTML = `<span>${annotation.labeler_id || 'unknown'} · ${new Date(annotation.created_at).toLocaleString()}</span>`;
    const removeBtn = document.createElement('button');
    removeBtn.textContent = 'Remove';
    removeBtn.addEventListener('click', async () => {
      await fetchJSON(`/api/annotations/${annotation.annotation_id}`, { method: 'DELETE' });
      await loadEmail(state.emailHashes[state.index]);
    });
    header.appendChild(removeBtn);
    const body = document.createElement('p');
    body.textContent = annotation.open_code;

    item.appendChild(header);
    item.appendChild(body);
    elements.annotationList.appendChild(item);
  });
}

function renderSelectedFailureModes(modes) {
  elements.selectedFailureModes.innerHTML = '';
  if (!modes.length) {
    const empty = document.createElement('span');
    empty.textContent = 'No failure modes assigned yet.';
    elements.selectedFailureModes.appendChild(empty);
    return;
  }
  modes.forEach(mode => {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = mode.display_name;
    const remove = document.createElement('button');
    remove.textContent = '×';
    remove.addEventListener('click', async () => {
      await fetchJSON(`/api/axial-links?annotation_id=${mode.annotation_id}&failure_mode_id=${mode.failure_mode_id}`, { method: 'DELETE' });
      await loadEmail(state.emailHashes[state.index]);
    });
    chip.appendChild(remove);
    elements.selectedFailureModes.appendChild(chip);
  });
}

function populateFailureSelect() {
  elements.failureSelect.innerHTML = '';
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = '— choose failure mode —';
  elements.failureSelect.appendChild(placeholder);
  state.failureModes.forEach(mode => {
    const opt = document.createElement('option');
    opt.value = mode.failure_mode_id;
    opt.textContent = `${mode.display_name} (${mode.slug})`;
    opt.dataset.definition = mode.definition || '';
    elements.failureSelect.appendChild(opt);
  });
}

async function createJudgment(passFail) {
  const labelerId = elements.labelerSelect.value;
  if (!labelerId) {
    alert('Select a labeler first.');
    return;
  }
  const payload = {
    email_hash: state.emailHashes[state.index],
    pass_fail: passFail,
    labeler_id: labelerId,
  };
  await fetchJSON('/api/judgments', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  await loadEmail(state.emailHashes[state.index]);
}

async function deleteJudgment() {
  if (!state.judgment) {
    return;  // Nothing to delete
  }
  const labelerId = elements.labelerSelect.value;
  if (!labelerId) {
    return;
  }
  // Instant delete - no confirmation dialog
  await fetchJSON(
    `/api/judgments?email_hash=${encodeURIComponent(state.emailHashes[state.index])}&labeler_id=${encodeURIComponent(labelerId)}`,
    { method: 'DELETE' }
  );
  await loadEmail(state.emailHashes[state.index]);
}

async function submitNote(event) {
  event.preventDefault();
  const openCode = elements.noteText.value.trim();
  if (!openCode) {
    alert('Please provide a note.');
    return;
  }

  const labelerId = elements.labelerSelect.value;
  const existingNote = state.annotations.find(a => a.labeler_id === labelerId);

  if (existingNote) {
    // Update existing note
    await fetchJSON(`/api/annotations/${existingNote.annotation_id}`, {
      method: 'PUT',
      body: JSON.stringify({ open_code: openCode }),
    });
  } else {
    // Create new note
    const payload = {
      email_hash: state.emailHashes[state.index],
      open_code: openCode,
      labeler_id: labelerId,
    };
    await fetchJSON('/api/annotations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  elements.noteDialog.close();
  elements.noteForm.reset();
  await loadEmail(state.emailHashes[state.index]);
}

async function submitFailureMode(event) {
  event.preventDefault();
  if (!state.judgment) {
    alert('Create a judgment (Z/X) before assigning failure modes.');
    return;
  }
  if (state.judgment.pass_fail) {
    alert('Failure modes are only for failed emails.');
    return;
  }

  // Create a placeholder annotation if none exists (for backward compatibility with axial_links)
  let annotationId;
  if (state.annotations.length > 0) {
    annotationId = state.annotations[0].annotation_id;
  } else {
    // Create implicit annotation for failure mode linkage
    const labelerId = elements.labelerSelect.value;
    const response = await fetchJSON('/api/annotations', {
      method: 'POST',
      body: JSON.stringify({
        email_hash: state.emailHashes[state.index],
        open_code: '(failure mode assignment)',
        labeler_id: labelerId,
      }),
    });
    annotationId = response.annotation_id;
  }

  const existingId = elements.failureSelect.value || null;
  let failureModeId = existingId;
  if (!existingId) {
    const displayName = elements.failureName.value.trim();
    if (!displayName) {
      alert('Provide a name or choose an existing failure mode.');
      return;
    }
    const definition = elements.failureDefinition.value.trim();
    const created = await fetchJSON('/api/failure-modes', {
      method: 'POST',
      body: JSON.stringify({ display_name: displayName, definition }),
    });
    failureModeId = created.failure_mode_id;
  }
  await fetchJSON('/api/axial-links', {
    method: 'POST',
    body: JSON.stringify({
      annotation_id: annotationId,
      failure_mode_id: failureModeId,
    }),
  });
  elements.failureDialog.close();
  elements.failureForm.reset();
  await loadEmail(state.emailHashes[state.index]);
}

function bindEvents() {
  elements.prevBtn.addEventListener('click', () => {
    if (state.index > 0) {
      state.index -= 1;
      updatePosition();
      loadEmail(state.emailHashes[state.index]);
    }
  });
  elements.nextBtn.addEventListener('click', () => {
    if (state.index < state.emailHashes.length - 1) {
      state.index += 1;
      updatePosition();
      loadEmail(state.emailHashes[state.index]);
    }
  });
  elements.addNoteBtn.addEventListener('click', () => {
    if (!elements.labelerSelect.value) {
      alert('Select or create a labeler first.');
      return;
    }
    if (!state.judgment) {
      alert('Create a judgment (Z/X) before adding notes.');
      return;
    }

    // Pre-fill with existing note if it exists
    const labelerId = elements.labelerSelect.value;
    const existingNote = state.annotations.find(a => a.labeler_id === labelerId);
    if (existingNote) {
      elements.noteText.value = existingNote.open_code;
    } else {
      elements.noteText.value = '';
    }

    elements.noteDialog.showModal();
    setTimeout(() => elements.noteText.focus(), 50);
  });
  elements.failureBtn.addEventListener('click', () => {
    if (!state.judgment) {
      alert('Create a judgment (Z/X) before assigning failure modes.');
      return;
    }
    if (state.judgment.pass_fail) {
      alert('Failure modes are only for failed emails.');
      return;
    }
    populateFailureSelect();
    elements.failureDialog.showModal();
  });
  elements.noteForm.addEventListener('submit', submitNote);
  elements.failureForm.addEventListener('submit', submitFailureMode);

  // Handle Enter to submit note (Shift+Enter for new line)
  elements.noteText.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      elements.noteForm.requestSubmit();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      elements.noteDialog.close();
    }
  });
  elements.newLabelerBtn.addEventListener('click', async () => {
    const name = prompt('Labeler name');
    if (!name) return;
    const created = await fetchJSON('/api/labelers', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
    state.labelers.push([created.labeler_id, created.name]);
    populateLabelers();
    elements.labelerSelect.value = created.labeler_id;
  });

  elements.loadRunBtn.addEventListener('click', async () => {
    const desired = elements.runIdInput.value.trim();
    await loadContext(desired || null);
  });
  elements.runIdInput.addEventListener('keydown', async event => {
    if (event.key === 'Enter') {
      event.preventDefault();
      const desired = elements.runIdInput.value.trim();
      await loadContext(desired || null);
    }
  });

  document.addEventListener('keydown', event => {
    if (event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLInputElement) {
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      deleteJudgment();
    } else if (event.key.toLowerCase() === 'z') {
      event.preventDefault();
      createJudgment(true);  // Pass
    } else if (event.key.toLowerCase() === 'x') {
      event.preventDefault();
      createJudgment(false);  // Fail
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      elements.prevBtn.click();
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      elements.nextBtn.click();
    } else if (event.key.toLowerCase() === 'n') {
      event.preventDefault();
      elements.addNoteBtn.click();
    } else if (event.key.toLowerCase() === 'f') {
      event.preventDefault();
      elements.failureBtn.click();
    }
  });
}

window.addEventListener('DOMContentLoaded', async () => {
  bindEvents();
  try {
    await loadContext();
  } catch (error) {
    alert(`Failed to load context: ${error}`);
  }
});
