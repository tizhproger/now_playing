import websockets
import asyncio

# Server data
PORT = 8000
print("Server listening on Port " + str(PORT))

# A set of connected ws clients
connected = set()
obs_reciever = set()

# The main behavior function for this server
async def echo(websocket):
    global obs_reciever, connected
    # Store a copy of the connected client
    
    # Handle incoming messages
    try:
        async for message in websocket:
            if message == 'obs-source':
                obs_reciever.add(websocket)
                print("Source in OBS connected")
                
            elif 'connected - ' in message:
                print(message.split('-')[1] + " tab was connected")
                if websocket not in connected:
                    connected.add(websocket)
                
            elif 'closed - ' in message:
                print(message.split('-')[1] + " tab was closed/reloaded")
                if websocket in connected:
                    connected.remove(websocket)
                
            else:
                if len(obs_reciever) > 0:
                    for obs in obs_reciever:
                        if obs.open and obs != websocket:
                            await obs.send(message)

    # Handle disconnecting clients 
    except websockets.exceptions.ConnectionClosed as e:
        print("A client just disconnected")
    finally:
        if websocket in connected:
            connected.remove(websocket)

# Start the server
start_server = websockets.serve(echo, "localhost", PORT)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
