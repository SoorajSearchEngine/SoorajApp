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
import threading
from collections import defaultdict
from functools import wraps
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import shutil
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='sooraj.log'
)

# Memoize decorator
def memoize(func):
    cache = {}
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(kwargs.items()))
        if key not in cache: cache[key] = func(*args, **kwargs)
        return cache[key]
    return wrapper

# Search Index Class
class SearchIndex:
    @memoize
    def __init__(self):
        self.index = defaultdict(list)
        self.file_contents = {}
        self.lock = threading.Lock()

    @memoize
    def add_file(self, file_path):
        try:
            print(f"Adding file to index: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Read content length: {len(content)}")
                print(f"Content preview: {content[:100]}")
                words = self._process_text(content)
                with self.lock:
                    for word in words:
                        self.index[word].append(file_path)
                    self.file_contents[file_path] = content
                    print(f"Added file to index: {file_path}")
        except Exception as e:
            print(f"Error indexing {file_path}: {str(e)}")
            logging.error(f"Error indexing {file_path}: {e}")

    @memoize
    def _process_text(self, text):
        text = text.lower()
        words = word_tokenize(text)
        stop_words = set(stopwords.words('english'))
        return [word for word in words if word not in stop_words]

    @memoize
    def search(self, query):
        query_words = self._process_text(query)
        results = defaultdict(int)
        
        print(f"Searching for words: {query_words}")
        for word in query_words:
            matching_files = self.index.get(word, [])
            print(f"Found {len(matching_files)} files for word: {word}")
            for file_path in matching_files:
                results[file_path] += 1
        
        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
        print(f"Search results: {sorted_results}")
        return sorted_results

# Search Algorithm Class
class Search:
    @memoize    
    def __init__(self, search_index):
        self.search_index = search_index

    @memoize
    def search_algorithm(self, query):
        results = self.search_index.search(query)
        ranked_results = []
        
        for file_path, _ in results:
            content = self.search_index.file_contents[file_path]
            rank = self.rank(query, content)
            ranked_results.append((file_path, content, rank))
        
        # Sort results by rank in descending order
        ranked_results.sort(key=lambda x: x[2], reverse=True)
        
        # Return only file_path and content, removing the rank
        return [(file_path, content) for file_path, content, _ in ranked_results]

    @memoize
    def rank(self, query, content):
        rank = 0
        for word in content.lower():
            if word in query.lower():
                rank += 1
        return rank

# SERP Class
class SERP:
    def __init__(self):
        self.master = None
        self.search_instance = None
        self.page = None
        self.current_content = None

    def set_master(self, master):
        if not isinstance(master, Container):
            master = Container(
                content=Column(controls=[]),
                width=900,
                height=900,
                bgcolor="#f5f6f7",
                padding=10,
                border_radius=10,
                alignment=alignment.center
            )
        self.master = master

    def set_page(self, page):
        self.page = page

    def set_search(self, search_instance):
        self.search_instance = search_instance

    def clear_content(self):
        if self.master and hasattr(self.master, 'content') and isinstance(self.master.content, Column):
            self.master.content.controls.clear()
            if self.page:
                self.page.update()

    def open_file(self, content):
        try:
            if not self.master or not self.page:
                logging.error("Master container or page not set")
                return

            print(f"Opening file with content length: {len(content) if content else 0}")
            print(f"Content preview: {content[:100] if content else 'None'}")
            
            self.clear_content()
            
            if not content:
                print("No content to display")
                if self.page:
                    self.page.show_snack_bar(
                        SnackBar(
                            content=Text("No content to display"),
                            bgcolor="red"
                        )
                    )
                return
            
            # Create a container for the content
            content_container = Container(
                content=Column(
                    controls=[
                        Markdown(
                            value=content,
                            selectable=True,
                            extension_set="gitHubWeb"
                        ),
                        Divider(height=1, color="#1a0ea4")
                    ],
                    spacing=10,
                    scroll=ScrollMode.AUTO
                ),
                padding=20,
                bgcolor="#ffffff",
                border_radius=10,
                border=border.all(1, "#1a0ea4"),
                width=800,
                height=500
            )
            
            if hasattr(self.master, 'content') and isinstance(self.master.content, Column):
                self.master.content.controls.append(content_container)
                print("Content container added to master")
            else:
                print("Failed to add content container - master content not found or not Column")
            
            self.current_content = content
            self.page.update()
            print("Page updated")
        except Exception as e:
            print(f"Error in open_file: {str(e)}")
            logging.error(f"Error opening file: {e}")
            if self.page:
                self.page.show_snack_bar(
                    SnackBar(
                        content=Text(f"Error displaying content: {str(e)}"),
                        bgcolor="red"
                    )
                )

    def search(self, query, folder_path):
        try:
            print(f"SERP search called with query: {query}")
            
            if not query or not self.master or not self.page:
                print("Missing required parameters")
                return

            self.clear_content()
            
            if not self.search_instance:
                print("Search instance not set")
                logging.error("Search instance not set")
                return

            print("Calling search_algorithm...")
            results = self.search_instance.search_algorithm(query)
            print(f"Search results count: {len(results) if results else 0}")
            
            if not results:
                print("No results found")
                if hasattr(self.master, 'content') and isinstance(self.master.content, Column):
                    self.master.content.controls.append(
                        Text("No results found", size=16, color="#666666")
                    )
                self.page.update()
                return

            seen_files = set()
            
            for file_path, content in results:
                try:
                    if file_path in seen_files:
                        continue
                    
                    seen_files.add(file_path)
                    print(f"Processing file: {file_path}")
                    print(f"Content length: {len(content) if content else 0}")
                    
                    # Create a container for each result
                    result_container = Container(
                        content=TextButton(
                            text=Path(file_path).name,
                            on_click=lambda e, c=content: self.open_file(c),
                            style=ButtonStyle(
                                color="#1a0ea4",
                                overlay_color="#f5f6f7"
                            ),
                            width=800,
                            height=40
                        ),
                        padding=padding.symmetric(vertical=5),
                        alignment=alignment.center
                    )
                    
                    # Add the container to the master container's content
                    if hasattr(self.master, 'content') and isinstance(self.master.content, Column):
                        self.master.content.controls.append(result_container)
                        print(f"Added result for: {file_path}")
                    else:
                        print("Failed to add result container - master content not found or not Column")
                    
                except Exception as e:
                    print(f"Error processing result {file_path}: {e}")
                    logging.error(f"Error processing result {file_path}: {e}")
            
            if hasattr(self.master, 'content') and isinstance(self.master.content, Column) and not self.master.content.controls:
                print("No controls added")
                self.master.content.controls.append(
                    Text("No results found", size=16, color="#666666")
                )
            
            print("Updating page...")
            self.page.update()
        except Exception as e:
            print(f"Search error: {e}")
            logging.error(f"Search error: {e}")
            if self.page:
                self.page.show_snack_bar(
                    SnackBar(
                        content=Text(f"Search error: {str(e)}"),
                        bgcolor="red"
                    )
                )

# Developer Class
class Developer:
    def __init__(self):
        self.dev_console = None
        self.page = None
        self.folder_path = None
        self.file_picker = None

    def set_page(self, page):
        self.page = page
        if page and not self.file_picker:
            self.file_picker = FilePicker()
            page.overlay.append(self.file_picker)

    def set_folder_path(self, folder_path):
        self.folder_path = folder_path

    async def add_website(self, e: FilePickerResultEvent):
        try:
            if not e.files:
                return

            if not self.folder_path:
                self.show_message("Error", "Folder path not set")
                return

            file_path = e.files[0].path
            if not file_path:
                self.show_message("Error", "No file selected")
                return

            # Ensure the file is a text file
            if not file_path.lower().endswith('.txt'):
                self.show_message("Error", "Only .txt files are supported")
                return

            # Copy file to destination
            dest_path = Path(self.folder_path) / Path(file_path).name
            shutil.copy(file_path, dest_path)
            
            logging.info(f"File copied to {dest_path}")
            self.show_message("Success", "File added successfully!")
        except Exception as e:
            logging.error(f"Error copying file: {e}")
            self.show_message("Error", f"Failed to add file: {str(e)}")

    def show_message(self, title, message):
        try:
            if not self.page:
                logging.error("Page not set")
                return

            self.page.show_snack_bar(
                SnackBar(
                    content=Text(message),
                    action="OK",
                    bgcolor="#1a0ea4",
                    action_color="#ffffff"
                )
            )
        except Exception as e:
            logging.error(f"Error showing message: {e}")

    def show_developer_console(self):
        try:
            if not self.page:
                logging.error("Page not set")
                return

            if not self.dev_console:
                self.dev_console = Container(
                    content=Column(
                        controls=[
                            Text("Developer Console", size=20, weight="bold", color="#1a0ea4"),
                            ElevatedButton(
                                "Add Website",
                                icon="add",
                                on_click=lambda _: self.file_picker.pick_files(
                                    allowed_extensions=["txt"],
                                    on_result=self.add_website
                                ),
                                style=ButtonStyle(
                                    color="#ffffff",
                                    bgcolor="#1a0ea4",
                                    overlay_color="#1a0ea4"
                                )
                            ),
                            Divider(),
                            Text("Logs:", size=16, weight="bold"),
                            Text(logging.getLogger().handlers[0].baseFilename if logging.getLogger().handlers else "No log file configured")
                        ],
                        spacing=20
                    ),
                    padding=20,
                    bgcolor="#f5f6f7",
                    border_radius=10,
                    border=border.all(1, "#1a0ea4")
                )
                
                self.page.add(self.dev_console)
            else:
                self.dev_console.visible = not self.dev_console.visible
            
            self.page.update()
        except Exception as e:
            logging.error(f"Error showing developer console: {e}")
            if self.page:
                self.show_message("Error", f"Failed to show developer console: {str(e)}")

# Main function
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
        for file_path in glob.glob(f"{str(folder_path)}/*.*"):
            try:
                if file_path.lower().endswith(('.txt', '.md')):
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

        # Create search interface
        searchbox = TextField(
            width=700,
            height=50,
            label="Search",
            border_radius=50,
            border_color="#1a0ea4",
            focused_border_color="#1a0ea4",
            text_size=16,
            content_padding=padding.only(left=20, right=20),
            color="#0a0a0a"
        )

        def on_search(e):
            query = searchbox.value.strip()
            if query:
                print(f"Searching for: {query}")  # Debug print
                gui.search(query, folder_path)
                page.update()

        searchbox.on_submit = on_search

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


