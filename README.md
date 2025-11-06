# Node Editor with Zoomable Grid

A simple node editor application built with PyQt5 and nodeeditor, featuring a zoomable grid background.

## Features
- Zoom in/out with mouse wheel
- Pan around the canvas with right-click drag
- Add nodes (basic functionality)
- Grid background with major/minor lines
- Modern UI with Fusion style

## Requirements
- Python 3.6+
- PyQt5
- nodeeditor

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```bash
python main.py
```

### Controls
- **Mouse Wheel**: Zoom in/out
- **Right-click + Drag**: Pan around the canvas
- **Left-click + Drag**: Select/Move nodes
- **Delete**: Delete selected nodes

## License
MIT
