import websockets
import sys
import asyncio

clients = set()
recievers = set()
gui_reciever = ''

# The main behavior function for this server
async def echo(websocket):
    global recievers, clients, gui_reciever
    # Handle incoming messages
    try:
        async for message in websocket:
            if message == 'obs-source':
                recievers.add(websocket)
                await gui_message("Source in OBS connected")
                print("Source in OBS connected")

            elif 'twitch' in message:
                recievers.add(websocket)
                await gui_message("Twitch bot connected")
                print("Twitch bot connected")
            
            elif 'gui' in message:
                gui_reciever = websocket
                await gui_message("GUI connected")
                print("GUI connected")
                
            elif 'connected - ' in message:
                print(message.split('-')[1] + " was connected")
                await gui_message(message.split('-')[1] + " was connected")
                if websocket not in clients:
                    clients.add(websocket)
                
            elif 'closed - ' in message:
                print(message.split('-')[1] + " was closed/reloaded")
                await gui_message(message.split('-')[1] + " was closed/reloaded")
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
    

async def gui_message(message):
    await gui_reciever.send(message)


def run(ipaddress, port):
    loop = asyncio.get_event_loop()

    try:
        print("Server listening on Port " + str(port))
        start_server = websockets.serve(echo, ipaddress, port)
        loop.run_until_complete(start_server)
        loop.run_forever()
    except Exception as e:
            print('Server error - ' + str(e))
    

if __name__ == "__main__":
    ip_address = sys.argv[1]
    port = sys.argv[2]
    run(ip_address, port)