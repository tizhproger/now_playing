// nowplaying_client.js

const hostname = window.location.hostname;

const SUPPORTED_HOSTS = [
  'soundcloud.com',
  'www.soundcloud.com',
  'music.youtube.com',
  'www.youtube.com',
  'open.spotify.com'
];

const shouldRun = SUPPORTED_HOSTS.includes(hostname);

let transferInterval = null;

function npLog(...args) {
  console.log('[NowPlaying CS]', ...args);
}

function query(selector, fn, alt = null) {
  const el = document.querySelector(selector);
  if (!el) return alt;
  try {
    return fn(el);
  } catch (_) {
    return alt;
  }
}

function timestamp_to_ms(ts) {
  if (!ts) return 0;

  ts = String(ts).trim();
  const parts = ts.split(':').map(Number);

  if (parts.some(isNaN)) return 0;

  if (parts.length === 2) {
    const [m, s] = parts;
    return (m * 60 + s) * 1000;
  }

  if (parts.length === 3) {
    const [h, m, s] = parts;
    return (h * 3600 + m * 60 + s) * 1000;
  }

  return 0;
}

function sendTrackUpdate(payload) {
  if (!payload) return;

  if (!payload.title || payload.status !== 'playing') {
    return;
  }

  try {
    chrome.runtime.sendMessage(
      {
        type: 'NP_TRACK_UPDATE',
        host: hostname,
        payload
      },
      (response) => {
        if (chrome.runtime.lastError) {
          console.log('[NowPlaying CS] sendMessage error:', chrome.runtime.lastError.message);
          return;
        }
      }
    );
  } catch (e) {
    console.log('[NowPlaying CS] sendMessage failed:', e);
  }
}

function collectSoundCloud() {
  const status = query('.playControl', e =>
    e.classList.contains('playing') ? 'playing' : 'stopped', 'unknown');

  const cover = query('.playbackSoundBadge span.sc-artwork', e =>
    e.style.backgroundImage
      ? e.style.backgroundImage.slice(5, -2).replace('t50x50', 't500x500')
      : '', '');

  const title = query('.playbackSoundBadge__titleLink', e => e.title || '');
  const artists = [query('.playbackSoundBadge__lightLink', e => e.title || '', '')];

  const progress = query('.playbackTimeline__timePassed span:nth-child(2)',
    e => timestamp_to_ms(e.textContent), 0);

  const duration = query('.playbackTimeline__duration span:nth-child(2)',
    e => timestamp_to_ms(e.textContent), 0);

  let song_link = '';
  const avatars = document.getElementsByClassName('playbackSoundBadge__avatar');
  if (avatars.length > 0) {
    song_link = avatars[0].href.split('?')[0];
  }

  return { cover, title, artists, status, progress, duration, song_link };
}

function collectSpotify() {
  const playBtnLabel = query(
    '[data-testid="control-button-playpause"]',
    e => e.getAttribute('aria-label') || '',
    ''
  );

  const status = (playBtnLabel === 'Play' || playBtnLabel === 'Слушать')
    ? 'stopped'
    : 'playing';

  let cover = '';
  let title = '';
  let artists = [''];

  if (navigator.mediaSession && navigator.mediaSession.metadata) {
    const md = navigator.mediaSession.metadata;

    if (md.artwork && md.artwork.length) {
      cover = md.artwork[md.artwork.length - 1].src;
    }

    title = md.title || '';
    artists = [md.artist || ''];
  }

  const progress = query('[data-testid="playback-position"]',
    e => timestamp_to_ms(e.textContent), 0);

  const duration = query('[data-testid="playback-duration"]',
    e => timestamp_to_ms(e.textContent), 0);

  let song_link = '';
  const trackLinks = document.querySelectorAll('a[aria-label][data-context-item-type="track"]');

  if (trackLinks.length > 0) {
    const href = decodeURIComponent(trackLinks[0].href || '');
    const parts = href.split(':');
    song_link = 'https://open.spotify.com/track/' + parts[parts.length - 1];
  }

  return { cover, title, artists, status, progress, duration, song_link };
}

function collectYouTube() {
  const video = document.querySelector('video');
  if (!video || !isFinite(video.duration) || video.duration === 0) return null;

  const status = video.paused ? 'stopped' : 'playing';
  const progress = Math.floor(video.currentTime * 1000);
  const duration = Math.floor(video.duration * 1000);

  let title = '';
  let artists = [''];
  let cover = '';

  if (navigator.mediaSession && navigator.mediaSession.metadata) {
    const md = navigator.mediaSession.metadata;
    title = md.title || '';
    artists = [md.artist || ''];

    if (md.artwork && md.artwork.length) {
      cover = md.artwork[md.artwork.length - 1].src;
    }
  }

  if (!title) {
    title =
      document.querySelector('h1.ytd-watch-metadata yt-formatted-string')?.textContent?.trim() ||
      document.querySelector('h1.title yt-formatted-string')?.textContent?.trim() ||
      document.title.replace(' - YouTube', '').trim();
  }

  if (!artists[0]) {
    artists = [
      document.querySelector('#owner #channel-name a')?.textContent?.trim() ||
      document.querySelector('ytd-channel-name a')?.textContent?.trim() ||
      ''
    ];
  }

  const url = new URL(location.href);
  const videoId = url.searchParams.get('v');
  const song_link = videoId ? 'https://www.youtube.com/watch?v=' + videoId : location.href;

  if (!cover && videoId) {
    cover = 'https://i.ytimg.com/vi/' + videoId + '/hqdefault.jpg';
  }

  return { cover, title, artists, status, progress, duration, song_link };
}

function collectYouTubeMusic() {
  if (!navigator.mediaSession || !navigator.mediaSession.metadata) return null;

  const time = query('.ytmusic-player-bar.time-info', e => e.innerText.split(' / '), null);
  if (!time || time.length < 2) return null;

  const btnStatus = query('#play-pause-button', e =>
    (e.getAttribute('aria-label') === 'Play' || e.getAttribute('aria-label') === 'Воспроизвести')
      ? 'stopped'
      : 'playing',
    'unknown'
  );

  const md = navigator.mediaSession.metadata;

  const title = md.title || '';
  const artists = [md.artist || ''];

  let cover = '';
  if (md.artwork && md.artwork.length) {
    cover = md.artwork[md.artwork.length - 1].src;
  }

  const progress = timestamp_to_ms(time[0]);
  const duration = timestamp_to_ms(time[1]);

  let song_link = '';
  if (md.artwork && md.artwork[0] && md.artwork[0].src) {
    const lnk = md.artwork[0].src;
    if (lnk.includes('vi/') && lnk.includes('/sddefault')) {
      song_link = 'https://www.youtube.com/watch?v=' +
        lnk.substring(lnk.indexOf('vi/') + 3, lnk.lastIndexOf('/sddefault'));
    }
  }

  return {
    cover,
    title,
    artists,
    status: btnStatus,
    progress,
    duration,
    song_link
  };
}

function collectAndSend() {
  try {
    let payload = null;

    if (hostname === 'soundcloud.com' || hostname === 'www.soundcloud.com') {
      payload = collectSoundCloud();
    } else if (hostname === 'open.spotify.com') {
      payload = collectSpotify();
    } else if (hostname === 'www.youtube.com') {
      payload = collectYouTube();
    } else if (hostname === 'music.youtube.com') {
      payload = collectYouTubeMusic();
    }

    if (payload) {
      sendTrackUpdate(payload);
    }
  } catch (e) {
    npLog('collect error:', e);
  }
}

function startTransfer() {
  if (!shouldRun || transferInterval) return;

  npLog('content script started on', hostname);

  transferInterval = setInterval(collectAndSend, 500);
}

// Меню настроек сервера: prompt / alert остаются в content script,
// потому что background service worker не может показывать prompt.
try {
  chrome.runtime.onMessage.addListener((msg) => {
    if (!msg || !msg.type) return;

    if (msg.type === 'NP_SET_SERVER') {
      const current = msg.current || 'ws://127.0.0.1:8000';
      const value = prompt(
        'Введите адрес WebSocket сервера Now Playing (например ws://127.0.0.1:8000):',
        current
      );

      if (value) {
        chrome.runtime.sendMessage({
          type: 'NP_SAVE_SERVER',
          value: value.trim()
        });
      }
    }

    if (msg.type === 'NP_SHOW_SERVER') {
      alert('Текущий адрес сервера Now Playing:\n' + (msg.current || 'ws://127.0.0.1:8000'));
    }
  });
} catch (_) {}

startTransfer();
