import os
import re
import certifi
import time
from twitchio.ext import commands
import asyncio
import websockets
import json


exit = ''

class Bot(commands.Bot):
    
    song_cmds = {"song"}
    _song_raw = ""

    def __init__(self, acc_token, channel, ip, port,
                 song_commands, reply_playing, reply_other, reply_empty, reply_error):
        super().__init__(token=acc_token, prefix='!', initial_channels=[channel])

        self.uri = f"ws://{ip}:{port}/"
        self.song_cmds  = self.parse_commands(song_commands)
        self._song_raw = ""
        self._last_update_ts = 0.0
        self._stale_after_sec = 4.0

        self.reply_playing = reply_playing
        self.reply_other   = reply_other
        self.reply_empty   = reply_empty
        self.reply_error   = reply_error

        self.last_data = None
    

    async def websocket_client(self):
        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    await websocket.send('connected - twitch bot')
                    while True:
                        self._song_raw = await websocket.recv()
                        self._last_update_ts = time.monotonic()
                        try:
                            self.last_data = json.loads(self._song_raw)
                        except Exception:
                            self.last_data = None
            except:
                await asyncio.sleep(2)


    async def event_ready(self):
        # We are logged in and ready to chat and use commands...
        print(' ')
        print("Logging to twitch profile...")
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id} \n')
        asyncio.create_task(self.websocket_client())

    def parse_commands(self, value: str):
        if not value:
            return ['song']
        parts = re.split(r"[,\s]+", value.strip())
        out = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if p.startswith('!'):
                p = p[1:]
            out.append(p.lower())
        return list(dict.fromkeys(out)) or ['song']

    def template_disabled(self, t: str) -> bool:
        if t is None:
            return True
        s = str(t).strip()
        return s == "" or s.lower() in {"none", "off", "0", "disable", "disabled"}

    def render(self, tpl: str, ctx_user: str, data: dict):
        artists_list = data.get('artists') or []
        artists = ", ".join(artists_list)
        artist = artists_list[0] if artists_list else ""
        title = data.get('title') or "Unknown"
        link = data.get('song_link') or data.get('link') or ""
        status = data.get('status') or ""

        vars = {
            "user": ctx_user,
            "mention": f"@{ctx_user}",
            "artists": artists,
            "artist": artist,
            "title": title,
            "link": link,
            "song_link": link,
            "status": status,
            "progress": str(data.get("progress") or ""),
            "duration": str(data.get("duration") or ""),
        }

        try:
            return tpl.format(**vars).strip()
        except Exception:
            return tpl.strip()


    async def event_message(self, message):
        if message.author is None:
            return

        if getattr(message, "echo", False):
            return

        content = (message.content or "").strip()
        if content.startswith("!"):
            cmd = content[1:].split()[0].lower()
            cmds = getattr(self, "song_cmds", {"song"})

            if cmd in cmds:
                user = message.author.name
                song_raw = getattr(self, "_song_raw", "")
                
                if not song_raw:
                    if not self.template_disabled(self.reply_empty):
                        txt = self.render(self.reply_empty, user, {})
                        if txt:
                            await message.channel.send(txt)
                    return

                try:
                    data = json.loads(song_raw)
                    now = time.monotonic()
                    age = now - float(getattr(self, "_last_update_ts", 0.0) or 0.0)
                    stale = (self._last_update_ts > 0) and (age > self._stale_after_sec)

                    status = (data.get("status") or "").lower()
                    if stale:
                        status = "stopped"
                except Exception:
                    self._song_raw = ""
                    if not self.template_disabled(self.reply_error):
                        txt = self.render(self.reply_error, user, {})
                        if txt:
                            await message.channel.send(txt)
                    return

                tpl = self.reply_playing if status == "playing" else self.reply_other
                if self.template_disabled(tpl):
                    return

                txt = self.render(tpl, user, data)
                if txt:
                    await message.channel.send(txt)
                return
    

    @commands.command(name='ping')
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"@{ctx.author.name} IT'S ALIIIIVE!")


async def starting(token, channel, ipaddress, port, exit_,
                   cmds, rp, ro, re, rerr):
    tb = Bot(token, channel, ipaddress, port, cmds, rp, ro, re, rerr)
    await tb.connect()
    await exit_
    await tb.close()

def run_bot(token, channel, ipaddress, port, cmds, rp, ro, re, rerr):
    global exit
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    exit = asyncio.Future()
    loop.create_task(starting(token, channel, ipaddress, port, exit, cmds, rp, ro, re, rerr))
    loop.run_forever()


def close_bot():
    global exit
    exit.set_result('exit')
