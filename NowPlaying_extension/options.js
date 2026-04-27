const DEFAULT_SERVER_URL = 'ws://127.0.0.1:8000';

const input = document.getElementById('serverUrl');
const statusEl = document.getElementById('status');

function normalizeServerUrl(url) {
  const value = String(url || '').trim();

  if (!value) return DEFAULT_SERVER_URL;

  if (!value.startsWith('ws://') && !value.startsWith('wss://')) {
    return DEFAULT_SERVER_URL;
  }

  return value;
}

chrome.storage.sync.get({ serverUrl: DEFAULT_SERVER_URL }, ({ serverUrl }) => {
  input.value = serverUrl || DEFAULT_SERVER_URL;
});

document.getElementById('save').addEventListener('click', () => {
  const value = normalizeServerUrl(input.value);

  chrome.storage.sync.set({ serverUrl: value }, () => {
    input.value = value;
    statusEl.textContent = 'Saved: ' + value;
  });
});

document.getElementById('test').addEventListener('click', () => {
  const value = normalizeServerUrl(input.value);

  statusEl.textContent = 'Testing...';

  try {
    const ws = new WebSocket(value);

    ws.onopen = () => {
      statusEl.textContent = 'Connected successfully';
      ws.close();
    };

    ws.onerror = () => {
      statusEl.textContent = 'Connection failed';
    };

    ws.onclose = () => {
      setTimeout(() => {
        if (statusEl.textContent === 'Testing...') {
          statusEl.textContent = 'Connection closed';
        }
      }, 100);
    };
  } catch (e) {
    statusEl.textContent = 'Invalid address';
  }
});