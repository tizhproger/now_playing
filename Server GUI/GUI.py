from configparser import ConfigParser
from tkinter import messagebox
from tkinter import filedialog
import customtkinter
import os
import sys
import subprocess
import threading
import requests
import websocket

app = customtkinter.CTk()
config_object = ConfigParser()

logs_textbox = ''
config_frame = ''
save_button = ''
run_button = ''
bot_button = ''
logs_frame = ''
reload_button = ''
widgets_button = ''
bot_thread = ''
server_thread = ''
bot_script = ''
server_script = ''
websocket_client = ''
old_stdout = ''
config_filename = 'now_playing_conf.ini'


class RedirectOutput():
    def __init__(self, widget, autoscroll=True):
        self.widget = widget
        self.autoscroll = autoscroll

    def write(self, text):
        self.widget.configure(state="normal")
        self.widget.insert('end', text)
        self.widget.configure(state="disable")
        if self.autoscroll:
            self.widget.see("end")  # autoscroll
    
    def flush(self):
        pass

class WebSocketClient():
    def __init__(self, url, widget):
        self.url = url
        self.messages = []
        self.websocket = None
        self.widget = widget

    def connect(self):
        self.websocket = websocket.WebSocketApp(self.url,
                                                on_message=self.on_message,
                                                on_error=self.on_error,
                                                on_open=self.on_open)
        self.websocket.run_forever()

    def on_message(self, message, tst):
        self.update_messages(tst)

    def on_error(self, error, tst):
        self.connect()

    def on_open(self, arg1):
        self.websocket.send('connected - gui')

    def start(self):
        websocket_thread = threading.Thread(target=self.connect)
        websocket_thread.daemon = True
        websocket_thread.start()
    
    def close(self):
        self.websocket.close()

    def update_messages(self, message):
        self.widget.configure(state='normal')
        self.widget.insert('end', message + '\n')
        self.widget.configure(state='disabled')
        self.widget.see("end")

class ConfigFrame(customtkinter.CTkScrollableFrame):
    def __init__(self, master, title):
        super().__init__(master, label_text=title, width=300, height=250)
        self.grid(row=0, column=0, padx=20, pady=20)
        self.config = ''
        self.config_elements = {}
        self.update()

    def frame_config(self):
        new_config = {}
        for key, value in self.config_elements.items():
            new_config[key] = value.get()

        return new_config
    
    def update(self, values=''):
        if len(self.winfo_children()) > 1:
            for widget in self.winfo_children():
                widget.destroy()

        count = 0
        if values == '':
            self.config = load_config()
        else:
            self.config = values

        for key, k_value in self.config.items():
            if 'autorun' not in key:
                label = customtkinter.CTkLabel(self, text=key, fg_color="transparent")
                entry = customtkinter.CTkEntry(self, textvariable=customtkinter.StringVar(self, k_value))

                label.grid(row=count, column=0, padx=15, pady=5, sticky="w")
                entry.grid(row=count, column=1, padx=10, pady=5, sticky="w")

                self.config_elements[key] = entry

            else:
                label = customtkinter.CTkLabel(self, text=key, fg_color="transparent")
                combobox = customtkinter.CTkComboBox(self, values=["Yes", "No"])
                combobox.set(k_value)

                label.grid(row=count, column=0, padx=15, pady=5, sticky="w")
                combobox.grid(row=count, column=1, padx=10, pady=5, sticky="w")

                self.config_elements[key] = combobox

            count += 1

class AlertWindow(customtkinter.CTkToplevel):
    def __init__(self, text_info, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("400x300")

        self.label = customtkinter.CTkLabel(self, text=text_info)
        self.label.grid(padx=20, pady=20)

        bot_button = customtkinter.CTkButton(self, text='Close', command=self.close_window)
        bot_button.grid(row=1, column=1, pady=5, padx=(45, 0), sticky='w')

        self.focus()
    
    def close_window(self):
        self.destroy()


app.title("Now Playing - OBS (Server)")

window_height = 400
window_width = 800

screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()

x_cordinate = int((screen_width/2) - (window_width/2))
y_cordinate = int((screen_height/2) - (window_height/2))

app.geometry("{}x{}+{}+{}".format(window_width, window_height, x_cordinate, y_cordinate))
app.wm_resizable(False, False)


def load_config():
    config_data = {}
    config_object.read(config_filename)
    
    for section in config_object.sections():
        for key, value in config_object[section].items():
            config_data[key] = value
    
    return config_data


def create_ini_file(config_filename):
    config_object['CHANNEL'] = {'channel_name': ''}
    config_object['TOKEN'] = {'profile_token': ''}
    config_object['CONNECTION'] = {'ip_address': 'localhost', 'port': 8000}
    config_object['AUTORUN'] = {'twitch_bot_autorun': 'No', 'server_autorun': 'No'}
    
    with open(config_filename, 'w') as configfile:
        config_object.write(configfile)
    
    logs_textbox.configure(state="normal")
    logs_textbox.insert('end', 'Config file now_playing_conf.ini created \n')
    logs_textbox.configure(state="disabled")


def check_config():
    if os.path.exists(config_filename):
        logs_textbox.configure(state="normal")
        logs_textbox.insert('end', f"Config file '{config_filename}' already exists \n")
        logs_textbox.insert('end', 'Loading data... \n')
        logs_textbox.configure(state="disabled")

    else:
        logs_textbox.configure(state="normal")
        logs_textbox.insert('end', f"Config file '{config_filename}' does not exist \n")
        logs_textbox.insert('end', 'It will be created automatically with default values... \n')
        logs_textbox.insert('end', 'You can fill it manually, just edit config on the left panel... \n')
        logs_textbox.configure(state="disabled")

        create_ini_file(config_filename)


def save_config():
    config_object.read(config_filename)
    updated_config = config_frame.frame_config()
    if updated_config['twitch_bot_autorun'] not in ['Yes', 'No']:
        messagebox.showinfo("Input error", "Twitch_bot_autorun can have only 'Yes' or 'No' value!")
        logs_textbox.configure(state="normal")
        logs_textbox.insert('end', f"Change twitch_bot_autorun to Yes or No... \n")
        logs_textbox.configure(state="disabled")
        return

    elif updated_config['server_autorun'] not in ['Yes', 'No']:
        messagebox.showinfo("Input error", "Server_autorun can have only 'Yes' or 'No' value!")
        logs_textbox.configure(state="normal")
        logs_textbox.insert('end', f"Change server_autorun to Yes or No... \n")
        logs_textbox.configure(state="disabled")
        return
    
    for section in config_object.sections():
        for key in config_object[section].keys():
            config_object.set(section, key, updated_config[key])
    
    with open(config_filename, 'w') as configfile:
        config_object.write(configfile)
    
    logs_textbox.configure(state="normal")
    logs_textbox.insert('end', f"Config file '{config_filename}' updated... \n")
    logs_textbox.configure(state="disabled")


def bot_function():
    global bot_script

    start_parameters = config_frame.config_elements
    command = ["python", 'background_bot.py', start_parameters['profile_token'].get(), start_parameters['channel_name'].get(), start_parameters['ip_address'].get(), start_parameters['port'].get()]
    bot_script = subprocess.Popen(command, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, shell=False, creationflags = subprocess.CREATE_NO_WINDOW)
    print(f"Starting twitch bot...")


def server_function():
    global server_script
    
    start_parameters = config_frame.config_elements
    command = ["python", 'server.py', start_parameters['ip_address'].get(), start_parameters['port'].get()]
    server_script = subprocess.Popen(command, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=False, creationflags = subprocess.CREATE_NO_WINDOW)
    print(f"Starting server on {start_parameters['ip_address'].get()}:{start_parameters['port'].get()}...")


def run_server():
    global server_thread

    print('')
    if config_frame.config_elements['ip_address'].get() != '' and config_frame.config_elements['port'].get() != '':
        run_button.configure(text = 'Stop server')
        run_button.configure(command = stop_server)

        server_thread = threading.Thread(target=server_function)
        server_thread.daemon = True
        server_thread.start()

    else:
        logs_textbox.configure(state="normal")
        if config_frame.config_elements['ip_address'].get() == '':
            logs_textbox.insert('end', "Server can not be started, missing 'ip_address'... \n")

        if config_frame.config_elements['port'].get() == '':
            logs_textbox.insert('end', "Server can not be started, missing 'port'... \n")

        logs_textbox.configure(state="disabled")


def run_bot():
    global bot_thread
    
    print('')
    if config_frame.config_elements['channel_name'].get() != '' and config_frame.config_elements['profile_token'].get() != '':
        bot_button.configure(text = 'Stop bot')
        bot_button.configure(command = stop_bot)

        bot_thread = threading.Thread(target=bot_function)
        bot_thread.daemon = True
        bot_thread.start()

        if server_script == '':
            logs_textbox.configure(state="normal")
            logs_textbox.insert('end', 'Server not running, waiting for it... \n')
            logs_textbox.configure(state="disabled")

    else:
        logs_textbox.configure(state="normal")
        if config_frame.config_elements['profile_token'].get() == '':
            logs_textbox.insert('end', "Bot can not be started, missing 'profile_token'... \n")

        if config_frame.config_elements['channel_name'].get() == '':
            logs_textbox.insert('end', "Bot can not be started, missing 'channel_name'... \n")

        logs_textbox.configure(state="disabled")


def stop_bot():
    bot_button.configure(text = 'Run bot')
    bot_button.configure(command = run_bot)

    bot_script.terminate()

    logs_textbox.configure(state="normal")
    logs_textbox.insert('end', 'Bot stopped... \n')
    logs_textbox.configure(state="disabled")


def stop_server():
    run_button.configure(text = 'Run server')
    run_button.configure(command = run_server)

    server_script.terminate()

    logs_textbox.configure(state="normal")
    logs_textbox.insert('end', 'Server stopped... \n')
    logs_textbox.configure(state="disabled")


def download_widget(value):
    if 'default' in value:
        url = 'https://raw.githubusercontent.com/tizhproger/now_playing/main/Widget%20page/NowPlaying.html'
    else:
        url = 'https://raw.githubusercontent.com/tizhproger/now_playing/main/Widget%20page/NowPlaying_hiding.html'

    filename = url.split('/')[-1]
    response = requests.get(url)
    if response.status_code == 200:
        file_path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML Files")], initialfile=filename)
        if file_path:
            with open(file_path, "wb") as file:
                file.write(response.content)
        
            logs_textbox.configure(state="normal")
            logs_textbox.insert('end', f"Widget {filename} downloaded \n")
            logs_textbox.insert('end', f"Path {file_path} \n")
            logs_textbox.configure(state="disabled")

    else:
        print("Failed to download file")
    
    widgets_button.set('')

#Logs section
logs_textbox = customtkinter.CTkTextbox(app, width=400, height=300)
logs_textbox.configure(state="disabled")
logs_textbox.grid(row=0, column=1, padx=20, pady=20)

#Config section
check_config()
config_frame = ConfigFrame(app, 'Server config')

widgets_button = customtkinter.CTkSegmentedButton(app, values=["Widget default", "Widget hiding"], command=download_widget)
widgets_button.grid(row=1, column=0, padx=20, pady=5, sticky='w')

save_button = customtkinter.CTkButton(app, text='Save', width=80, command=save_config)
save_button.grid(row=1, column=0, padx=64, pady=5, sticky='e')

reload_button = customtkinter.CTkButton(app, text='⟳', width=30, command=config_frame.update)
reload_button.grid(row=1, column=0, padx=25, pady=5, sticky='e')

#Starting buttons
if config_frame.config_elements['server_autorun'].get() == 'Yes':
    run_button = customtkinter.CTkButton(app, text='Stop server', command=stop_server)
    run_server()

else:
    run_button = customtkinter.CTkButton(app, text='Run server', command=run_server)
run_button.grid(row=1, column=1, pady=5, padx=(0, 45), sticky='e')


if config_frame.config_elements['twitch_bot_autorun'].get() == 'Yes':
    bot_button = customtkinter.CTkButton(app, text='Stop bot', command=stop_bot)
    run_bot()

else:
    bot_button = customtkinter.CTkButton(app, text='Run bot', command=run_bot)
bot_button.grid(row=1, column=1, pady=5, padx=(45, 0), sticky='w')

def on_closing():
    websocket_client.close()
    sys.stdout = old_stdout

    if server_script != '':
        server_script.terminate()
    
    if bot_script != '':
        bot_script.terminate()

    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)

websocket_client = WebSocketClient(f"ws://{config_frame.config_elements['ip_address'].get()}:{config_frame.config_elements['port'].get()}", logs_textbox)
websocket_client.start()

old_stdout = sys.stdout
sys.stdout = RedirectOutput(logs_textbox)
app.mainloop()

