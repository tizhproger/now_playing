import websockets
import asyncio

# Server data
PORT = 8000
print("Server listening on Port " + str(PORT))

# A set of connected ws clients
connected = set()
obs_reciever = ''

# The main behavior function for this server
async def echo(websocket):
    global obs_reciever
    print("A client just connected")
    # Store a copy of the connected client
    connected.add(websocket)
    # Handle incoming messages
    try:
        async for message in websocket:
            print("Received message from client: " + message)
            if message == 'obs-source':
                obs_reciever = websocket
            else:
                if obs_reciever != websocket and obs_reciever != '':
                    if obs_reciever.open:
                        await obs_reciever.send(message)

    # Handle disconnecting clients 
    except websockets.exceptions.ConnectionClosed as e:
        print("A client just disconnected")
    finally:
        connected.remove(websocket)

# Start the server
start_server = websockets.serve(echo, "localhost", PORT)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()