import glob
import nltk
from flet import *
from pathlib import Path
import platform
from PIL import Image as PILImage
import logging
from datetime import date
import os
import sys
from Optimizer import *
from Search_Index import *
from SERP import *
from Developer import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='sooraj.log'
)

def initialize():
    try:
        # Download required NLTK data
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)

        # Set up data folder
        folder_path = Path(f"{Path.home()}/data")
        if platform.system() == "Windows":
            folder_path = Path(f"{Path.home()}\\data")
        elif platform.system() == "Darwin": 
            folder_path = Path(f"{Path.home()}/data")

        if not folder_path.exists():
            folder_path.mkdir(parents=True)
        
        # Initialize components
        search_index = SearchIndex()
        search_instance = Search(search_index)
        gui = SERP()
        dev = Developer()
        
        # Initialize index with existing files
        for file_path in glob.glob(f"{str(folder_path)}/*.txt"):
            try:
                search_index.add_file(file_path)
            except Exception as e:
                logging.error(f"Error adding file {file_path} to index: {e}")
        
        return folder_path, search_instance, gui, dev
    except Exception as e:
        logging.critical(f"Initialization error: {e}")
        raise

def resource_path(relative_path):
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
    except Exception as e:
        logging.critical(f"Error getting resource path: {e}")
        return ""

async def main(page: Page):
    try:
        # Initialize components
        folder_path, search, gui, dev = initialize()
        
        # Configure page
        page.window.maximized = True
        page.window.center()
        page.title = "Sooraj"
        page.bgcolor = "#f5f6f7"
        page.padding = 20
        page.vertical_alignment = MainAxisAlignment.CENTER
        page.horizontal_alignment = CrossAxisAlignment.CENTER
        
        # Load logo
        logo_path = resource_path("assets/logo.png")
        if not os.path.exists(logo_path):
            logging.error(f"Logo not found at {logo_path}")
            lbl = Text("Sooraj", size=32, weight="bold", color="#1a0ea4")
        else:
            lbl = Image(
                src=logo_path,
                width=200,
                height=50,
                fit=ImageFit.CONTAIN
            )

        # Create main container
        master = Container(
            content=Column(
                controls=[],
                scroll=ScrollMode.AUTO,
                spacing=10,
                expand=True
            ),
            width=900,
            height=600,
            bgcolor="#f5f6f7",
            padding=10,
            border_radius=10,
            alignment=alignment.center
        )

        # Create search interface
        searchbox = TextField(
            width=700,
            height=50,
            label="Search",
            border_radius=50,
            border_color="#1a0ea4",
            focused_border_color="#1a0ea4",
            text_size=16,
            content_padding=padding.only(left=20, right=20)
        )

        def on_search(e):
            query = searchbox.value.strip()
            if query:
                print(f"Searching for: {query}")  # Debug print
                gui.search(query, folder_path)
                page.update()

        searchbox.on_submit = on_search

        # Initialize GUI components
        gui.set_master(master)
        gui.set_search(search)
        gui.set_page(page)
        dev.set_page(page)
        dev.set_folder_path(folder_path)

        # Create main layout
        main_column = Column(
            controls=[
                lbl,
                searchbox,
                master
            ],
            spacing=20,
            alignment=MainAxisAlignment.CENTER,
            horizontal_alignment=CrossAxisAlignment.CENTER,
            expand=True
        )

        # Add components to page
        page.add(main_column)
        page.update()

    except Exception as e:
        logging.critical(f"Main function error: {e}")
        if page:
            page.add(Text(f"Error: {str(e)}", color="red", size=20))
            page.update()

if __name__ == "__main__":
    app(target=main)


