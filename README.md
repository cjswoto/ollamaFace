# ollamaFace
===================================================
OllamaFace Master Application
===================================================

Overview
--------
OllamaFace is a master container application that integrates two key components:
  1. Ollama Setup Wizard – A GUI-based wizard to check system prerequisites, install, and manage
     the local Ollama service and download AI models.
  2. Ollama Chat (Local LLM Interface) – A chat interface that connects to the local Ollama service,
     allowing you to interact with a local language model.

This project uses Python’s Tkinter library enhanced with ttkbootstrap for modern UI styling.
The master container is built in main.py which organizes the two components in a tabbed interface.

Features
--------
- Tabbed Interface: Easily switch between the Ollama Setup Wizard and the Ollama Chat interface.
- Setup Wizard:
  - Checks system prerequisites (CPU architecture, system RAM, and disk space).
  - Verifies if Ollama is installed and whether the service is running.
  - Provides options to install or start Ollama.
  - Allows downloading of pre-defined and custom AI models.
  - Dynamically adjusts its layout to fill the full width of the parent canvas.
- Chat Interface:
  - Provides a local LLM chat interface.
  - Includes model selection, conversation history, and session management.
  - Integrates optional web search functionality to enhance query processing.

Requirements
------------
- Python 3.6 or higher
- Tkinter (usually bundled with Python)
- ttkbootstrap
- requests
- Pillow (PIL)
- duckduckgo_search (optional, for enhanced web search functionality)
- Ollama installed and running (see below)

Ollama Dependency
-----------------
Ollama is required for local AI inference. You must have Ollama installed and running on your system 
for the Chat Interface to function properly. Please visit:
    https://ollama.com
for installation instructions.

**   The Setup Wizard in this application will verify the installation and prompt you to install or start Ollama if necessary.

Installation
------------
1. Clone the Repository:
   git clone https://github.com/yourusername/ollamaface.git
   cd ollamaface

2. Install Required Dependencies:
   pip install ttkbootstrap requests Pillow duckduckgo_search

3. Install Ollama:
   Follow the instructions at https://ollama.com to install Ollama on your system.


Usage
-----
1. Run the Master Application:
   python main.py

2. Tabbed Interface:
   - The application window opens with two tabs:
     - Ollama Wizard: Use this tab to run system checks, install or start the Ollama service, and download AI models.
     - Ollama Chat: Use this tab to interact with your locally running Ollama service via a chat interface.
   - The interface automatically adjusts to fill the available width of the window.

Project Structure
-----------------
- main.py: The master container that organizes the two components in a tabbed interface.
- OllamaWizard.py: Contains the code for the Setup Wizard including system checks, installation status, and model download functionality.
- OllamaGUI.py: Contains the code for the Chat Interface, managing conversations, session history, and optional web search integration.

Customization
-------------
- You can modify the list of featured models by editing the “self.featured_models” list in OllamaWizard.py.
- UI themes can be changed by altering the ttkbootstrap Style settings in each module.

Contributing
------------
Contributions, issues, and feature requests are welcome! Feel free to check the issues page if you want to contribute.

License
-------
This project is licensed under the MIT License. See the LICENSE file for more details.

Contact
-------
For questions or support, please contact your.email@example.com.

===================================================
