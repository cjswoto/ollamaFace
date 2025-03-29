import os

def create_dirs_and_files(file_paths):
    """Ensure directories exist and create files if they do not already exist."""
    for file_path in file_paths:
        # Extract directory path and create it if it does not exist
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            print(f"Created directory: {dir_path}")

        # Create the file if it does not exist
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write("# This file was created by the setup script\n")
            print(f"Created file: {file_path}")
        else:
            print(f"Already exists: {file_path}")

# Define the required directories and files
items_to_create = [
    "OllamaDataPrep/ollamadataprep.py",
    "OllamaDataPrep/requirements.txt",
    "OllamaDataPrep/output/"  # This is a directory
]

# Run the script
create_dirs_and_files(items_to_create)
