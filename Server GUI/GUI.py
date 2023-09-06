from configparser import ConfigParser
from tkinter import messagebox
from tkinter import filedialog
import customtkinter
import os
import sys
import threading
import requests
import server as wss
import background_bot as tbb

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
        self.widget.see("end")  # autoscroll
    
    def flush(self):
        pass


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
    
    print(' ')
    print('Config file now_playing_conf.ini created')


def check_config():
    if os.path.exists(config_filename):
        print(' ')
        print(f"Config file '{config_filename}' already exists")
        print('Loading data...')

    else:
        print(' ')
        print(f"Config file '{config_filename}' does not exist")
        print('It will be created automatically with default values...')
        print('You can fill it manually, just edit config on the left panel...')

        create_ini_file(config_filename)


def save_config():
    config_object.read(config_filename)
    updated_config = config_frame.frame_config()
    if updated_config['twitch_bot_autorun'] not in ['Yes', 'No']:
        messagebox.showinfo("Input error", "Twitch_bot_autorun can have only 'Yes' or 'No' value!")
        print(' ')
        print(f"Change twitch_bot_autorun to Yes or No...")
        return

    elif updated_config['server_autorun'] not in ['Yes', 'No']:
        messagebox.showinfo("Input error", "Server_autorun can have only 'Yes' or 'No' value!")
        print(' ')
        print(f"Change server_autorun to Yes or No...")
        return
    
    for section in config_object.sections():
        for key in config_object[section].keys():
            config_object.set(section, key, updated_config[key])
    
    with open(config_filename, 'w') as configfile:
        config_object.write(configfile)
    
    print(' ')
    print(f"Config file '{config_filename}' updated...")


def run_server():
    if config_frame.config_elements['ip_address'].get() != '' and config_frame.config_elements['port'].get() != '':
        run_button.configure(text = 'Stop server')
        run_button.configure(command = stop_server)

        start_parameters = config_frame.config_elements
        print(' ')
        print(f"Starting server on {start_parameters['ip_address'].get()}:{start_parameters['port'].get()}...")
        thread = threading.Thread(target=wss.run_webserver, args=(start_parameters['ip_address'].get(), start_parameters['port'].get()))
        thread.daemon = True
        thread.start()

    else:
        if config_frame.config_elements['ip_address'].get() == '':
            print(' ')
            print("Server can not be started, missing 'ip_address'...")

        if config_frame.config_elements['port'].get() == '':
            print(' ')
            print("Server can not be started, missing 'port'...")


def run_bot():
    if config_frame.config_elements['channel_name'].get() != '' and config_frame.config_elements['profile_token'].get() != '':
        bot_button.configure(text = 'Stop bot')
        bot_button.configure(command = stop_bot)

        print(' ')
        print(f"Starting twitch bot...")
        start_parameters = config_frame.config_elements
        thread = threading.Thread(target=tbb.run_bot, args=(start_parameters['profile_token'].get(), start_parameters['channel_name'].get(), start_parameters['ip_address'].get(), start_parameters['port'].get()))
        thread.daemon = True
        thread.start()

    else:
        if config_frame.config_elements['profile_token'].get() == '':
            print(' ')
            print("Bot can not be started, missing 'profile_token'...")

        if config_frame.config_elements['channel_name'].get() == '':
            print(' ')
            print("Bot can not be started, missing 'channel_name'...")


def stop_bot():
    bot_button.configure(text = 'Run bot')
    bot_button.configure(command = run_bot)

    tbb.close_bot()

    print(' ')
    print('Bot stopped...')


def stop_server():
    run_button.configure(text = 'Run server')
    run_button.configure(command = run_server)

    wss.close_webserver()

    print(' ')
    print('Stopping server...')


def download_widget(value):
    if 'default' in value:
        url = 'https://drive.google.com/uc?id=1f1JJjZKcnO96KP53KpuZdBTcMu-qIcf_&export=download'
        filename = 'NowPlaying'
    else:
        url = 'https://drive.google.com/uc?id=1YykGLquiBrVPnNjphaa8Rd-VwAimjL5U&export=download'
        filename = 'NowPlaying_hiding'

    response = requests.get(url)
    if response.status_code == 200:
        file_path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML Files")], initialfile=filename)
        if file_path:
            with open(file_path, "wb") as file:
                file.write(response.content)
            print(' ')
            print(f"Widget {filename} downloaded")
            print(f"Path {file_path}")

    else:
        print(' ')
        print("Failed to download file")
    
    widgets_button.set('')

#Logs section
logs_textbox = customtkinter.CTkTextbox(app, width=400, height=300)
logs_textbox.configure(state="disabled")
logs_textbox.grid(row=0, column=1, padx=20, pady=20)

old_stdout = sys.stdout
sys.stdout = RedirectOutput(logs_textbox)

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
    run_button.grid(row=1, column=1, pady=5, padx=(0, 45), sticky='e')
    run_server()

else:
    run_button = customtkinter.CTkButton(app, text='Run server', command=run_server)
    run_button.grid(row=1, column=1, pady=5, padx=(0, 45), sticky='e')

if config_frame.config_elements['twitch_bot_autorun'].get() == 'Yes':
    bot_button = customtkinter.CTkButton(app, text='Stop bot', command=stop_bot)
    bot_button.grid(row=1, column=1, pady=5, padx=(45, 0), sticky='w')
    run_bot()

else:
    bot_button = customtkinter.CTkButton(app, text='Run bot', command=run_bot)
    bot_button.grid(row=1, column=1, pady=5, padx=(45, 0), sticky='w')

app.mainloop()
sys.stdout = old_stdout
