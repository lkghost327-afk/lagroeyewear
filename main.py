"""
LagroEyewear - AI-Powered Eye Health & Blink Rate Monitor

Main entry point for the application. Initializes all components
and launches the GUI.
"""

import sys
import os

# Add the project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
from ui.main_window import MainWindow


def main():
    """Initialize and run the LagroEyewear application."""
    # Set CustomTkinter appearance
    ctk.set_appearance_mode('dark')
    ctk.set_default_color_theme('blue')
    
    # Create and run the main window
    app = MainWindow()
    
    # Handle clean shutdown
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.quit_app()
    except Exception as e:
        print(f'Fatal error: {e}')
        app.quit_app()


if __name__ == '__main__':
    main()
