import websockets
from configparser import ConfigParser
import os
import asyncio
import subprocess

config_object = ConfigParser()
connected = set()
obs_reciever = set()

PORT = 8000

def get_non_empty_input(prompt):
    while True:
        user_input = input(prompt).strip()
        if user_input:
            return user_input
        else:
            print("Input cannot be empty. Please try again.")


def create_ini_file(config_filename, bot=False):

    if bot:
        token = get_non_empty_input('Enter account token from https://twitchtokengenerator.com/ : ')
        channel = get_non_empty_input('Enter channel name to work with: ')
    else:
        token = 'None'
        channel = 'None'

    print(" ")

    config_object['CHANNEL'] = {'channel_name': channel}
    config_object['TOKEN'] = {'profile_token': token}
    
    with open(config_filename, 'w') as configfile:
        config_object.write(configfile)
    
    print(f"Config file now_playing_conf.ini created.")
    print(" ")


def check_config():
    config_filename = 'now_playing_conf.ini'

    if os.path.exists(config_filename):
        print(f"Config file '{config_filename}' already exists.")
        print("Loading data...")
    else:
        print(f"Config file '{config_filename}' does not exist.")
        create_new = input("Do you want to add a bot? (y/n): ").lower()
        if create_new != 'y':
            create_ini_file(config_filename)
            print(f"You can add bot function manually, just edit config file!")

        else:
            create_new = input("Do you want to create a new config file? (y/n): ").lower()

            if create_new == 'y':
                create_ini_file(config_filename, bot=True)
            else:
                print("No config file created...")
                print("Copy existing config file (with name now_playing_conf.ini) or create new...")

                return False
    
    config_object.read(config_filename)
    
    print("Current config:")
    for section in config_object.sections():
        for key, value in config_object[section].items():
            print(f"{key}: {value}")

    print(" ")
    print("Config loaded...")
    print(" ")
    return True


# The main behavior function for this server
async def echo(websocket):
    global obs_reciever, connected, current_track
    # Handle incoming messages
    try:
        async for message in websocket:
            if message == 'obs-source':
                obs_reciever.add(websocket)
                print(" Source in OBS connected")

            elif 'twitch' in message:
                obs_reciever.add(websocket)
                print(" Twitch bot connected")
                
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


loop = asyncio.get_event_loop()

# Start the server and bot
result = check_config()
if result:
    if config_object['TOKEN']['profile_token'] != 'None':
        command = ["python", 'background_bot.py', config_object['TOKEN']['profile_token'], config_object['CHANNEL']['channel_name']]
        bot_script = subprocess.Popen(command, stderr=subprocess.DEVNULL)
    else:
        print('Server runs without bot...')

else:
    print('Without config, server will work without bot option...')
    print(" ")

print("Server listening on Port " + str(PORT))
start_server = websockets.serve(echo, "localhost", PORT)
loop.run_until_complete(start_server)
loop.run_forever()