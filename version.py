"""
Version information for the Hierarchical State Machine Modeller
"""

__version__ = "1.0.0"
__version_info__ = (1, 0, 0)

# Version history
VERSION_HISTORY = """
Version 1.0.0 (2025-11-21)
==========================
Initial release with complete hierarchical state machine modeling and simulation capabilities.

Features:
- Visual state machine editor with drag-and-drop interface
- Support for StateMachine and State node types
- Hierarchical state nesting with parent-child relationships
- Initial state marking for states
- Edge creation with orthogonal routing and waypoints
- Undo/Redo functionality for all operations
- JSON import/export for saving and loading designs

Simulator Mode:
- Complete read-only simulation mode
- Hierarchical state machine execution
- Automatic initial state entry with recursive child resolution
- State transition validation (source and hierarchy checks)
- Visual feedback: orange border + yellow smiley face on active state
- State path display in status bar
- Click edge control points to trigger transitions
- All editing disabled in simulator mode

Naming Conventions:
- Edges: EV_1, EV_2, EV_3, ...
- States: State1St, State2St, State3St, ...
- StateMachines: Statemachine1Sm, Statemachine2Sm, ...

UI/UX:
- Modern toolbar with node type buttons and icons
- Simulator ON/OFF toggle button
- Context menus for operations
- Resize handles for nodes
- Title editing via double-click
- Color-coded node types (green for StateMachine, darker green for State)
"""

def get_version():
    """Return the current version string"""
    return __version__

def get_version_info():
    """Return the version as a tuple"""
    return __version_info__

def print_version():
    """Print version information"""
    print(f"Hierarchical State Machine Modeller v{__version__}")
    print("Copyright (c) 2025")
    print()
    print(VERSION_HISTORY)

if __name__ == "__main__":
    print_version()
