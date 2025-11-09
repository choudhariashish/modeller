"""
Modeller - Node Editor Application
Main entry point for the application.
All classes are in node.py for better separation of concerns.
"""

import sys
from PyQt5.QtWidgets import QApplication
from node import NodeEditorWindow


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show the main window
    window = NodeEditorWindow()
    
    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
