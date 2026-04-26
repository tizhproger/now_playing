from configparser import ConfigParser
from tkinter import messagebox
from tkinter import filedialog
import customtkinter as ctk
import logging
import webbrowser
import customtkinter
import os
import re
import sys
import threading
import requests
import server as wss
import background_bot as tbb
import widgets_server as ows

app = customtkinter.CTk()
config_object = ConfigParser(interpolation=None)

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


class ToolTip:
    def __init__(self, widget, text: str, delay_ms: int = 350):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id = None
        self._tip = None

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _):
        self._after_id = self.widget.after(self.delay_ms, self.show)

    def _on_leave(self, _):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self.hide()

    def show(self):
        if self._tip or not self.widget.winfo_exists():
            return

        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6

        self._tip = ctk.CTkToplevel(self.widget)
        self._tip.overrideredirect(True)
        self._tip.attributes("-topmost", True)
        self._tip.geometry(f"+{x}+{y}")

        frame = ctk.CTkFrame(self._tip, corner_radius=8)
        frame.pack(padx=0, pady=0)

        label = ctk.CTkLabel(
            frame,
            text=self.text,
            justify="left",
            padx=10,
            pady=6,
            wraplength=360
        )
        label.pack()

    def hide(self):
        if self._tip:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None

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
        super().__init__(master, label_text=title, width=350, height=480)
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
        tips = {
            "twitch_song_commands": "Commands separated by commas or spaces, without '!'\nExample: song, track\n[Bot reboot required]",
            "twitch_reply_playing": "Response when status = playing.\nVariables: {user} {artists} {title} {link}\n[Bot reboot required]",
            "twitch_reply_other": "Response when the track is not playing (paused/unknown).\nVariables: {user} {artists} {title} {link}\n[Bot reboot required]",
            "twitch_reply_empty": "Response when the bot hasn't yet received track data.\nLeave blank or 'off' to not respond.\n[Bot reboot required]",
            "twitch_reply_error": "Reply if corrupted data was received.\nLeave blank or 'off' to not reply.\n[Bot reboot required]",
            "port": "Port for OBS-sources connections.\n[Server reboot required]",
            "widgets_port": "Port for widgets-pages hosting.\n[Application reboot required]",
            "ip_address": "IP for OBS-sources connections.\n[Server reboot required]",
            "profile_token": "Twitch profile token (OAuth Token API v2).\nUses V2 of API, in V3 other creds. needed\n[Bot reboot required]",
            "channel_name": "Twitch channel name.\n[Bot reboot required]"
        }
        
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
                
                if key in tips:
                    ToolTip(entry, tips[key])

            else:
                label = customtkinter.CTkLabel(self, text=key, fg_color="transparent")
                combobox = customtkinter.CTkComboBox(self, values=["Yes", "No"])
                combobox.set(k_value)

                label.grid(row=count, column=0, padx=15, pady=5, sticky="w")
                combobox.grid(row=count, column=1, padx=10, pady=5, sticky="w")

                self.config_elements[key] = combobox

            count += 1


app.title("Now Playing - OBS (Server)")

window_height = 650
window_width = 850

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
    config_object['WIDGETS'] = {'widgets_port': 9000}
    config_object['TWITCH_BOT'] = {
        'twitch_song_commands': "song, track",
        'twitch_reply_playing': "@{user} Now playing: {artists} - {title} {link}",
        'twitch_reply_other':   "@{user} Track: {artists} - {title} {link}",
        'twitch_reply_empty':   "@{user} Don't know yet. Wait a few seconds.",
        'twitch_reply_error':   "@{user} 404 Song Not Found :("
    }
    
    with open(config_filename, 'w') as configfile:
        config_object.write(configfile)
    
    print(' ')
    print('Config file now_playing_conf.ini created')


def check_config():
    if os.path.exists(config_filename):
        print(' ')
        print(f"Config file '{config_filename}' already exists")
        print('Loading data...')
        
        twitch_defaults = {
            'twitch_song_commands': "song, track, трек, песня",
            'twitch_reply_playing': "@{user} Now playing: {artists} - {title} {link}",
            'twitch_reply_other':   "@{user} Track: {artists} - {title} {link}",
            'twitch_reply_empty':   "@{user} Don't know track yet. Wait a few seconds.",
            'twitch_reply_error':   "@{user} 404 Song Not Found :("
        }
        
        widgets_defaults = {
            'widgets_port': '9000',
        }
        
        config_object.read(config_filename)
        if 'WIDGETS' not in config_object:
            config_object['WIDGETS'] = widgets_defaults
            with open(config_filename, 'w') as configfile:
                config_object.write(configfile)
                
        elif 'widgets_port' not in config_object['WIDGETS']:
            config_object['WIDGETS']['widgets_port'] = '9000'
            with open(config_filename, 'w') as configfile:
                config_object.write(configfile)
            print(' ')
            print('Config updated: WIDGETS fields added.')


        changed = False
        if 'TWITCH_BOT' not in config_object:
            config_object['TWITCH_BOT'] = twitch_defaults
            changed = True
        else:
            sec = config_object['TWITCH_BOT']
            for k, v in twitch_defaults.items():
                if k not in sec:
                    sec[k] = v
                    changed = True

        if changed:
            with open(config_filename, 'w') as configfile:
                config_object.write(configfile)
            print(' ')
            print('Config updated: TWITCH_BOT fields added.')

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
        
        cmds  = config_frame.config_elements.get('twitch_song_commands').get()
        rp    = config_frame.config_elements.get('twitch_reply_playing').get()
        ro    = config_frame.config_elements.get('twitch_reply_other').get()
        re    = config_frame.config_elements.get('twitch_reply_empty').get()
        rerr  = config_frame.config_elements.get('twitch_reply_error').get()
        token = config_frame.config_elements.get('profile_token').get()
        channel = config_frame.config_elements.get('channel_name').get()
        ip = config_frame.config_elements.get('ip_address').get()
        port = config_frame.config_elements.get('port').get()

        print(' ')
        print(f"Starting twitch bot...")
        start_parameters = config_frame.config_elements
        thread = threading.Thread(target=tbb.run_bot, args=(token, channel, ip, port, cmds, rp, ro, re, rerr))
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


#Logs section
logs_textbox = customtkinter.CTkTextbox(app, width=350, height=535)
logs_textbox.configure(state="disabled")
logs_textbox.grid(row=0, column=1, padx=40, pady=20)

old_stdout = sys.stdout
old_stderr = sys.stderr
sys.stdout = RedirectOutput(logs_textbox)
sys.stderr = RedirectOutput(logs_textbox)

logging.basicConfig(level=logging.INFO, stream=sys.stdout, force=True)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("twitchio").setLevel(logging.WARNING)

#Config section
check_config()
config_frame = ConfigFrame(app, 'Server config')

save_button = customtkinter.CTkButton(app, text='Save', width=60, command=save_config)
save_button.grid(row=1, column=0, padx=120, pady=5, sticky='e')

reload_button = customtkinter.CTkButton(app, text='⟳', width=60, command=config_frame.update)
reload_button.grid(row=1, column=0, padx=40, pady=5, sticky='e')



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


widgets_port = 9000
try:
    widgets_port = int(config_frame.config_elements.get('widgets_port').get() or 9000)
except Exception:
    widgets_port = 9000

widgets = threading.Thread(target=ows.run_widgets, args=(widgets_port,))
widgets.daemon = True
widgets.start()


class StdoutHandler(logging.Handler):
    """Выводит только полезные строки логов."""
    def emit(self, record):
        try:
            msg = record.getMessage()

            if re.search(r"Connected:\s*\('127\.0\.0\.1',\s*\d+\)", msg):
                return

            if any(x in msg for x in (
                "Server started",        # запуск сервера
                "youtube.com connected", # youtube
                "OBS source",            # OBS
                "Twitch",                # Twitch если появится
                )):
                print(msg)
        except Exception:
            pass

def hook_nowplaying_logger():
    logger = logging.getLogger("NowPlayingWS")
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = StdoutHandler()
    logger.addHandler(handler)

hook_nowplaying_logger()


def open_constructor():
    # Открыть конструктор в системном браузере
    host = config_frame.config_elements.get('ip_address').get() if config_frame and 'ip_address' in config_frame.config_elements else 'localhost'
    widgets_port = 9000
    try:
        widgets_port = int(config_frame.config_elements.get('widgets_port').get() or 9000)
    except Exception:
        widgets_port = 9000

    url = f"http://{host}:{widgets_port}/constructor.html"
    try:
        webbrowser.open(url, new=2)  # new=2 — в новой вкладке
        print(' ')
        print(f"Opening constructor: {url}")
    except Exception as e:
        print(' ')
        print(f"Failed to open constructor: {e}")
        messagebox.showinfo("Open Constructor", f"Open this URL manually:\n{url}")

# Widgets constructor button
widgets_button = customtkinter.CTkButton(app, text='Widget Constructor', width=60, command=open_constructor)
widgets_button.grid(row=1, column=0, pady=5, padx=40, sticky='w')


def on_closing():
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    ows.close_widgets()
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()
