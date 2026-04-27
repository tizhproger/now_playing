// background.js

const DEFAULT_SERVER_URL = 'ws://localhost:8000';

let serverUrl = DEFAULT_SERVER_URL;
let ws = null;
let reconnectTimer = null;
let keepAliveTimer = null;

function bgLog(...args) {
  console.log('[NowPlaying BG]', ...args);
}

function normalizeServerUrl(url) {
  const value = String(url || '').trim();
  if (!value) return DEFAULT_SERVER_URL;
  if (!value.startsWith('ws://') && !value.startsWith('wss://')) {
    return DEFAULT_SERVER_URL;
  }
  return value;
}

function scheduleReconnect() {
  if (reconnectTimer) return;

  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connectWs();
  }, 2000);
}

function startKeepAlive() {
  if (keepAliveTimer) return;

  keepAliveTimer = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ type: 'ping' }));
      } catch (e) {
        bgLog('keepalive failed:', e);
      }
    }
  }, 20000);
}

function connectWs() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  bgLog('connecting to', serverUrl);

  try {
    ws = new WebSocket(serverUrl);
  } catch (e) {
    bgLog('WebSocket create error:', e);
    ws = null;
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    bgLog('connected:', serverUrl);
    try {
      ws.send('connected - extension-background');
    } catch (_) {}

    startKeepAlive();
  };

  ws.onmessage = () => {};

  ws.onerror = (e) => {
    bgLog('ws error:', e);
  };

  ws.onclose = (e) => {
    bgLog('closed:', e.code, e.reason || '');
    ws = null;
    scheduleReconnect();
  };
}

function reconnectWs() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  if (ws) {
    try {
      ws.close();
    } catch (_) {}
    ws = null;
  }

  connectWs();
}

function sendToServer(payload) {
  if (!payload) return;

  if (!ws || ws.readyState !== WebSocket.OPEN) {
    connectWs();

    setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify(payload));
        } catch (e) {
          bgLog('delayed send failed:', e);
        }
      }
    }, 300);

    return;
  }

  try {
    ws.send(JSON.stringify(payload));
  } catch (e) {
    bgLog('send failed:', e);
    reconnectWs();
  }
}

function loadServerUrlAndConnect() {
	chrome.storage.sync.get({ serverUrl: DEFAULT_SERVER_URL }, ({ serverUrl: savedUrl }) => {
	  serverUrl = normalizeServerUrl(savedUrl);
	  bgLog('using server URL:', serverUrl);
	});
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'np-set-server',
    title: 'Now Playing: задать адрес сервера',
    contexts: ['page']
  });

  chrome.contextMenus.create({
    id: 'np-show-server',
    title: 'Now Playing: показать адрес сервера',
    contexts: ['page']
  });
  
  chrome.contextMenus.create({
    id: 'np-open-options',
    title: 'Now Playing: настройки',
    contexts: ['page']
  });

  chrome.storage.sync.get({ serverUrl: DEFAULT_SERVER_URL }, ({ serverUrl: savedUrl }) => {
    if (!savedUrl) {
      chrome.storage.sync.set({ serverUrl: DEFAULT_SERVER_URL });
    }
  });
});


chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (!tab || tab.id == null) return;

  if (info.menuItemId === 'np-set-server') {
    chrome.storage.sync.get({ serverUrl: DEFAULT_SERVER_URL }, ({ serverUrl: savedUrl }) => {
      chrome.tabs.sendMessage(tab.id, {
        type: 'NP_SET_SERVER',
        current: normalizeServerUrl(savedUrl)
      });
    });
  }

  if (info.menuItemId === 'np-show-server') {
    chrome.storage.sync.get({ serverUrl: DEFAULT_SERVER_URL }, ({ serverUrl: savedUrl }) => {
      chrome.tabs.sendMessage(tab.id, {
        type: 'NP_SHOW_SERVER',
        current: normalizeServerUrl(savedUrl)
      });
    });
  }
  
  if (info.menuItemId === 'np-open-options') {
    chrome.runtime.openOptionsPage();
  }
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || !msg.type) return;

  if (msg.type === 'NP_TRACK_UPDATE') {
	  bgLog('track update from content script:', msg.host, msg.payload?.title);
	  sendToServer(msg.payload);
	  sendResponse({ ok: true });
	  return true;
	}

  if (msg.type === 'NP_SAVE_SERVER') {
    const nextUrl = normalizeServerUrl(msg.value);

    chrome.storage.sync.set({ serverUrl: nextUrl }, () => {
      serverUrl = nextUrl;
      bgLog('server URL saved:', serverUrl);
      reconnectWs();
      sendResponse({ ok: true, serverUrl });
    });

    return true;
  }

  if (msg.type === 'NP_GET_SERVER') {
    sendResponse({ serverUrl });
  }
});

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== 'sync' || !changes.serverUrl) return;

  const nextUrl = normalizeServerUrl(changes.serverUrl.newValue);
  if (nextUrl !== serverUrl) {
    serverUrl = nextUrl;
    bgLog('server URL changed:', serverUrl);
    reconnectWs();
  }
});