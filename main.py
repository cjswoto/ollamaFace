import os
import logging
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from PIL import Image, ImageTk

# Import the sub-application modules.
# OllamaGUI.py should define a class named OllamaGUI.
# OllamaWizard.py defines a class named OllamaSetupWizard.
import OllamaGUI
import OllamaWizard

# --------------------------------------------------------------------
# 1. Configure Logging
# --------------------------------------------------------------------
log_filename = os.path.join(os.path.dirname(__file__), "ollamaface_main.log")
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,  # use DEBUG for more details
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
logger.info("==== Starting OllamaFace main.py ====")


class OllamaFaceApp:
    def __init__(self, root):
        logger.info("Initializing OllamaFaceApp...")

        self.root = root
        self.root.title("OllamaFace - Container Application")
        self.root.geometry("1200x800")
        logger.info("Main window created with 1200x800 geometry.")

        # Attempt to set the window icon.
        icon_path = os.path.join(os.path.dirname(__file__), "resources", "Icon.png")
        if os.path.exists(icon_path):
            try:
                self.root.iconphoto(True, tk.PhotoImage(file=icon_path))
                logger.info(f"Window icon set from: {icon_path}")
            except Exception as e:
                logger.warning(f"Could not load icon: {e}")
        else:
            logger.warning(f"Icon file not found at: {icon_path}")

        # First, show the splash screen.
        logger.info("Displaying splash screen...")
        self.show_splash_screen()

    def show_splash_screen(self):
        """Display a splash screen covering the entire window."""
        logger.info("Creating splash screen frame.")
        self.splash_frame = ttk.Frame(self.root)
        self.splash_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Paths to images in the resources folder.
        top_image_path = os.path.join(os.path.dirname(__file__), "resources", "Icon.png")
        splash_image_path = os.path.join(os.path.dirname(__file__), "resources", "Icon.png")

        self.top_image = None
        self.splash_image = None

        try:
            top_img_obj = Image.open(top_image_path)
            self.top_image = ImageTk.PhotoImage(top_img_obj)
            logger.info(f"Loaded top image from: {top_image_path}")
        except Exception as e:
            logger.warning(f"Could not load top image: {e}")

        try:
            splash_img_obj = Image.open(splash_image_path)
            self.splash_image = ImageTk.PhotoImage(splash_img_obj)
            logger.info(f"Loaded splash image from: {splash_image_path}")
        except Exception as e:
            logger.warning(f"Could not load splash image: {e}")

        if self.splash_image:
            splash_label = ttk.Label(self.splash_frame, image=self.splash_image)
            splash_label.pack(pady=10)

        info_label = ttk.Label(
            self.splash_frame,
            text="SlackerIT - We Get IT Done",
            font=("Segoe UI", 16, "bold")
        )
        info_label.pack(pady=5)

        app_label = ttk.Label(
            self.splash_frame,
            text="OllamaFace - Private LLM Interface",
            font=("Segoe UI", 20, "bold")
        )
        app_label.pack(pady=5)

        # Change this value to control how long the splash stays visible.
        splash_duration_ms = 2000  # 5000 ms = 5 seconds
        logger.info(f"Splash screen shown; scheduling removal in {splash_duration_ms / 1000} seconds.")
        self.root.after(splash_duration_ms, self.hide_splash_screen)

    def hide_splash_screen(self):
        """Destroy the splash screen and build the main UI."""
        logger.info("Destroying splash screen frame.")
        self.splash_frame.destroy()
        # Now that the splash is gone, build the main Notebook UI.
        self.build_main_ui()

    def build_main_ui(self):
        """Create the Notebook with tabs and instantiate sub-applications."""
        logger.info("Creating main Notebook (tabs)...")
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        # --- Tab 1: Home Config (Wizard) ---
        logger.info("Adding 'Home Config' tab (Wizard).")
        self.home_config_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.home_config_frame, text="Home Config")
        self.home_config_app = OllamaWizard.OllamaSetupWizard(self.home_config_frame)

        # --- Tab 2: OllamaGUI ---
        logger.info("Adding 'OllamaGUI' tab.")
        self.gui_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.gui_frame, text="OllamaGUI")
        self.ollama_gui_app = OllamaGUI.OllamaGUI(self.gui_frame)

        # Ensure the Home Config tab is shown by default.
        self.notebook.select(0)
        logger.info("Main UI built; Home Config tab is active.")


if __name__ == "__main__":
    logger.info("Creating main Tk window with ttkbootstrap theme='darkly'.")
    root = tb.Window(themename="darkly")
    logger.info("Instantiating OllamaFaceApp.")
    app = OllamaFaceApp(root)
    logger.info("Starting main Tkinter event loop.")
    root.mainloop()
    logger.info("Main event loop has ended. Exiting application.")
