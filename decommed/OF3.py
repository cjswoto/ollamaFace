import os
import json
import threading
import time
import requests
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
import datetime
import re
from urllib.parse import quote_plus
import html

# Import BeautifulSoup for robust HTML parsing
from bs4 import BeautifulSoup

# Add these imports for enhanced web search
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False


class OllamaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OllamaChat - Local LLM Interface")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        # Set Windows-like style with dark theme
        self.style = tb.Style(theme="darkly")

        # Initialize variables
        self.ollama_url = "http://localhost:11434"
        self.current_model = tk.StringVar()
        self.message_history = []
        self.is_processing = False
        self.progress = None

        # Web search toggle and settings
        self.web_search_enabled = tk.BooleanVar(value=True)
        self.search_engine_url = "https://duckduckgo.com/html/?q="
        self.max_search_results = 3

        # Search debug info
        self.search_debug_info = ""

        # Session management
        self.sessions = {}
        self.current_session_id = None
        self.sessions_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../sessions")
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)

        # Setup main frame (creates sessions_listbox and other UI elements)
        self.setup_ui()

        # Create a mapping for Listbox indices to session IDs
        self.session_id_mapping = {}

        # Load existing sessions after the UI is setup
        self.load_sessions()

        # Get available models
        threading.Thread(target=self.refresh_models, daemon=True).start()

        # Create a new session at startup
        self.new_session()

        # Check for required packages
        self.check_required_packages()

    def check_required_packages(self):
        """Check if required packages are installed and notify user if not"""
        missing_packages = []
        if not DDGS_AVAILABLE:
            missing_packages.append("duckduckgo_search")
        if missing_packages:
            message = "For better search functionality, consider installing these packages:\n\n"
            message += "\n".join([f"pip install {pkg}" for pkg in missing_packages])
            self.root.after(1000, lambda: messagebox.showinfo("Package Recommendations", message))

    def setup_ui(self):
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left frame (chat interface)
        self.chat_frame = ttk.Frame(self.paned)
        self.paned.add(self.chat_frame, weight=3)

        # Right frame (model settings)
        self.settings_frame = ttk.Frame(self.paned)
        self.paned.add(self.settings_frame, weight=1)

        # Set up the chat interface
        self.setup_chat_interface()

        # Set up the settings panel
        self.setup_settings_panel()

    def setup_chat_interface(self):
        self.chat_label = ttk.Label(self.chat_frame, text="🗨️ Conversation", font=("Segoe UI", 12, "bold"))
        self.chat_label.pack(anchor=tk.W, pady=(0, 5))

        # Response display
        self.chat_display = scrolledtext.ScrolledText(
            self.chat_frame, wrap=tk.WORD, bg="#2b2b2b", fg="#ffffff", insertbackground="white",
            font=("Segoe UI", 10), height=20
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.chat_display.config(state=tk.DISABLED)

        # Progress bar container for loading indicator
        self.progress_frame = ttk.Frame(self.chat_frame)
        self.progress_frame.pack(fill=tk.X, pady=(0, 5))
        self.progress_label = ttk.Label(self.progress_frame, text="", font=("Segoe UI", 9))
        self.progress_label.pack(anchor=tk.W, side=tk.LEFT)

        # Message input
        self.message_input = scrolledtext.ScrolledText(
            self.chat_frame, height=4, wrap=tk.WORD, bg="#363636", fg="#ffffff", insertbackground="white",
            font=("Segoe UI", 10)
        )
        self.message_input.pack(fill=tk.X, pady=(0, 5))
        self.message_input.bind("<Return>", self.handle_return_key)
        self.message_input.bind("<Shift-Return>", lambda e: None)

        # Buttons
        button_frame = ttk.Frame(self.chat_frame)
        button_frame.pack(fill=tk.X)

        self.web_search_checkbox = ttk.Checkbutton(
            button_frame,
            text="Enable Web Search",
            variable=self.web_search_enabled,
            style="success.TCheckbutton"
        )
        self.web_search_checkbox.pack(side=tk.LEFT)

        self.show_search_debug = tk.BooleanVar(value=True)
        self.search_debug_checkbox = ttk.Checkbutton(
            button_frame,
            text="Show Search Debug Info",
            variable=self.show_search_debug,
            style="info.TCheckbutton"
        )
        self.search_debug_checkbox.pack(side=tk.LEFT, padx=10)

        self.send_button = ttk.Button(button_frame, text="Send 📤", command=self.send_message, style="success.TButton")
        self.send_button.pack(side=tk.RIGHT)

        self.new_session_button = ttk.Button(button_frame, text="New Session 🗒️", command=self.new_session,
                                             style="info.TButton")
        self.new_session_button.pack(side=tk.RIGHT, padx=5)

    def setup_settings_panel(self):
        # Model selection
        model_frame = ttk.LabelFrame(self.settings_frame, text="Model Settings")
        model_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(model_frame, text="Select Model:").pack(anchor=tk.W, padx=5, pady=5)
        self.model_combo = ttk.Combobox(model_frame, textvariable=self.current_model)
        self.model_combo.pack(fill=tk.X, padx=5, pady=5)

        self.refresh_models_btn = ttk.Button(
            model_frame, text="Refresh Models", command=self.refresh_models, style="info.TButton"
        )
        self.refresh_models_btn.pack(fill=tk.X, padx=5, pady=5)

        # Web Search Settings
        search_frame = ttk.LabelFrame(self.settings_frame, text="Web Search Settings")
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(search_frame, text="Search Engine:").pack(anchor=tk.W, padx=5, pady=5)
        self.search_engine_combo = ttk.Combobox(search_frame, values=["DuckDuckGo", "DuckDuckGo API", "Google"])
        self.search_engine_combo.current(0 if not DDGS_AVAILABLE else 1)
        self.search_engine_combo.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(search_frame, text="Max Search Results:").pack(anchor=tk.W, padx=5, pady=5)
        self.max_results_spinbox = ttk.Spinbox(search_frame, from_=1, to=10, width=5)
        self.max_results_spinbox.set(3)
        self.max_results_spinbox.pack(anchor=tk.W, padx=5, pady=5)

        ttk.Label(search_frame, text="Search Timeout (seconds):").pack(anchor=tk.W, padx=5, pady=5)
        self.search_timeout_spinbox = ttk.Spinbox(search_frame, from_=5, to=30, width=5)
        self.search_timeout_spinbox.set(10)
        self.search_timeout_spinbox.pack(anchor=tk.W, padx=5, pady=5)

        # Status frame
        status_frame = ttk.LabelFrame(self.settings_frame, text="Server Status")
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_label = ttk.Label(status_frame, text="Checking connection...")
        self.status_label.pack(anchor=tk.W, padx=5, pady=5)

        # Sessions frame
        sessions_frame = ttk.LabelFrame(self.settings_frame, text="Chat Sessions")
        sessions_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        sessions_container = ttk.Frame(sessions_frame)
        sessions_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(sessions_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.sessions_listbox = tk.Listbox(
            sessions_container,
            bg="#363636",
            fg="#ffffff",
            selectbackground="#4a6da7",
            selectforeground="#ffffff",
            activestyle="none",
            highlightthickness=0,
            bd=0
        )
        self.sessions_listbox.pack(fill=tk.BOTH, expand=True)
        self.sessions_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.sessions_listbox.yview)

        self.sessions_listbox.bind("<Double-1>", self.open_selected_session)

        session_buttons_frame = ttk.Frame(sessions_frame)
        session_buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        self.open_session_btn = ttk.Button(
            session_buttons_frame, text="Open", command=self.open_selected_session, style="primary.TButton"
        )
        self.open_session_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.delete_session_btn = ttk.Button(
            session_buttons_frame, text="Delete", command=self.delete_selected_session, style="danger.TButton"
        )
        self.delete_session_btn.pack(side=tk.LEFT)

        self.export_session_btn = ttk.Button(
            session_buttons_frame, text="Export", command=self.export_selected_session, style="secondary.TButton"
        )
        self.export_session_btn.pack(side=tk.RIGHT)

        threading.Thread(target=self.check_server_connection, daemon=True).start()

    def handle_return_key(self, event):
        if not event.state & 0x1:
            self.send_message()
            return "break"
        return None

    def check_server_connection(self):
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            if response.status_code == 200:
                self.root.after(0, lambda: self.status_label.config(
                    text="✅ Connected to Ollama server", foreground="green"))
            else:
                self.root.after(0, lambda: self.status_label.config(
                    text=f"⚠️ Server error: {response.status_code}", foreground="orange"))
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(
                text="❌ Cannot connect to Ollama server", foreground="red"))

    def refresh_models(self):
        self.refresh_models_btn.config(state=tk.DISABLED, text="Refreshing...")

        def _refresh():
            try:
                response = requests.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [model["name"] for model in models]
                    self.root.after(0, lambda: self._update_model_list(model_names))
                else:
                    self.root.after(0, lambda: self._show_error(f"Server returned: {response.status_code}"))
            except Exception as e:
                self.root.after(0, lambda: self._show_error(f"Connection error: {str(e)}"))
            self.root.after(0, lambda: self.refresh_models_btn.config(state=tk.NORMAL, text="Refresh Models"))

        threading.Thread(target=_refresh, daemon=True).start()

    def _update_model_list(self, model_names):
        self.model_combo["values"] = model_names
        if model_names and not self.current_model.get():
            self.current_model.set(model_names[0])

    def _show_error(self, message):
        print(f"❌ {message}")
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"Error: {message}\n\n", "error_msg")
        self.chat_display.tag_configure("error_msg", foreground="#ff6b6b")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def perform_web_search(self, query):
        self.search_debug_info = f"Search query: \"{query}\"\n"
        self.search_debug_info += f"Search time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

        max_results = int(self.max_results_spinbox.get())
        search_engine = self.search_engine_combo.get()
        timeout = int(self.search_timeout_spinbox.get())

        self.search_debug_info += f"Search engine: {search_engine}\n"
        self.search_debug_info += f"Max results: {max_results}\n"
        self.search_debug_info += f"Timeout: {timeout} seconds\n\n"

        search_results = []

        try:
            if search_engine == "DuckDuckGo API" and DDGS_AVAILABLE:
                self.search_debug_info += "Using DuckDuckGo Search API\n"
                try:
                    with DDGS() as ddgs:
                        ddgs_results = list(ddgs.text(query, max_results=max_results))
                        self.search_debug_info += f"Found {
                            for result in ddgs_results:
                                                        search_results.append({
                                                            'title': result.get('title', 'No title'),
                                                            'snippet': result.get('body', 'No snippet'),
                                                            'url': result.get('href', 'No URL')
                                                        })
                                            except Exception as e:
                                                self.search_debug_info += f"DuckDuckGo API error: {str(e)}\n"
                                        elif search_engine == "DuckDuckGo" or (search_engine == "DuckDuckGo API" and not DDGS_AVAILABLE):
                                            self.search_debug_info += "Using DuckDuckGo HTML search\n"
                                            try:
                                                # Use the HTML search method
                                                encoded_query = quote_plus(query)
                                                url = f"{self.search_engine_url}{encoded_query}"

                                                headers = {
                                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                                                }

                                                response = requests.get(url, headers=headers, timeout=timeout)
                                                response.raise_for_status()

                                                soup = BeautifulSoup(response.text, 'html.parser')

                                                # Extract search results
                                                results = soup.select('.result')
                                                count = 0

                                                for result in results:
                                                    if count >= max_results:
                                                        break

                                                    title_elem = result.select_one('.result__title')
                                                    snippet_elem = result.select_one('.result__snippet')
                                                    url_elem = result.select_one('.result__url')

                                                    if title_elem and snippet_elem:
                                                        title = title_elem.get_text(strip=True)
                                                        snippet = snippet_elem.get_text(strip=True)
                                                        url = url_elem.get_text(strip=True) if url_elem else "No URL"

                                                        if title and snippet:
                                                            search_results.append({
                                                                'title': title,
                                                                'snippet': snippet,
                                                                'url': url
                                                            })
                                                            count += 1

                                            except Exception as e:
                                                self.search_debug_info += f"DuckDuckGo search error: {str(e)}\n"

                                        else:  # Google
                                            self.search_debug_info += "Using Google search\n"
                                            try:
                                                encoded_query = quote_plus(query)
                                                url = f"https://www.google.com/search?q={encoded_query}"

                                                headers = {
                                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                                                }

                                                response = requests.get(url, headers=headers, timeout=timeout)
                                                response.raise_for_status()

                                                soup = BeautifulSoup(response.text, 'html.parser')

                                                # Extract Google search results
                                                results = soup.select('div.g')
                                                count = 0

                                                for result in results:
                                                    if count >= max_results:
                                                        break

                                                    title_elem = result.select_one('h3')
                                                    snippet_elem = result.select_one('div.VwiC3b')
                                                    url_elem = result.select_one('cite')

                                                    if title_elem and snippet_elem:
                                                        title = title_elem.get_text(strip=True)
                                                        snippet = snippet_elem.get_text(strip=True)
                                                        url = url_elem.get_text(strip=True) if url_elem else "No URL"

                                                        if title and snippet:
                                                            search_results.append({
                                                                'title': title,
                                                                'snippet': snippet,
                                                                'url': url
                                                            })
                                                            count += 1

                                            except Exception as e:
                                                self.search_debug_info += f"Google search error: {str(e)}\n"

                                    except Exception as e:
                                        self.search_debug_info += f"Search error: {str(e)}\n"

                                    self.search_debug_info += f"Found {len(search_results)} results\n\n"

                                    # Format results
                                    if search_results:
                                        formatted_results = []
                                        for i, result in enumerate(search_results, 1):
                                            formatted_result = f"[{i}] {result['title']}\n{result['url']}\n{result['snippet']}\n"
                                            formatted_results.append(formatted_result)
                                            self.search_debug_info += f"Result {i}:\nTitle: {result['title']}\nURL: {result['url']}\nSnippet: {result['snippet']}\n\n"

                                        return "\n".join(formatted_results)
                                    else:
                                        self.search_debug_info += "No results found\n"
                                        return "No search results found."

                                def send_message(self):
                                    if self.is_processing:
                                        return

                                    user_message = self.message_input.get("1.0", tk.END).strip()
                                    if not user_message:
                                        return

                                    # Clear the input field
                                    self.message_input.delete("1.0", tk.END)

                                    # Check if the model is selected
                                    if not self.current_model.get():
                                        messagebox.showwarning("Warning", "Please select a model first.")
                                        return

                                    self.is_processing = True
                                    self.send_button.config(state=tk.DISABLED)

                                    # Add user message to the chat display
                                    self.chat_display.config(state=tk.NORMAL)
                                    self.chat_display.insert(tk.END, f"You: ", "user_prefix")
                                    self.chat_display.insert(tk.END, f"{user_message}\n\n", "user_msg")
                                    self.chat_display.tag_configure("user_prefix", foreground="#4a86e8", font=("Segoe UI", 10, "bold"))
                                    self.chat_display.tag_configure("user_msg", foreground="#ffffff")
                                    self.chat_display.see(tk.END)
                                    self.chat_display.config(state=tk.DISABLED)

                                    # Create a progress bar
                                    self.progress_label.config(text="Thinking...")
                                    self.progress = ttk.Progressbar(self.progress_frame, mode="indeterminate", length=200)
                                    self.progress.pack(side=tk.LEFT, padx=(10, 0))
                                    self.progress.start(10)

                                    # Start a new thread to process the message
                                    threading.Thread(target=self.process_message, args=(user_message,), daemon=True).start()

                                def process_message(self, user_message):
                                    search_results = ""

                                    # Perform web search if enabled
                                    if self.web_search_enabled.get() and any(keyword in user_message.lower() for keyword in
                                                                           ["search", "find", "look up", "information", "about", "what is", "who is", "where is", "when", "why", "how"]):
                                        self.update_progress_status("Searching the web...")
                                        search_results = self.perform_web_search(user_message)

                                    # Prepare the message history
                                    messages = []
                                    for msg in self.message_history:
                                        messages.append({"role": msg["role"], "content": msg["content"]})

                                    # Add the user message to the history
                                    user_message_with_search = user_message
                                    self.message_history.append({"role": "user", "content": user_message})

                                    # If search results are available, include them in the message to the model
                                    if search_results:
                                        user_message_with_search = f"{user_message}\n\nSearch results:\n{search_results}"

                                    # Update the status
                                    self.update_progress_status("Generating response...")

                                    try:
                                        # Make the API call
                                        response = requests.post(
                                            f"{self.ollama_url}/api/chat",
                                            json={
                                                "model": self.current_model.get(),
                                                "messages": messages + [{"role": "user", "content": user_message_with_search}],
                                                "stream": True
                                            },
                                            stream=True
                                        )

                                        if response.status_code != 200:
                                            error_message = f"Error {response.status_code}: {response.text}"
                                            self.root.after(0, lambda: self._show_error(error_message))
                                            return

                                        # Add the model's response to the chat display
                                        self.root.after(0, lambda: self.add_model_response_header())

                                        # Process the streaming response
                                        full_response = ""
                                        for line in response.iter_lines():
                                            if line:
                                                try:
                                                    json_line = json.loads(line)
                                                    if "message" in json_line and "content" in json_line["message"]:
                                                        content = json_line["message"]["content"]
                                                        full_response += content
                                                        self.root.after(0, lambda c=content: self.update_chat_display(c))
                                                except json.JSONDecodeError:
                                                    pass

                                        # Add the model's response to the message history
                                        self.message_history.append({"role": "assistant", "content": full_response})

                                        # Save the session
                                        self.save_current_session()

                                        # Show search debug info if enabled
                                        if self.web_search_enabled.get() and search_results and self.show_search_debug.get():
                                            self.root.after(0, lambda: self.show_search_debug_info())

                                    except Exception as e:
                                        self.root.after(0, lambda: self._show_error(f"Error: {str(e)}"))

                                    # Clean up
                                    self.root.after(0, self.cleanup_after_processing)

                                def update_progress_status(self, status):
                                    self.root.after(0, lambda: self.progress_label.config(text=status))

                                def add_model_response_header(self):
                                    self.chat_display.config(state=tk.NORMAL)
                                    self.chat_display.insert(tk.END, f"{self.current_model.get()}: ", "model_prefix")
                                    self.chat_display.tag_configure("model_prefix", foreground="#50c878", font=("Segoe UI", 10, "bold"))
                                    self.chat_display.see(tk.END)
                                    self.chat_display.config(state=tk.DISABLED)

                                def update_chat_display(self, content):
                                    self.chat_display.config(state=tk.NORMAL)
                                    self.chat_display.insert(tk.END, content, "model_msg")
                                    self.chat_display.tag_configure("model_msg", foreground="#ffffff")
                                    self.chat_display.see(tk.END)
                                    self.chat_display.config(state=tk.DISABLED)

                                def show_search_debug_info(self):
                                    self.chat_display.config(state=tk.NORMAL)
                                    self.chat_display.insert(tk.END, "\n\n", "debug_msg")
                                    self.chat_display.insert(tk.END, "Search Debug Info:\n", "debug_header")
                                    self.chat_display.insert(tk.END, self.search_debug_info, "debug_msg")
                                    self.chat_display.tag_configure("debug_header", foreground="#ffcc00", font=("Segoe UI", 9, "bold"))
                                    self.chat_display.tag_configure("debug_msg", foreground="#888888", font=("Segoe UI", 9))
                                    self.chat_display.see(tk.END)
                                    self.chat_display.config(state=tk.DISABLED)

                                def cleanup_after_processing(self):
                                    self.is_processing = False
                                    self.send_button.config(state=tk.NORMAL)
                                    self.progress_label.config(text="")
                                    if self.progress:
                                        self.progress.stop()
                                        self.progress.destroy()
                                        self.progress = None
                                    self.update_session_display()

                                def new_session(self):
                                    # Create a new session with a timestamp
                                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    session_id = f"session_{int(time.time())}"
                                    self.sessions[session_id] = {
                                        "title": f"New Session - {timestamp}",
                                        "messages": [],
                                        "created_at": timestamp,
                                        "updated_at": timestamp,
                                        "model": self.current_model.get() if self.current_model.get() else "Default"
                                    }

                                    # Set the current session ID
                                    self.current_session_id = session_id

                                    # Clear the chat display
                                    self.chat_display.config(state=tk.NORMAL)
                                    self.chat_display.delete("1.0", tk.END)
                                    self.chat_display.config(state=tk.DISABLED)

                                    # Clear the message history
                                    self.message_history = []

                                    # Update the session display
                                    self.update_session_display()

                                    # Save the session
                                    self.save_current_session()

                                def update_session_display(self):
                                    # Update the session display in the listbox
                                    self.sessions_listbox.delete(0, tk.END)
                                    self.session_id_mapping = {}

                                    for i, (session_id, session) in enumerate(sorted(self.sessions.items(),
                                                                                    key=lambda x: x[1]["updated_at"],
                                                                                    reverse=True)):
                                        display_name = session["title"]
                                        if session_id == self.current_session_id:
                                            display_name = f"➤ {display_name}"

                                        self.sessions_listbox.insert(tk.END, display_name)
                                        self.session_id_mapping[i] = session_id

                                    # Update the chat window title
                                    if self.current_session_id and self.current_session_id in self.sessions:
                                        self.chat_label.config(text=f"🗨️ {self.sessions[self.current_session_id]['title']}")

                                def open_selected_session(self, event=None):
                                    selection = self.sessions_listbox.curselection()
                                    if not selection:
                                        return

                                    index = selection[0]
                                    session_id = self.session_id_mapping.get(index)

                                    if not session_id or session_id not in self.sessions:
                                        return

                                    self.open_session(session_id)

                                def open_session(self, session_id):
                                    if session_id == self.current_session_id:
                                        return

                                    # Save the current session before opening a new one
                                    self.save_current_session()

                                    # Load the selected session
                                    self.current_session_id = session_id
                                    self.message_history = self.sessions[session_id]["messages"].copy()

                                    # Update the model if it's stored in the session
                                    if "model" in self.sessions[session_id] and self.sessions[session_id]["model"] in self.model_combo["values"]:
                                        self.current_model.set(self.sessions[session_id]["model"])

                                    # Update the chat display
                                    self.chat_display.config(state=tk.NORMAL)
                                    self.chat_display.delete("1.0", tk.
                                                    }