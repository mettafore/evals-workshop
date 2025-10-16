const state = {
  emailHashes: [],
  index: 0,
  runId: null,
  annotations: [],
  failureModes: [],
  labelers: [],
  suggestions: [],
};

function qs(selector) {
  const el = document.querySelector(selector);
  if (!el) throw new Error(`Missing element ${selector}`);
  return el;
}

const elements = {
  runId: qs('#run-id'),
  position: qs('#email-position'),
  labelerSelect: qs('#labeler-select'),
  newLabelerBtn: qs('#new-labeler-btn'),
  prevBtn: qs('#prev-btn'),
  nextBtn: qs('#next-btn'),
  annotateBtn: qs('#annotate-btn'),
  failureBtn: qs('#failure-btn'),
  suggestBtn: qs('#suggest-btn'),
  emailSubject: qs('#email-subject'),
  metadataChips: qs('#metadata-chips'),
  emailBody: qs('#email-body'),
  annotationList: qs('#annotation-list'),
  selectedFailureModes: qs('#selected-failure-modes'),
  annotationDialog: qs('#annotation-dialog'),
  annotationForm: qs('#annotation-form'),
  annotationText: qs('#annotation-text'),
  annotationPassFail: qs('#annotation-passfail'),
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

async function loadContext() {
  const data = await fetchJSON('/api/context');
  state.runId = data.run_id;
  state.emailHashes = data.email_hashes || data.email_ids || [];
  state.labelers = data.labelers || [];
  elements.runId.textContent = state.runId;
  updatePosition();
  populateLabelers();
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
  const data = await fetchJSON(`/api/email/${encodeURIComponent(emailHash)}`);
  const email = data.email;
  state.annotations = data.annotations;
  state.failureModes = data.available_failure_modes || [];

  elements.emailSubject.textContent = email.subject || '(no subject)';
  elements.metadataChips.innerHTML = '';
  Object.entries(email.metadata || {}).forEach(([key, value]) => {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = `${key}: ${value}`;
    elements.metadataChips.appendChild(chip);
  });
  elements.emailBody.innerHTML = formatBody(email.body || '');
  renderAnnotations();
  renderSelectedFailureModes(data.failure_modes || []);
  populateFailureSelect();
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
    empty.textContent = 'No annotations yet—press A to add one.';
    elements.annotationList.appendChild(empty);
    return;
  }
  state.annotations.forEach(annotation => {
    const item = document.createElement('li');
    item.className = 'annotation-item';
    if (annotation.pass_fail === true) item.classList.add('pass');
    if (annotation.pass_fail === false) item.classList.add('fail');

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

async function submitAnnotation(event) {
  event.preventDefault();
  const openCode = elements.annotationText.value.trim();
  if (!openCode) return;
  const passFailRaw = elements.annotationPassFail.value;
  const passFail = passFailRaw === '' ? null : passFailRaw === '1';
  const labelerId = elements.labelerSelect.value || null;
  const payload = {
    email_hash: state.emailHashes[state.index],
    open_code: openCode,
    pass_fail: passFail,
    labeler_id: labelerId,
  };
  await fetchJSON('/api/annotations', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  elements.annotationDialog.close();
  elements.annotationForm.reset();
  await loadEmail(state.emailHashes[state.index]);
}

async function submitFailureMode(event) {
  event.preventDefault();
  if (!state.annotations.length) {
    alert('Add an annotation before assigning failure modes.');
    return;
  }
  const selectedAnnotation = state.annotations[0];
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
      annotation_id: selectedAnnotation.annotation_id,
      failure_mode_id: failureModeId,
    }),
  });
  elements.failureDialog.close();
  elements.failureForm.reset();
  await loadEmail(state.emailHashes[state.index]);
}

async function handleSuggestions() {
  if (!state.annotations.length) {
    alert('Add annotations before generating suggestions.');
    return;
  }
  const emailHash = state.emailHashes[state.index];
  const data = await fetchJSON(`/api/failure-modes/suggest?email_hash=${emailHash}`);
  state.suggestions = data.suggestions || [];
  if (!state.suggestions.length) {
    alert('No suggestions available yet – add more detailed annotations.');
    return;
  }
  const names = state.suggestions.map(s => s.display_name).join(', ');
  if (confirm(`Suggestions: ${names}. Add the first one?`)) {
    const suggestion = state.suggestions[0];
    const created = await fetchJSON('/api/failure-modes', {
      method: 'POST',
      body: JSON.stringify({
        display_name: suggestion.display_name,
        slug: suggestion.slug,
        definition: suggestion.definition,
      }),
    });
    const annotationId = state.annotations[0].annotation_id;
    await fetchJSON('/api/axial-links', {
      method: 'POST',
      body: JSON.stringify({
        annotation_id: annotationId,
        failure_mode_id: created.failure_mode_id,
      }),
    });
    await loadEmail(emailId);
  }
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
  elements.annotateBtn.addEventListener('click', () => {
    elements.annotationDialog.showModal();
    setTimeout(() => elements.annotationText.focus(), 50);
  });
  elements.failureBtn.addEventListener('click', () => {
    if (!state.annotations.length) {
      alert('Add an annotation before assigning failure modes.');
      return;
    }
    populateFailureSelect();
    elements.failureDialog.showModal();
  });
  elements.suggestBtn.addEventListener('click', handleSuggestions);
  elements.annotationForm.addEventListener('submit', submitAnnotation);
  elements.failureForm.addEventListener('submit', submitFailureMode);
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

  document.addEventListener('keydown', event => {
    if (event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLInputElement) {
      return;
    }
    if (event.key.toLowerCase() === 'z') {
    event.preventDefault();
    elements.annotationPassFail.value = '1';
  } else if (event.key.toLowerCase() === 'x') {
    event.preventDefault();
    elements.annotationPassFail.value = '0';
  } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      elements.prevBtn.click();
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      elements.nextBtn.click();
    } else if (event.key.toLowerCase() === 'a') {
      event.preventDefault();
      elements.annotateBtn.click();
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
