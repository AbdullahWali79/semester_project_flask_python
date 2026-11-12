document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.toggle-password').forEach((toggle) => toggle.addEventListener('click', () => {
    const input = document.getElementById(toggle.dataset.target);
    if (!input) return;
    const visible = input.type === 'text';
    input.type = visible ? 'password' : 'text';
    toggle.textContent = visible ? 'Show' : 'Hide';
    toggle.setAttribute('aria-label', visible ? 'Show password' : 'Hide password');
  }));

  document.querySelectorAll('form').forEach((form) => form.addEventListener('submit', () => {
    const button = form.querySelector('button[type="submit"]');
    if (button && !form.action.endsWith('/logout')) {
      button.disabled = true;
      button.textContent = 'Please wait…';
    }
  }));
});
