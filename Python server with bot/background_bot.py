from twitchio.ext import commands
import sys
import websockets


class Bot(commands.Bot):

    def __init__(self, acc_token, channel):
        # Initialise our Bot with our access token, prefix and a list of channels to join on boot...
        super().__init__(token=acc_token, prefix='!', initial_channels=[channel])
        self._song = ''


    async def websocket_client(self):
        uri = "ws://localhost:8000/"  # Replace with the WebSocket server URI
        async with websockets.connect(uri) as websocket:
            await websocket.send('connected - twitch bot')
            while True:
                self._song = await websocket.recv()


    async def event_ready(self):
        # We are logged in and ready to chat and use commands...
        print(" ")
        print("Logging to twitch profile...")
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')
        print(" ")
        await self.websocket_client()


    @commands.command(name='song', aliases=['трек', 'песня', 'track'])
    async def song(self, ctx: commands.Context):
        data = eval(self._song)
        text = ''
        if 'google' in data['cover']:
            text = 'Сори, только название: ' + ','.join(data['artists']) + ' - ' + data['title']

        else:
            text = 'Текущий трек: ' + ','.join(data['artists']) + ' - ' + data['title'] + '  ' + data['song_link']

        await ctx.send(f"@{ctx.author.name} {text}")
    

    @commands.command(name='ping')
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"@{ctx.author.name} Я жив!")


if __name__ == "__main__":
    token = sys.argv[1]
    channel = sys.argv[2]
    bot = Bot(token, channel)
    bot.run()