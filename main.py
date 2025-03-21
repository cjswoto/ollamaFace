import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from OllamaWizard import OllamaSetupWizard
from OllamaGUI import OllamaGUI

class MasterContainer:
    def __init__(self, root):
        self.root = root
        self.root.title("Master Application - Ollama Wizard | Ollama Chat")
        self.root.geometry("1200x800")

        # Apply a modern theme
        self.style = tb.Style(theme="superhero")

        # Create a Notebook (Tabbed Interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both")

        # Create tabs for each application
        self.create_ollamawizard_tab()
        self.create_ollamachat_tab()

    def create_ollamawizard_tab(self):
        """Create a tab for Ollama Wizard and properly display it."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🛠️ Ollama Wizard")
        self.embed_application(frame, OllamaSetupWizard)

    def create_ollamachat_tab(self):
        """Create a tab for Ollama Chat and properly display it."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="💬 Ollama Chat")
        self.embed_application(frame, OllamaGUI)

    def embed_application(self, parent_frame, app_class):
        """Forces the application to properly render inside the assigned frame."""
        embedded_frame = ttk.Frame(parent_frame)
        embedded_frame.pack(expand=True, fill="both")

        # Trick: Ensure the app initializes AFTER the parent frame is ready
        self.root.after(100, lambda: app_class(embedded_frame))

if __name__ == "__main__":
    root = tb.Window(themename="superhero")
    app = MasterContainer(root)
    root.mainloop()
