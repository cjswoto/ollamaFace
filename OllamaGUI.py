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

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False


class OllamaGUI:
    def __init__(self, parent):
        """
        If 'parent' is a Tk root window, we can set the window title.
        Otherwise, we create an internal Frame so this class can also be embedded
        inside another application (e.g. a Notebook tab).
        """
        if hasattr(parent, "title"):
            parent.title("OllamaChat - Local LLM Interface")
            self.root = parent
        else:
            self.root = tk.Frame(parent)
            self.root.pack(fill=tk.BOTH, expand=True)

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
        self.sessions_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "sessions"
        )
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)

        # Setup main UI
        self.setup_ui()

        # Create a mapping for Listbox indices to session IDs
        self.session_id_mapping = {}

        # Load existing sessions
        self.load_sessions()

        # Create a new session at startup
        self.new_session()

        # Check for required packages
        self.check_required_packages()

        # IMPORTANT: Schedule background tasks *after* the main loop starts
        # This avoids "main thread is not in main loop" errors.
        self.root.after(100, self.start_background_tasks)

    def start_background_tasks(self):
        """Start background tasks once the main loop is running."""
        # Refresh models in a background thread
        threading.Thread(target=self.refresh_models, daemon=True).start()
        # Check server connection in a background thread
        threading.Thread(target=self.check_server_connection, daemon=True).start()

    def check_required_packages(self):
        """Check if required packages are installed and notify user if not."""
        missing_packages = []
        if not DDGS_AVAILABLE:
            missing_packages.append("duckduckgo_search")

        if missing_packages:
            message = "For better search functionality, consider installing these packages:\n\n"
            message += "\n".join([f"pip install {pkg}" for pkg in missing_packages])
            self.root.after(
                1000, lambda: messagebox.showinfo("Package Recommendations", message)
            )

    def setup_ui(self):
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left frame (chat interface)
        self.chat_frame = ttk.Frame(self.paned)
        self.paned.add(self.chat_frame, weight=3)

        # Right frame (model settings)
        self.settings_frame = ttk.Frame(self.paned)
        self.paned.add(self.settings_frame, weight=1)

        self.setup_chat_interface()
        self.setup_settings_panel()

    def setup_chat_interface(self):
        self.chat_label = ttk.Label(
            self.chat_frame, text="🗨️ Conversation", font=("Segoe UI", 12, "bold")
        )
        self.chat_label.pack(anchor=tk.W, pady=(0, 5))

        self.chat_display = scrolledtext.ScrolledText(
            self.chat_frame,
            wrap=tk.WORD,
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="white",
            font=("Segoe UI", 10),
            height=20,
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.chat_display.config(state=tk.DISABLED)

        self.progress_frame = ttk.Frame(self.chat_frame)
        self.progress_frame.pack(fill=tk.X, pady=(0, 5))
        self.progress_label = ttk.Label(self.progress_frame, text="", font=("Segoe UI", 9))
        self.progress_label.pack(anchor=tk.W, side=tk.LEFT)

        self.message_input = scrolledtext.ScrolledText(
            self.chat_frame,
            height=4,
            wrap=tk.WORD,
            bg="#363636",
            fg="#ffffff",
            insertbackground="white",
            font=("Segoe UI", 10),
        )
        self.message_input.pack(fill=tk.X, pady=(0, 5))
        self.message_input.bind("<Return>", self.handle_return_key)
        self.message_input.bind("<Shift-Return>", lambda e: None)

        button_frame = ttk.Frame(self.chat_frame)
        button_frame.pack(fill=tk.X)

        self.web_search_checkbox = ttk.Checkbutton(
            button_frame,
            text="Enable Web Search",
            variable=self.web_search_enabled,
            style="success.TCheckbutton",
        )
        self.web_search_checkbox.pack(side=tk.LEFT)

        self.show_search_debug = tk.BooleanVar(value=True)
        self.search_debug_checkbox = ttk.Checkbutton(
            button_frame,
            text="Show Search Debug Info",
            variable=self.show_search_debug,
            style="info.TCheckbutton",
        )
        self.search_debug_checkbox.pack(side=tk.LEFT, padx=10)

        self.send_button = ttk.Button(
            button_frame, text="Send 📤", command=self.send_message, style="success.TButton"
        )
        self.send_button.pack(side=tk.RIGHT)

        self.new_session_button = ttk.Button(
            button_frame,
            text="New Session 🗒️",
            command=self.new_session,
            style="info.TButton",
        )
        self.new_session_button.pack(side=tk.RIGHT, padx=5)

    def setup_settings_panel(self):
        model_frame = ttk.LabelFrame(self.settings_frame, text="Model Settings")
        model_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(model_frame, text="Select Model:").pack(anchor=tk.W, padx=5, pady=5)
        self.model_combo = ttk.Combobox(model_frame, textvariable=self.current_model)
        self.model_combo.pack(fill=tk.X, padx=5, pady=5)

        self.refresh_models_btn = ttk.Button(
            model_frame,
            text="Refresh Models",
            command=self.refresh_models_main_thread,
            style="info.TButton",
        )
        self.refresh_models_btn.pack(fill=tk.X, padx=5, pady=5)

        search_frame = ttk.LabelFrame(self.settings_frame, text="Web Search Settings")
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(search_frame, text="Search Engine:").pack(anchor=tk.W, padx=5, pady=5)
        self.search_engine_combo = ttk.Combobox(
            search_frame, values=["DuckDuckGo", "DuckDuckGo API", "Google"]
        )
        # Default to DuckDuckGo API if available, otherwise DuckDuckGo
        self.search_engine_combo.current(0 if not DDGS_AVAILABLE else 1)
        self.search_engine_combo.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(search_frame, text="Max Search Results:").pack(anchor=tk.W, padx=5, pady=5)
        self.max_results_spinbox = ttk.Spinbox(search_frame, from_=1, to=10, width=5)
        self.max_results_spinbox.set(3)
        self.max_results_spinbox.pack(anchor=tk.W, padx=5, pady=5)

        ttk.Label(search_frame, text="Search Timeout (seconds):").pack(
            anchor=tk.W, padx=5, pady=5
        )
        self.search_timeout_spinbox = ttk.Spinbox(search_frame, from_=5, to=30, width=5)
        self.search_timeout_spinbox.set(10)
        self.search_timeout_spinbox.pack(anchor=tk.W, padx=5, pady=5)

        status_frame = ttk.LabelFrame(self.settings_frame, text="Server Status")
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_label = ttk.Label(status_frame, text="Checking connection...")
        self.status_label.pack(anchor=tk.W, padx=5, pady=5)

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
            bd=0,
        )
        self.sessions_listbox.pack(fill=tk.BOTH, expand=True)
        self.sessions_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.sessions_listbox.yview)

        self.sessions_listbox.bind("<Double-1>", self.open_selected_session)

        session_buttons_frame = ttk.Frame(sessions_frame)
        session_buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        self.open_session_btn = ttk.Button(
            session_buttons_frame,
            text="Open",
            command=self.open_selected_session,
            style="primary.TButton",
        )
        self.open_session_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.delete_session_btn = ttk.Button(
            session_buttons_frame,
            text="Delete",
            command=self.delete_selected_session,
            style="danger.TButton",
        )
        self.delete_session_btn.pack(side=tk.LEFT)

        self.export_session_btn = ttk.Button(
            session_buttons_frame,
            text="Export",
            command=self.export_selected_session,
            style="secondary.TButton",
        )
        self.export_session_btn.pack(side=tk.RIGHT)

    def handle_return_key(self, event):
        """Submit if Shift isn't pressed; otherwise, new line."""
        if not event.state & 0x1:  # Shift key not pressed
            self.send_message()
            return "break"
        return None

    # ----------------------------------------------------------
    #  BACKGROUND TASKS (CALLED AFTER MAIN LOOP STARTS)
    # ----------------------------------------------------------
    def start_background_tasks(self):
        """Start any background tasks once the main loop is running."""
        # Refresh models
        threading.Thread(target=self.refresh_models, daemon=True).start()
        # Check server connection
        threading.Thread(target=self.check_server_connection, daemon=True).start()

    def refresh_models_main_thread(self):
        """Called when user clicks 'Refresh Models' button (main thread)."""
        threading.Thread(target=self.refresh_models, daemon=True).start()

    def refresh_models(self):
        """
        Refresh the list of available models from Ollama in a background thread.
        All UI updates are scheduled back on the main thread using root.after.
        """
        # Disable the button on the main thread
        self.root.after(
            0,
            lambda: self.refresh_models_btn.config(state=tk.DISABLED, text="Refreshing..."),
        )

        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                # Schedule UI update
                self.root.after(0, lambda: self._update_model_list(model_names))
            else:
                # Schedule an error update
                self.root.after(
                    0,
                    lambda: self._show_error(
                        f"Server returned error: {response.status_code}"
                    ),
                )
        except Exception as e:
            # Schedule an error update
            self.root.after(0, lambda: self._show_error(f"Connection error: {str(e)}"))
        finally:
            # Re-enable the button on the main thread
            self.root.after(
                0,
                lambda: self.refresh_models_btn.config(state=tk.NORMAL, text="Refresh Models"),
            )

    def check_server_connection(self):
        """Check if Ollama server is running (background thread)."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            if response.status_code == 200:
                self.root.after(
                    0,
                    lambda: self.status_label.config(
                        text="✅ Connected to Ollama server", foreground="green"
                    ),
                )
            else:
                self.root.after(
                    0,
                    lambda: self.status_label.config(
                        text=f"⚠️ Server error: {response.status_code}", foreground="orange"
                    ),
                )
        except Exception:
            self.root.after(
                0,
                lambda: self.status_label.config(
                    text="❌ Cannot connect to Ollama server", foreground="red"
                ),
            )

    def _update_model_list(self, model_names):
        """Update the model combo with new model names (main thread)."""
        self.model_combo["values"] = model_names
        if model_names and not self.current_model.get():
            self.current_model.set(model_names[0])

    def _show_error(self, message):
        """Display an error message in the chat (must be called on main thread)."""
        print(f"❌ {message}")
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"Error: {message}\n\n", "error_msg")
        self.chat_display.tag_configure("error_msg", foreground="#ff6b6b")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    # ----------------------------------------------------------
    #  WEB SEARCH / MESSAGE HANDLING
    # ----------------------------------------------------------
    def perform_web_search(self, query):
        """Perform a web search in the main thread; returns formatted results or error."""
        self.search_debug_info = f"Search query: \"{query}\"\n"
        self.search_debug_info += f"Search time: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n"

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
                        self.search_debug_info += f"Found {len(ddgs_results)} results\n\n"
                        for i, result in enumerate(ddgs_results):
                            title = result.get("title", "No title")
                            body = result.get("body", "No content")
                            href = result.get("href", "No URL")
                            search_results.append(
                                f"Result {i+1}:\nTitle: {title}\nSnippet: {body}\nURL: {href}\n"
                            )
                            self.search_debug_info += f"Result {i+1} - {title}\n"
                except Exception as e:
                    error_msg = f"DuckDuckGo API error: {str(e)}"
                    self.search_debug_info += (
                        f"Error: {error_msg}\nFalling back to HTML scraping method\n"
                    )
                    search_engine = "DuckDuckGo"

            if search_engine in ["DuckDuckGo", "Google"]:
                if search_engine == "DuckDuckGo":
                    search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
                    self.search_debug_info += f"Using DuckDuckGo HTML scraping\nURL: {search_url}\n"
                else:
                    search_url = f"https://www.google.com/search?q={quote_plus(query)}"
                    self.search_debug_info += f"Using Google HTML scraping\nURL: {search_url}\n"

                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                        " AppleWebKit/537.36 (KHTML, like Gecko)"
                        " Chrome/91.0.4472.124 Safari/537.36"
                    )
                }
                response = requests.get(search_url, headers=headers, timeout=timeout)
                self.search_debug_info += f"Response status code: {response.status_code}\n"
                if response.status_code != 200:
                    return f"Error: Search engine returned status code {response.status_code}"

                content = response.text

                if search_engine == "DuckDuckGo":
                    # Use regex or BeautifulSoup for parsing
                    result_divs = re.findall(
                        r'<div class="result__body">(.*?)</div>\s*</div>', content, re.DOTALL
                    )
                    self.search_debug_info += f"Found {len(result_divs)} result divs in HTML\n\n"
                    for i, div in enumerate(result_divs[:max_results]):
                        title_match = re.search(
                            r'<a class="result__a" href=".*?">(.*?)</a>', div, re.DOTALL
                        )
                        title = (
                            html.unescape(re.sub(r"<.*?>", "", title_match.group(1)))
                            if title_match
                            else "No title"
                        )
                        snippet_match = re.search(
                            r'<a class="result__snippet".*?>(.*?)</a>', div, re.DOTALL
                        )
                        snippet = (
                            html.unescape(re.sub(r"<.*?>", "", snippet_match.group(1)))
                            if snippet_match
                            else "No snippet"
                        )
                        url_match = re.search(
                            r'<a class="result__a" href="(.*?)"', div, re.DOTALL
                        )
                        url = url_match.group(1) if url_match else "No URL"
                        search_results.append(
                            f"Result {i+1}:\nTitle: {title}\nSnippet: {snippet}\nURL: {url}\n"
                        )
                        self.search_debug_info += f"Result {i+1} - {title}\n"

                elif search_engine == "Google":
                    result_divs = re.findall(
                        r'<div class="g">(.*?)</div>\s*</div>\s*</div>', content, re.DOTALL
                    )
                    self.search_debug_info += f"Found {len(result_divs)} result divs in HTML\n\n"
                    for i, div in enumerate(result_divs[:max_results]):
                        title_match = re.search(
                            r'<h3 class=".*?">(.*?)</h3>', div, re.DOTALL
                        )
                        title = (
                            html.unescape(re.sub(r"<.*?>", "", title_match.group(1)))
                            if title_match
                            else "No title"
                        )
                        snippet_match = re.search(
                            r'<span class=".*?">(.*?)</span>', div, re.DOTALL
                        )
                        snippet = (
                            html.unescape(re.sub(r"<.*?>", "", snippet_match.group(1)))
                            if snippet_match
                            else "No snippet"
                        )
                        url_match = re.search(r'<a href="(https?://.*?)"', div, re.DOTALL)
                        url = url_match.group(1) if url_match else "No URL"
                        search_results.append(
                            f"Result {i+1}:\nTitle: {title}\nSnippet: {snippet}\nURL: {url}\n"
                        )
                        self.search_debug_info += f"Result {i+1} - {title}\n"

            if not search_results:
                self.search_debug_info += "No search results found.\n"
                return "No search results found."

            self.search_debug_info += (
                f"\nSearch completed successfully with {len(search_results)} results."
            )
            formatted_results = f"Web search results for: {query}\n\n" + "\n".join(search_results)
            return formatted_results

        except Exception as e:
            error_msg = f"Error performing web search: {str(e)}"
            self.search_debug_info += f"\n{error_msg}"
            return error_msg

    def send_message(self, event=None):
        """Send a message to the Ollama API (main thread)."""
        if self.is_processing:
            return

        message = self.message_input.get("1.0", tk.END).strip()
        if not message:
            return

        model = self.current_model.get()
        if not model:
            self._show_error("Please select a model first")
            return

        self.disable_input()
        self.show_loading_indicator()
        self.message_input.delete("1.0", tk.END)

        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"You: {message}\n\n", "user_msg")
        self.chat_display.tag_configure("user_msg", foreground="#8aecff")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

        self.message_history.append({"role": "user", "content": message})
        self.is_processing = True

        # Process in a background thread
        threading.Thread(target=self._process_message, args=(model, message), daemon=True).start()

    def disable_input(self):
        self.message_input.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        self.web_search_checkbox.config(state=tk.DISABLED)
        self.search_debug_checkbox.config(state=tk.DISABLED)

    def enable_input(self):
        self.message_input.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)
        self.web_search_checkbox.config(state=tk.NORMAL)
        self.search_debug_checkbox.config(state=tk.NORMAL)
        self.message_input.focus_set()

    def show_loading_indicator(self):
        if hasattr(self, "progress_bar") and self.progress_bar:
            self.progress_bar.destroy()

        self.progress_label.config(text="🤖 AI is thinking...")
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="indeterminate", length=200)
        self.progress_bar.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        self.progress_bar.start(15)

    def hide_loading_indicator(self):
        if hasattr(self, "progress_bar") and self.progress_bar:
            self.progress_bar.stop()
            self.progress_bar.destroy()
            self.progress_bar = None

        self.progress_label.config(text="")

    def _process_message(self, model, message):
        """Background thread that sends request to Ollama."""
        try:
            search_results = None
            if self.web_search_enabled.get():
                # Show "Searching the web..." on main thread
                self.root.after(0, lambda: self.progress_label.config(text="🌐 Searching the web..."))
                search_results = self.perform_web_search(message)
                self.root.after(
                    0, lambda: self.progress_label.config(text="🤖 AI is processing search results...")
                )
                self.root.after(0, lambda: self._show_search_results(search_results))
                if self.show_search_debug.get():
                    self.root.after(0, lambda: self._show_search_debug())

            prompt = message
            if search_results:
                prompt = f"""Question: {message}

Web Search Results:
{search_results}

Please answer the question based on the search results above. If the search results aren't relevant or don't contain the necessary information, use your knowledge to provide the best answer possible."""

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 2048},
                },
            )
            if response.status_code == 200:
                ai_response = response.json().get("response", "")
                self.message_history.append({"role": "assistant", "content": ai_response})
                # Update chat display on main thread
                self.root.after(0, lambda: self._update_chat_with_response(ai_response))
                # Save the session after response on main thread
                self.root.after(0, self.save_current_session)
            else:
                error_message = f"Server error: {response.status_code}"
                self.root.after(0, lambda: self._show_error(error_message))
        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: self._show_error("Cannot connect to Ollama server. Is it running?"))
        except Exception as e:
            self.root.after(0, lambda: self._show_error(f"Error: {str(e)}"))
        finally:
            self.is_processing = False
            self.root.after(0, self.enable_input)
            self.root.after(0, self.hide_loading_indicator)

    def _show_search_results(self, results):
        """Display search results in the chat (main thread)."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"🔍 {results}\n\n", "search_results")
        self.chat_display.tag_configure("search_results", foreground="#a0a0a0", font=("Segoe UI", 9))
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def _show_search_debug(self):
        """Display search debug info in the chat (main thread)."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(
            tk.END, f"🔧 Search Debug Information:\n{self.search_debug_info}\n\n", "debug_info"
        )
        self.chat_display.tag_configure("debug_info", foreground="#8a9a5b", font=("Consolas", 9))
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def _update_chat_with_response(self, response):
        """Update chat with AI response (main thread)."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"AI: {response}\n\n", "ai_msg")
        self.chat_display.tag_configure("ai_msg", foreground="#a8c7fa")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    # --- Session Management ---
    def new_session(self):
        if self.current_session_id:
            self.save_current_session()

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        session_id = f"session_{timestamp}"
        self.current_session_id = session_id
        self.sessions[session_id] = {
            "id": session_id,
            "title": f"Session {datetime.datetime.now():%Y-%m-%d %H:%M}",
            "model": self.current_model.get() if self.current_model.get() else "",
            "messages": [],
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.message_history = []
        self.update_sessions_list()

    def save_current_session(self):
        if not self.current_session_id:
            return
        self.sessions[self.current_session_id]["messages"] = self.message_history
        self.sessions[self.current_session_id]["model"] = self.current_model.get()
        self.sessions[self.current_session_id]["updated_at"] = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        session_file = os.path.join(self.sessions_dir, f"{self.current_session_id}.json")
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(self.sessions[self.current_session_id], f, indent=2)

    def load_sessions(self):
        self.sessions = {}
        session_files = [f for f in os.listdir(self.sessions_dir) if f.endswith(".json")]
        for file in session_files:
            try:
                with open(os.path.join(self.sessions_dir, file), "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                    self.sessions[session_data["id"]] = session_data
            except Exception as e:
                print(f"Error loading session {file}: {str(e)}")
        self.update_sessions_list()

    def update_sessions_list(self):
        self.sessions_listbox.delete(0, tk.END)
        self.session_id_mapping = {}
        sorted_sessions = sorted(
            self.sessions.values(), key=lambda s: s.get("updated_at", ""), reverse=True
        )
        for i, session in enumerate(sorted_sessions):
            title = session.get("title", "Untitled")
            model = session.get("model", "Unknown model")
            updated = session.get("updated_at", "").split()[0]
            if session["id"] == self.current_session_id:
                title = f"➤ {title}"
            entry = f"{title} ({model}) - {updated}"
            self.sessions_listbox.insert(tk.END, entry)
            self.session_id_mapping[i] = session["id"]

    def get_selected_session_id(self):
        selected_indices = self.sessions_listbox.curselection()
        if not selected_indices:
            return None
        index = selected_indices[0]
        return self.session_id_mapping.get(index)

    def open_selected_session(self, event=None):
        session_id = self.get_selected_session_id()
        if not session_id or session_id not in self.sessions:
            return
        self.save_current_session()
        session = self.sessions[session_id]
        self.current_session_id = session_id
        model = session.get("model", "")
        if model and model in self.model_combo["values"]:
            self.current_model.set(model)
        self.message_history = session.get("messages", [])
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        for msg in self.message_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                self.chat_display.insert(tk.END, f"You: {content}\n\n", "user_msg")
                self.chat_display.tag_configure("user_msg", foreground="#8aecff")
            elif role == "assistant":
                self.chat_display.insert(tk.END, f"AI: {content}\n\n", "ai_msg")
                self.chat_display.tag_configure("ai_msg", foreground="#a8c7fa")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.update_sessions_list()

    def delete_selected_session(self):
        session_id = self.get_selected_session_id()
        if not session_id or session_id not in self.sessions:
            return
        confirmed = messagebox.askyesno(
            "Confirm Deletion", "Are you sure you want to delete this session?"
        )
        if not confirmed:
            return
        del self.sessions[session_id]
        session_file = os.path.join(self.sessions_dir, f"{session_id}.json")
        if os.path.exists(session_file):
            os.remove(session_file)
        if session_id == self.current_session_id:
            self.new_session()
        else:
            self.update_sessions_list()

    def export_selected_session(self):
        session_id = self.get_selected_session_id()
        if not session_id or session_id not in self.sessions:
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Export Session",
        )
        if not file_path:
            return
        session = self.sessions[session_id]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Session: {session.get('title', 'Untitled')}\n")
            f.write(f"Model: {session.get('model', 'Unknown')}\n")
            f.write(f"Created: {session.get('created_at', '')}\n")
            f.write(f"Updated: {session.get('updated_at', '')}\n")
            f.write("-" * 50 + "\n\n")
            for msg in session.get("messages", []):
                role = "You" if msg.get("role") == "user" else "AI"
                content = msg.get("content", "")
                f.write(f"{role}:\n{content}\n\n")
        messagebox.showinfo("Export Complete", "Session exported successfully!")


if __name__ == "__main__":
    # For standalone testing, create a root window
    root = tb.Window(themename="darkly")
    app = OllamaGUI(root)
    root.mainloop()
