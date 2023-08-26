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
    var hostname = window.location.hostname;
    const FETCH_URL = 'ws://localhost:8000/';
	var count = 0
	var join_retry_time = 4000



    function join() {
        conn = new WebSocket(FETCH_URL);

        conn.addEventListener('open', function (event) {
            console.log('Connection Established');
			count = 0;
            conn.send("connected - " + hostname);
            start_transfer();
            if(join_interval){
                clearTimeout(join_interval);
                join_interval = null;
            };
        });

        conn.addEventListener('close', function () {
            console.log("Connection closed, retrying...");
			count += 1;
            clearTimeout(join_interval);
            clearInterval(transfer_interval);
			if(count % 20 === 0){
				join_retry_time *= 2;
			}
            join_interval = setTimeout(function(){join()}, join_retry_time);
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
            // TODO: maybe add more?
            if (hostname === 'soundcloud.com') {

                let status = query('.playControl', e => e.classList.contains('playing') ? "playing" : "stopped", 'unknown');
                let cover = query('.playbackSoundBadge span.sc-artwork', e => e.style.backgroundImage.slice(5, -2).replace('t50x50','t500x500'));
                let title = query('.playbackSoundBadge__titleLink', e => e.title);
                let artists = [ query('.playbackSoundBadge__lightLink', e => e.title) ];
                let progress = query('.playbackTimeline__timePassed span:nth-child(2)', e => timestamp_to_ms(e.textContent));
                let duration = query('.playbackTimeline__duration span:nth-child(2)', e => timestamp_to_ms(e.textContent));
				let song_link = document.getElementsByClassName('playbackSoundBadge__avatar')[0].href.split('?')[0];

                if (title !== null && status == "playing") {
                    conn.send(JSON.stringify({cover, title, artists, status, progress, duration, song_link }));
                }

            } else if (hostname === 'open.spotify.com') {

                let data = navigator.mediaSession;
                let status = query('.vnCew8qzJq3cVGlYFXRI', e => e === null ? 'stopped' : (e.getAttribute('aria-label') === 'Play' || e.getAttribute('aria-label') === 'Слушать' ? 'stopped' : 'playing'));
                let cover = data.metadata.artwork[0].src;
                let title = data.metadata.title
                let artists = [data.metadata.artist]
                let progress = query('.playback-bar__progress-time-elapsed', e => timestamp_to_ms(e.textContent));
                let duration = query('.npFSJSO1wsu3mEEGb5bh', e => timestamp_to_ms(e.textContent));
				let song_link = 'https://open.spotify.com/track/' + decodeURIComponent(document.querySelectorAll('a[aria-label][data-context-item-type="track"]')[0].href).split(':').slice(-1)[0];
				

                if (title !== null && status == "playing") {
                    conn.send(JSON.stringify({ cover, title, artists, status, progress, duration, song_link }));
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
                let cover = navigator.mediaSession.metadata.artwork[0].src;
                let status = navigator.mediaSession.playbackState;
				let song_link = window.location.href.split('&')[0];


                if (title !== null) {
                    title = title.replace(`${artists.join(", ")} - `, "");
                    title = title.replace(` - ${artists.join(", ")}`, "");
                    title = title.replace(`${artists.join(", ")}`, "");
                    title = title.replace("(Official Audio)", "");
                    title = title.replace("(Official Music Video)", "");
                    title = title.replace("(Original Video)", "");
                    title = title.replace("(Original Mix)", "");
                    title = title.replace(",", "");

                    if (status == 'playing' && progress > 0) {
                        conn.send(JSON.stringify({ cover, title, artists, status, progress: Math.floor(progress), duration, song_link }));
                    }
                }
            } else if (hostname === 'music.youtube.com') {
                if (!navigator.mediaSession.metadata) // if nothing is playing we don't submit anything, otherwise having two youtube tabs open causes issues
                    return;

                let time = query('.ytmusic-player-bar.time-info', e => e.innerText.split(" / "));

                let status = query('#play-pause-button', e => e === null ? 'stopped' : (e.getAttribute('aria-label') === 'Play' || e.getAttribute('aria-label') === 'Воспроизвести' ? 'stopped' : 'playing'));

                let title = document.getElementsByClassName("title style-scope ytmusic-player-bar")[0].innerHTML;
                let artists = [navigator.mediaSession.metadata.artist];
                let artwork = navigator.mediaSession.metadata.artwork;
                let cover = artwork[artwork.length - 1].src;
                let progress = timestamp_to_ms(time[0]);
                let duration = timestamp_to_ms(time[1]);
				let lnk = navigator.mediaSession.metadata.artwork[0].src;
				let song_link = 'https://www.youtube.com/watch?v=' + lnk.substring(
					lnk.indexOf("vi/") + 3, 
					lnk.lastIndexOf("/sddefault")
				);

                if (title !== null && status == 'playing') {
                    conn.send(JSON.stringify({ cover, title, artists, status, progress, duration, song_link }));
                }
            }
        }, 500);
    }

    if (hostname === 'soundcloud.com' || hostname === 'music.youtube.com' || hostname === 'www.youtube.com' || hostname === 'open.spotify.com'){
        join();
    };

    window.addEventListener('beforeunload', function (e) {
		if(conn.readyState == WebSocket.OPEN){
			conn.send("closed - " + hostname);
		}
    });


})();
