from fasthtml.common import *
from PIL import Image, ImageDraw, ImageFont
import requests
import json
import os
import socket
import re

# Define the bootstrap version, style, and icon packs
cdn = 'https://cdn.jsdelivr.net/npm/bootstrap'
bootstrap_links = [
    Link(href=cdn+"@5.3.3/dist/css/bootstrap.min.css", rel="stylesheet"),
    Script(src=cdn+"@5.3.3/dist/js/bootstrap.bundle.min.js"),
    Link(href=cdn+"-icons@1.11.3/font/bootstrap-icons.min.css", rel="stylesheet"),
    Link(href=cdn+"about:blank", rel="shortcut icon") # Suppress favicon warning
]

# Attempt to avoid needing to use a .css file. Insert overrides here if needed
# Placeholders for menu elements
css = Style()

# Define classes
class Game:
    game_id:int; game_name:str; game_added:bool
    def __ft__(self):
        return Li(
            Div(
                Strong(self.game_name, cls='col-auto'),
                Div(
                    Button(
                        'Add To Sunshine', hx_get=f'/add/{self.game_id}', target_id=f'appid-{self.game_id}',
                        cls='btn btn-primary me-2'
                    ),
                    Button(
                        'Remove', hx_get=f'/remove/{self.game_id}', target_id=f'appid-{self.game_id}',
                        cls='btn btn-danger me-2'
                    ),
                    Strong(
                        I(cls='bi bi-toggle-on') if self.game_added else I(cls='bi bi-toggle-off'),
                        id=f'appid-{self.game_id}'
                    ), cls='col d-flex justify-content-end'
                ), cls='row'
            ), cls='list-group-item'
        )
class Setting:
    key:str; value:str
    def __ft__(self):
        return Li(
            Strong(self.key, cls='col-auto'),
            Input(placeholder=f"{self.value}", id=f'setVal-{self.key}', cls='col-8'),
            Button('Save', hx_post=f'/save/{self.key}', cls='btn btn-danger col-1'),
            cls='list-group-item grid'
        )
class Logfile:
    def __init__(self, filename: str, content: str):
        self.filename = filename
        self.content = content
    def __ft__(self):
        return Details(Summary(self.filename), Pre(P(self.content)), cls='card mb-2')

# Define the database and create tables (if necessary)
try:
    db_exists = os.path.isfile('/home/default/.cache/shui.db')
    if not db_exists:
        db = database('/home/default/.cache/shui.db')
        gamedb = db.create(Game, pk='game_id')
        settingdb = db.create(Setting, pk='key')
        settingdb.insert(
            Setting(key='Steam Directory',
                value='/mnt/games/SteamLibrary/steamapps'
            )
        )
        settingdb.insert(
            Setting(key='Sunshine Json Location',
                value='/home/default/.config/sunshine/apps.json'
            )
        )
        settingdb.insert(
            Setting(key='Poster Directory',
                value='/home/default/.local/share/posters'
            )
        )
    else:
        db = database('/home/default/.cache/shui.db')
        gamedb = db.table(Game)
        settingdb = db.table(Setting)
except Exception as e:
    print(f"An error occurred: {e}")

# Get the Server IP Address
def get_local_ip():
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Connect to an external server (doesn't actually send any data)
        s.connect(("8.8.8.8", 80))
        
        # Get the local IP address
        local_ip = s.getsockname()[0]
        
        # Close the socket
        s.close()
        
        return local_ip
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Use the function to get the server IP
server_ip = get_local_ip()

# Grab Any ENV variables for later use
port_novnc_web = os.getenv('PORT_NOVNC_WEB')

# Invokation of the fast_app function
# Define the main fastHTML app
app,rt = fast_app(
    pico=False, # Avoid conflicts between bootstrap styling and the built in picolink
    hdrs=(
        bootstrap_links, 
        css)
)

# Define the sidebar items
def SidebarItem(text, hx_get, hx_target, **kwargs):
    return Div(
        I(cls=f'bi bi-{text}'),
        Span(text),
        hx_get=hx_get, hx_target=hx_target,
        data_bs_toggle='modal', data_bs_target="#centeredScrollableModal",
        data_bs_parent='#sidebar', data_bs_dismiss='offcanvas', role='button',
        cls='list-group-item border-end-0 d-inline-block text-truncate',
        **kwargs)

# Define the sidebar
def Sidebar(sidebar_items, hx_get, hx_target):
    return Div(
        Div(*(SidebarItem(o, f"{hx_get}?menu={o}", hx_target) for o in sidebar_items),
            id='sidebar-nav',
            cls='list-group border-0 rounded-0 text-sm-start'
        ),
        id='sidebar',
        cls='offcanvas offcanvas-start w-25')

# Add remove buttons to the sidebar
sidebar_items = ('Logs', 'FAQ')

# The Log Page content is defined here
def logs_content():
    logs_dir = "/home/default/.cache/log"
    if os.path.isdir(logs_dir):
        # List all log files in the logs directory
        log_files = [f for f in os.listdir(logs_dir) if os.path.isfile(os.path.join(logs_dir, f)) and f.endswith('.log')]
        sorted_log_files = sorted(log_files)
        # Read the last 50 lines of each log file
        logfiles = []
        for log_file in sorted_log_files:
            file_path = os.path.join(logs_dir, log_file)
            with open(file_path, 'r') as file:
                lines = file.readlines()[-50:]
                content = "".join(lines)
                logfiles.append(Logfile(log_file, content))
        # Return a container with all the logs using bootstrap classes
        return Div(*logfiles, cls='container py-5') if logfiles else Div("No log files found.")
    else:
        return Div("No log Directory Created.")

# The Faq Page content is defined here
# TODO add a proper FAQ page with markdown, styling, and links to the documentation
def faq_content():
    url = "https://raw.githubusercontent.com/Steam-Headless/docker-steam-headless/refs/heads/master/docs/troubleshooting.md"
    response = requests.get(url)
    if response.status_code == 200:
        _content = response.text
    else:
        _content = "Failed to load content."

    return Div(
        H1("FAQ", cls="py-5"),
        Pre(_content),
        cls="container"
    )

@rt('/')
def get():
    return Main(
        Sidebar(
            sidebar_items, hx_get='menucontent', hx_target='#current-menu-content'
        ),
        A(
            I(cls='bi bi-controller bi-lg py-2 p-1'),
            href='#', data_bs_target='#sidebar', data_bs_toggle='offcanvas', aria_expanded='false', aria_controls='sidebar',
            cls='border rounded-3 p-1 text-decoration-none bg-dark text-white bg-opacity-25 position-fixed my-2 mx-2'
        ),
        Iframe(
            id='landing', src=f'http://{server_ip}:{port_novnc_web}/web/index.html?autoconnect=true',
            style='width: 100%; height: 100vh; border:none; overflow-y:hidden;'
        ),
        Div(
            Div(
                Div(
                    Div(id='current-menu-content', cls='modal-body'),
                    cls='modal-content'
                ),
                cls='modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable'
            ),
            id="centeredScrollableModal", cls='modal', tabindex='-1', aria_labelledby='modalLabel', aria_hidden='true'
        )
    )

# The route for the menu content, which is dynamically loaded via htmx into #current-menu-content
@rt('/menucontent')
def menucontent(menu: str):

    switch_cases = {
        'Logs': logs_content(),
        'FAQ': faq_content()
    }

    return switch_cases.get(menu, Div("No content available", cls='py-5'))

# Run the app
# Serve the application at port 8082
serve(port=8082, reload=False)