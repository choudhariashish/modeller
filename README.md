# Modeller - Node Editor

AI powered software modeling tool with code generation capabilities.

A PyQt5-based node editor application with orthogonal edge routing and interactive edge manipulation.

## Features

### Node Management
- Create and organize nodes in a hierarchical structure
- Container nodes that can hold child nodes
- Nested node support with unlimited depth
- Drag and drop nodes
- Double-click to edit node titles
- Delete nodes via toolbar button or Delete/Backspace keys

### Edge Routing
- Orthogonal (90-degree angle) edge routing between nodes
- Draggable blue endpoint controls to adjust connection points
- Draggable orange waypoint control to adjust edge bend position
- Proportional waypoint movement with endpoint changes
- Edges automatically update when parent nodes move (recursive for all nested children)
- Wider hit area for easier edge selection

### UI Features
- Zoom in/out with mouse wheel
- Pan around the canvas
- Toolbar with delete button
- Keyboard shortcuts (Delete/Backspace for deletion)
- Modern UI with Fusion style
- Grid background with major/minor lines

## Requirements
- Python 3.6+
- PyQt5

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/choudhariashish/modeller.git
   cd modeller
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install PyQt5
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
- **Ctrl + Click + Drag**: Create edge between nodes
- **Click on edge/node + Delete/Backspace**: Delete selected item
- **Toolbar Delete Button**: Delete selected items
- **Double-click node title**: Edit node title
- **Right-click**: Context menu for adding nodes

## License
MIT
