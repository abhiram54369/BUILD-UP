(function () {
  const body = document.body;
  const button = document.getElementById('theme-toggle');
  const label = document.getElementById('theme-label');
  const icon = document.getElementById('theme-icon');
  const meta = document.getElementById('theme-color-meta');
  function applyTheme(theme) {
    body.dataset.theme = theme;
    const day = theme === 'day';
    if (label) label.textContent = day ? 'Night mode' : 'Day mode';
    if (icon) icon.textContent = day ? '☾' : '☼';
    if (button) button.setAttribute('aria-label', day ? 'Switch to night mode' : 'Switch to day mode');
    if (meta) meta.setAttribute('content', day ? '#f4f0fa' : '#090909');
  }
  let saved = 'night';
  try { saved = localStorage.getItem('build-up-theme') || 'night'; } catch (_) {}
  applyTheme(saved === 'day' ? 'day' : 'night');
  if (button) button.addEventListener('click', function () {
    const next = body.dataset.theme === 'day' ? 'night' : 'day';
    applyTheme(next);
    try { localStorage.setItem('build-up-theme', next); } catch (_) {}
  });
})();

document.addEventListener('click', function (event) {
  const button = event.target.closest('#add-exercise');
  if (button) {
    const list = document.getElementById('exercise-list');
    if (!list) return;
    const row = document.createElement('div');
    row.className = 'exercise-row';
    row.innerHTML = '<input name="exercise_name[]" placeholder="Exercise" aria-label="Exercise"><input name="sets[]" type="number" min="1" max="20" value="3" aria-label="Sets"><input name="reps[]" type="number" min="1" max="100" value="10" aria-label="Reps"><input name="weight[]" type="number" min="0" step="0.5" value="0" aria-label="Weight in kg">';
    list.appendChild(row);
  }
  const hint = event.target.closest('[data-coach-prompt]');
  if (hint) {
    const textarea = document.getElementById('coach-message');
    if (textarea) { textarea.value = hint.dataset.coachPrompt; textarea.focus(); }
  }
});

document.addEventListener('submit', function (event) {
  const form = event.target.closest('form[data-confirm]');
  if (form && !window.confirm(form.dataset.confirm)) event.preventDefault();
});
