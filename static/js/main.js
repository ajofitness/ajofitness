document.addEventListener('DOMContentLoaded', function() {
  setTimeout(function() {
    document.querySelectorAll('.ft-alert').forEach(function(el) {
      const alert = bootstrap.Alert.getOrCreateInstance(el);
      setTimeout(() => alert.close(), Math.random() * 1000 + 500);
    });
  }, 4000);

  // Theme toggle
  const html = document.documentElement;
  const themeBtn = document.getElementById('themeToggle');

  function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  if (themeBtn) {
    // Apply persisted theme client-side
    var savedTheme = localStorage.getItem('ft-theme');
    if (savedTheme) {
      html.setAttribute('data-bs-theme', savedTheme);
    }
    // Update meta theme-color
    var metaTheme = document.querySelector('meta[name="theme-color"]');
    if (metaTheme) {
      metaTheme.content = savedTheme === 'light' ? '#ffffff' : '#0a0a0a';
    }

    themeBtn.addEventListener('click', function() {
      const current = html.getAttribute('data-bs-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      // Instant client-side switch
      html.setAttribute('data-bs-theme', next);
      localStorage.setItem('ft-theme', next);
      // Persist on server
      fetch('/toggle-dark-mode', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCSRFToken(),
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'csrf_token=' + encodeURIComponent(getCSRFToken()),
      }).catch(function() { /* silent */ });
      // Update icon and theme-color
      const icon = themeBtn.querySelector('i');
      if (icon) {
        icon.className = 'bi ' + (next === 'dark' ? 'bi-moon-fill' : 'bi-sun-fill');
      }
      var metaTheme = document.querySelector('meta[name="theme-color"]');
      if (metaTheme) {
        metaTheme.content = next === 'light' ? '#ffffff' : '#0a0a0a';
      }
    });
  }

  // Notification reminder polling
  let reminderInterval = null;
  const NOTIFICATION_INTERVAL = 5 * 60 * 1000;

  function checkForReminder() {
    if (!('Notification' in window) || Notification.permission === 'denied') return;
    if (Notification.permission === 'granted') {
      doReminderCheck();
    } else {
      Notification.requestPermission().then(function(permission) {
        if (permission === 'granted') doReminderCheck();
      });
    }
  }

  function doReminderCheck() {
    fetch('/api/check-reminder')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (!data.show_reminder) return;
        var message = 'Ajò: ';
        var parts = [];
        if (data.missing_meals) parts.push('pasti');
        if (data.missing_water) parts.push('acqua');
        if (data.missing_workout) parts.push('allenamento');
        message += 'Non hai registrato ' + parts.join(', ') + ' oggi!';
        if (navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({
            type: 'show-notification', title: 'Ajò', body: message, tag: 'ajo-reminder',
          });
        } else {
          new Notification('Ajò', {
            body: message, icon: '/static/icon-192.png', tag: 'ajo-reminder',
          });
        }
      })
      .catch(function() {});
  }

  function startReminderPolling() {
    var loginForm = document.querySelector('form[action*="login"]');
    if (!loginForm && reminderInterval === null) {
      reminderInterval = setInterval(checkForReminder, NOTIFICATION_INTERVAL);
    }
  }

  setTimeout(function() {
    startReminderPolling();
    checkForReminder();
  }, 30000);
});
