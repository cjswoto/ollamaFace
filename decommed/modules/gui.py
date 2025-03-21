import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import ttkbootstrap as tb
import requests
from decommed.modules.session import SessionManager

OLLAMA_API_URL = "http://localhost:11434/api/tags"

class OllamaGUI:
    def __init__(self, parent):
        if hasattr(parent, "title"):
            parent.title("OllamaChat - Local LLM Interface")
            self.root = parent
        else:
            self.root = tk.Frame(parent)
            self.root.pack(fill=tk.BOTH, expand=True)

        self.style = tb.Style(theme="darkly")
        self.current_model = tk.StringVar()
        self.web_search_enabled = tk.BooleanVar(value=True)
        self.show_debug_info = tk.BooleanVar(value=True)
        self.message_history = []
        self.session_manager = SessionManager()
        self.current_session_id = None

        self.setup_ui()
        self.refresh_models()  # Ensure models are loaded at startup
        self.new_session()
        self.load_sessions()

    def setup_ui(self):
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.chat_frame = ttk.Frame(self.paned)
        self.paned.add(self.chat_frame, weight=3)

        self.settings_frame = ttk.Frame(self.paned)
        self.paned.add(self.settings_frame, weight=1)

        self.setup_chat_interface()
        self.setup_settings_panel()

    def setup_chat_interface(self):
        self.chat_display = scrolledtext.ScrolledText(self.chat_frame, wrap=tk.WORD, height=20)
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.chat_display.config(state=tk.DISABLED)

        self.message_input = scrolledtext.ScrolledText(self.chat_frame, height=4, wrap=tk.WORD)
        self.message_input.pack(fill=tk.X, pady=(0, 5))
        self.message_input.bind("<Return>", self.send_message)

        button_frame = ttk.Frame(self.chat_frame)
        button_frame.pack(fill=tk.X)

        self.web_search_checkbox = ttk.Checkbutton(button_frame, text="Enable Web Search", variable=self.web_search_enabled)
        self.web_search_checkbox.pack(side=tk.LEFT)

        self.debug_checkbox = ttk.Checkbutton(button_frame, text="Show Search Debug Info", variable=self.show_debug_info)
        self.debug_checkbox.pack(side=tk.LEFT, padx=10)

        self.send_button = ttk.Button(button_frame, text="Send", command=self.send_message, style="success.TButton")
        self.send_button.pack(side=tk.RIGHT)

    def setup_settings_panel(self):
        model_frame = ttk.LabelFrame(self.settings_frame, text="Model Settings")
        model_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(model_frame, text="Select Model:").pack(anchor=tk.W, padx=5, pady=5)
        self.model_combo = ttk.Combobox(model_frame, textvariable=self.current_model)
        self.model_combo.pack(fill=tk.X, padx=5, pady=5)

        self.refresh_models_btn = ttk.Button(model_frame, text="Refresh Models", command=self.refresh_models, style="primary.TButton")
        self.refresh_models_btn.pack(fill=tk.X, padx=5, pady=5)

    def refresh_models(self):
        try:
            response = requests.get(OLLAMA_API_URL, timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model["name"] for model in models]
                self.model_combo["values"] = model_names
                if model_names:
                    self.current_model.set(model_names[0])
            else:
                messagebox.showerror("Error", f"Server error: {response.status_code}")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Error", "Cannot connect to Ollama server. Make sure it is running.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch models: {str(e)}")

    def send_message(self, event=None):
        message = self.message_input.get("1.0", tk.END).strip()
        if not message:
            return

        model = self.current_model.get()
        if not model:
            messagebox.showerror("Error", "Please select a model before sending a message.")
            return

        self.display_message("You", message)
        self.message_input.delete("1.0", tk.END)

        self.root.after(100, lambda: self.request_llm_response(model, message))

    def request_llm_response(self, model, message):
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": message,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 2048},
                },
                timeout=10,
            )

            if response.status_code == 200:
                ai_response = response.json().get("response", "No response from model.")
                self.display_message("AI", ai_response)
            else:
                self.display_message("AI", f"Error: {response.status_code}")

        except requests.exceptions.ConnectionError:
            self.display_message("AI", "Error: Cannot connect to Ollama server.")
        except requests.exceptions.Timeout:
            self.display_message("AI", "Error: Ollama server timeout.")
        except Exception as e:
            self.display_message("AI", f"Error: {str(e)}")

    def display_message(self, sender, message):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{sender}: {message}\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
