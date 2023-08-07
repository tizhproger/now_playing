// ==UserScript==
// @name         Now Playing script
// @namespace    univrsal
// @version      1.0.18
// @description  Get song information from web players, based on NowSniper by Kıraç Armağan Önal
// @author       univrsal
// @require      https://unpkg.com/peerjs@1.3.1/dist/peerjs.min.js
// @require      https://code.jquery.com/jquery-3.6.0.min.js
// @match        *://open.spotify.com/*
// @match        *://soundcloud.com/*
// @match        *://*.youtube.com/*
// @grant        unsafeWindow
// @license      GPLv2
// ==/UserScript==

(function() {

    var conn = null;
    var transfer_interval = null;
    var join_interval = null;
    const FETCH_URL = 'ws://localhost:8000/';



    function join() {
        conn = new WebSocket(FETCH_URL);

        conn.addEventListener('open', function (event) {
            console.log('Connection Established')
            start_transfer();
            if(join_interval){
                clearTimeout(join_interval);
                join_interval = null;
            };
        });

        conn.addEventListener('message', function (event) {
            console.log(event.data);
        });

        conn.addEventListener('close', function () {
            console.log("Connection closed, retrying...");
            clearTimeout(join_interval);
            clearInterval(transfer_interval);
            join_interval = setTimeout(function(){join()}, 4000);
        });
    };


    function query(target, fun, alt = null) {
        var element = document.querySelector(target);
        if (element !== null) {
            return fun(element);
        }
        return alt;
    };

    function timestamp_to_ms(ts) {
        var splits = ts.split(':');
        if (splits.length == 2) {
            return splits[0] * 60 * 1000 + splits[1] * 1000;
        } else if (splits.length == 3) {
            return splits[0] * 60 * 60 * 1000 + splits[1] * 60 * 1000 + splits[0] * 1000;
        }
        return 0;
    };

    function start_transfer(){
        transfer_interval = setInterval(()=>{
            let hostname = window.location.hostname;
            // TODO: maybe add more?
            if (hostname === 'soundcloud.com') {

                let status = query('.playControl', e => e.classList.contains('playing') ? "playing" : "stopped", 'unknown');
                let cover = query('.playbackSoundBadge span.sc-artwork', e => e.style.backgroundImage.slice(5, -2).replace('t50x50','t500x500'));
                let title = query('.playbackSoundBadge__titleLink', e => e.title);
                let artists = [ query('.playbackSoundBadge__lightLink', e => e.title) ];
                let progress = query('.playbackTimeline__timePassed span:nth-child(2)', e => timestamp_to_ms(e.textContent));
                let duration = query('.playbackTimeline__duration span:nth-child(2)', e => timestamp_to_ms(e.textContent));
                let album_url = query('.playbackSoundBadge__titleLink', e => e.href);
                let album = null;
                // this header only exists on album/set pages so we know this is a full album
                album = query('.fullListenHero .soundTitle__title', e => {
                    album_url = window.location.href;
                    return e.innerText
                })

                album = query('div.playlist.playing', e => {
                    return e.getElementsByClassName('soundTitle__title')[0].innerText;
                })

                if (title !== null && status == "playing") {
                    conn.send(JSON.stringify({cover, title, artists, status, progress, duration, album_url, album}));
                }

            } else if (hostname === 'open.spotify.com') {

                let data = navigator.mediaSession;
                let album = data.metadata.album;
                let status = query('.vnCew8qzJq3cVGlYFXRI', e => e === null ? 'stopped' : (e.getAttribute('aria-label') === 'Play' || e.getAttribute('aria-label') === 'Слушать' ? 'stopped' : 'playing'));
                let cover = data.metadata.artwork[0].src;
                let title = data.metadata.title
                let artists = [data.metadata.artist]
                let progress = query('.playback-bar__progress-time-elapsed', e => timestamp_to_ms(e.textContent));
                let duration = query('.npFSJSO1wsu3mEEGb5bh', e => timestamp_to_ms(e.textContent));


                if (title !== null && (status == "playing" || status == "playing")) {
                    conn.send(JSON.stringify({ cover, title, artists, status, progress, duration, album }));
                }
            } else if (hostname === 'www.youtube.com') {
                if (!navigator.mediaSession.metadata) // if nothing is playing we don't submit anything, otherwise having two youtube tabs open causes issues
                    return;
                let artists = [];

                try {
                    artists = [ document.querySelector('div#upload-info').querySelector('a').innerText.trim().replace("\n", "") ];
                } catch(e) {}

                let title = query('.style-scope.ytd-video-primary-info-renderer', e => {
                    let t = e.getElementsByClassName('title');
                    if (t && t.length > 0)
                        return t[0].innerText;
                    return "";
                });
                let duration = query('video', e => e.duration * 1000);
                let progress = query('video', e => e.currentTime * 1000);
                let cover = "";
                let status = query('video', e => e.paused ? 'stopped' : 'playing', 'unknown');
                let regExp = /^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
                let match = window.location.toString().match(regExp);
                if (match && match[2].length == 11) {
                    cover = `https://i.ytimg.com/vi/${match[2]}/maxresdefault.jpg`;
                }


                if (title !== null) {
                    title = title.replace(`${artists.join(", ")} - `, "");
                    title = title.replace(` - ${artists.join(", ")}`, "");
                    title = title.replace(`${artists.join(", ")}`, "");
                    title = title.replace("(Official Audio)", "");
                    title = title.replace("(Official Music Video)", "");
                    title = title.replace("(Original Video)", "");
                    title = title.replace("(Original Mix)", "");

                    if (status !== 'stopped') {
                        conn.send(JSON.stringify({ cover, title, artists, status, progress: Math.floor(progress), duration }));
                    }
                }
            } else if (hostname === 'music.youtube.com') {
                if (!navigator.mediaSession.metadata) // if nothing is playing we don't submit anything, otherwise having two youtube tabs open causes issues
                    return;
                // Youtube Music support by Rubecks
                const artistsSelectors = [
                    '.ytmusic-player-bar.byline [href*="channel/"]:not([href*="channel/MPREb_"]):not([href*="browse/MPREb_"])', // Artists with links
                    '.ytmusic-player-bar.byline .yt-formatted-string:nth-child(2n+1):not([href*="browse/"]):not([href*="channel/"]):not(:nth-last-child(1)):not(:nth-last-child(3))', // Artists without links
                    '.ytmusic-player-bar.byline [href*="browse/FEmusic_library_privately_owned_artist_detaila_"]', // Self uploaded music
                ];
                const albumSelectors = [
                    '.ytmusic-player-bar [href*="browse/MPREb_"]', // Albums from YTM with links
                    '.ytmusic-player-bar [href*="browse/FEmusic_library_privately_owned_release_detailb_"]', // Self uploaded music
                ];
                let time = query('.ytmusic-player-bar.time-info', e => e.innerText.split(" / "));

                let status = query('#play-pause-button', e => e === null ? 'stopped' : (e.getAttribute('aria-label') === 'Play' || e.getAttribute('aria-label') === 'Воспроизвести' ? 'stopped' : 'playing'));

                let title = query('.ytmusic-player-bar.title', e => e.title);
                let artists = Array.from(document.querySelectorAll(artistsSelectors)).map(x => x.innerText);
                let album = query(albumSelectors, e => e.textContent);
                let artwork = navigator.mediaSession.metadata.artwork;
                let cover = artwork[artwork.length - 1].src;
                let album_url = query(albumSelectors, e => e.href);
                let progress = timestamp_to_ms(time[0]);
                let duration = timestamp_to_ms(time[1]);

                if (title !== null && status == 'playing') {
                    conn.send(JSON.stringify({ cover, title, artists, status, progress, duration, album_url, album }));
                }
            }
        }, 500);
    }

    function delay(time) {
        return new Promise(resolve => setTimeout(resolve, time));
    }


    join();

})();