import os
import certifi
from twitchio.ext import commands
import asyncio
import websockets


exit = ''

class Bot(commands.Bot):

    def __init__(self, acc_token, channel, ip, port):
        # Initialise our Bot with our access token, prefix and a list of channels to join on boot...
        super().__init__(token=acc_token, prefix='!', initial_channels=[channel])
        self._song = ''
        self.uri = f"ws://{ip}:{port}/"
    

    async def websocket_client(self):
        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    await websocket.send('connected - twitch bot')
                    while True:
                        self._song = await websocket.recv()
            except:
                await asyncio.sleep(2)


    async def event_ready(self):
        # We are logged in and ready to chat and use commands...
        print(' ')
        print("Logging to twitch profile...")
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id} \n')
        await self.websocket_client()


    @commands.command(name='song', aliases=['трек', 'песня', 'track'])
    async def song(self, ctx: commands.Context):
        text = ''
        if self._song == '':
            text = 'Пока не знаю, нужно ждать...'

        else:
            data = eval(self._song)
            if 'google' in data['cover']:
                text = 'Сори, только название: ' + ','.join(data['artists']) + ' - ' + data['title']

            else:
                text = 'Текущий трек: ' + ','.join(data['artists']) + ' - ' + data['title'] + '  ' + data['song_link']

        await ctx.send(f"@{ctx.author.name} {text}")
        self._song = ''
    

    @commands.command(name='ping')
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"@{ctx.author.name} Я жив!")


async def starting(token, channel, ipaddress, port, exit_):
        tb = Bot(token, channel, ipaddress, port)
        await tb.connect()
        await exit_
        await tb.close()

def run_bot(token, channel, ipaddress, port):
    global exit

    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    try:
        exit = asyncio.Future()
        loop.create_task(starting(token, channel, ipaddress, port, exit))
        loop.run_forever()
        loop.close()
    except Exception as e:
            print('Bot error - ' + str(e))


def close_bot():
    global exit
    exit.set_result('exit')
