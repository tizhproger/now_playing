import websockets
import asyncio

clients = set()
recievers = set()
exit = ''

# The main behavior function for this server
async def echo(websocket):
    global recievers, clients, gui_reciever
    # Handle incoming messages
    try:
        async for message in websocket:
            if message == 'obs-source' and websocket not in recievers:
                recievers.add(websocket)
                print("Source in OBS connected")

            elif 'twitch' in message and websocket not in recievers:
                recievers.add(websocket)
                print("Twitch bot connected")
                
            elif 'connected - ' in message and websocket not in clients:
                print(message.split('-')[1] + " was connected")
                if websocket not in clients:
                    clients.add(websocket)
                
            elif 'closed - ' in message and websocket not in clients:
                print(message.split('-')[1] + " was closed/reloaded")
                if websocket in clients:
                    clients.remove(websocket)
                
            else:
                if len(recievers) > 0:
                    for reciever in recievers:
                        if reciever.open and reciever != websocket:
                            await reciever.send(message)

    # Handle disconnecting clients 
    except websockets.exceptions.ConnectionClosed as e:
        print("A client just disconnected")
    finally:
        if websocket in clients:
            clients.remove(websocket)


async def echo_server(ipaddress, port, exit_):
    async with websockets.serve(echo, ipaddress, port):
        await exit_


def run_webserver(ipaddress, port):
    global exit

    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()

    try:
        print("Server listening on Port " + str(port))
        exit = asyncio.Future()
        loop.create_task(echo_server(ipaddress, port, exit))
        loop.run_forever()
        loop.close()
    except Exception as e:
            print('Server error - ' + str(e))


def close_webserver():
    global exit

    exit.set_result('exit')
