from decommed.modules.gui import OllamaGUI
import ttkbootstrap as tb

if __name__ == "__main__":
    root = tb.Window(themename="darkly")
    app = OllamaGUI(root)
    root.mainloop()
