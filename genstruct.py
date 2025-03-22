import os

def create_files(file_paths):
    """Create the specified files if they do not already exist."""
    for file_path in file_paths:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write("""# This file was created by the setup script\n""")
            print(f"Created: {file_path}")
        else:
            print(f"Already exists: {file_path}")

# Define the files to create
files_to_create = [
    "core/__init__.py",
    "core/api.py",
    "core/search.py",
    "core/session.py",
    "core/core_manager.py",
    "gui/__init__.py",
    "gui/chat_interface.py",
    "gui/settings_panel.py",
    "gui/session_panel.py",
    "gui/main.py",
]

# Run the script
create_files(files_to_create)
