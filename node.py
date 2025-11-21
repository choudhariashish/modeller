import sys
import math
import json
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, 
                             QMainWindow, QVBoxLayout, QWidget, QGraphicsItem,
                             QGraphicsRectItem, QGraphicsTextItem, QGraphicsPathItem,
                             QGraphicsEllipseItem, QMenu, QAction, QLineEdit, QSizePolicy,
                             QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF, QByteArray, QTimer, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QPainter, QPen, QColor, QWheelEvent, QBrush, QFont, QPainterPath, QIcon, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from edge import Edge, EdgeControlPoint, WaypointControlPoint, EdgeTitleItem


class UserActionSignalDot(QWidget):
    """A widget that displays a colored dot in the status bar to signal user actions"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 20)  # 10px dot width, 20px height for vertical centering
        self._dot_color = QColor("#4CAF50")  # Default green color
        self._default_color = QColor("#4CAF50")
        
    def paintEvent(self, event):
        """Paint the dot"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(self._dot_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 5, 10, 10)  # 10px diameter, centered vertically
        
    @pyqtProperty(QColor)
    def dotColor(self):
        return self._dot_color
    
    @dotColor.setter
    def dotColor(self, color):
        self._dot_color = color
        self.update()
        
    def blink(self, color, duration=300):
        """Blink the dot with a specific color for a duration in milliseconds"""
        # Set the blink color
        self._dot_color = color
        self.update()
        
        # Reset to default color after duration
        QTimer.singleShot(duration, self._reset_color)
        
    def _reset_color(self):
        """Reset the dot to its default color"""
        self._dot_color = self._default_color
        self.update()


class UserActionMonitor:
    """Monitor and signal user actions through the status bar dot"""
    
    def __init__(self, signal_dot):
        """
        Initialize the user action monitor
        
        Args:
            signal_dot (UserActionSignalDot): The status bar dot widget to control
        """
        self.signal_dot = signal_dot
        self.actions = {
            'node_moved': {'color': QColor("#FF9800"), 'duration': 300},  # Orange
            'node_created': {'color': QColor("#2196F3"), 'duration': 300},  # Blue
            'node_deleted': {'color': QColor("#F44336"), 'duration': 300},  # Red
            'edge_created': {'color': QColor("#9C27B0"), 'duration': 300},  # Purple
        }
        
    def signal_action(self, action_type):
        """
        Signal a user action by blinking the dot
        
        Args:
            action_type (str): Type of action ('node_moved', 'node_created', etc.)
        """
        if action_type in self.actions:
            action = self.actions[action_type]
            self.signal_dot.blink(action['color'], action['duration'])
        
    def add_action_type(self, action_type, color, duration=300):
        """
        Add a new action type to monitor
        
        Args:
            action_type (str): Name of the action type
            color (QColor): Color to blink when this action occurs
            duration (int): Duration of the blink in milliseconds
        """
        self.actions[action_type] = {'color': color, 'duration': duration}


class NodeEditorGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.setScene(scene)
        
        # Set viewport update mode for better performance
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        # Set render hints for better quality
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.HighQualityAntialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        
        # Zoom settings
        self.zoom_in_factor = 1.25
        self.zoom_out_factor = 1 / self.zoom_in_factor
        self.zoom_level = 0
        self.zoom_step = 1
        self.zoom_range = [-10, 10]  # Min and max zoom levels
        
        # Grid settings
        self.grid_size = 20
        self.grid_squares = 5  # Major grid lines every N squares
        
        # Set up the view
        self.setRenderHints(QPainter.Antialiasing | QPainter.HighQualityAntialiasing | 
                           QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        
        # Set scene rect
        self.setSceneRect(-1000, -1000, 2000, 2000)
        
        # Edge creation state
        self.edge_start_node = None
        self.temp_edge = None
        
    def drawBackground(self, painter, rect):
        """Draw the background grid"""
        # Fill the background with the specified color
        painter.fillRect(rect, QColor("#292826"))
        
        # Set up the pen for minor grid lines (10% darker)
        minor_pen = QPen(QColor("#424241"))  # Slightly darker gray with transparency
        minor_pen.setWidth(1)
        painter.setPen(minor_pen)
        
        # Calculate the visible area in scene coordinates
        view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        
        # Add some margin to avoid edge artifacts
        margin = self.grid_size * 2
        left = int((view_rect.left() - margin) / self.grid_size) * self.grid_size
        top = int((view_rect.top() - margin) / self.grid_size) * self.grid_size
        right = int((view_rect.right() + margin) / self.grid_size) * self.grid_size
        bottom = int((view_rect.bottom() + margin) / self.grid_size) * self.grid_size
        
        # Draw minor grid lines (vertical)
        x = left
        while x <= right:
            painter.drawLine(QPointF(x, view_rect.top() - margin), 
                           QPointF(x, view_rect.bottom() + margin))
            x += self.grid_size
            
        # Draw minor grid lines (horizontal)
        y = top
        while y <= bottom:
            painter.drawLine(QPointF(view_rect.left() - margin, y),
                           QPointF(view_rect.right() + margin, y))
            y += self.grid_size
            
        # Draw major grid lines (10% darker)
        major_pen = QPen(QColor("#424241"))  # Slightly darker gray
        major_pen.setWidth(1)
        painter.setPen(major_pen)
        
        major_grid_size = self.grid_size * self.grid_squares
        
        # Draw major grid lines (vertical)
        x = int(left / major_grid_size) * major_grid_size
        while x <= right:
            if x % major_grid_size == 0:
                painter.drawLine(QPointF(x, view_rect.top() - margin),
                               QPointF(x, view_rect.bottom() + margin))
            x += major_grid_size
            
        # Draw major grid lines (horizontal)
        y = int(top / major_grid_size) * major_grid_size
        while y <= bottom:
            if y % major_grid_size == 0:
                painter.drawLine(QPointF(view_rect.left() - margin, y),
                               QPointF(view_rect.right() + margin, y))
            y += major_grid_size
    
    def wheelEvent(self, event):
        """Handle zooming with mouse wheel"""
        # Check if Ctrl key is pressed for zooming
        if event.modifiers() & Qt.ControlModifier:
            # Calculate zoom factor
            if event.angleDelta().y() > 0:  # Zoom in
                zoom_factor = self.zoom_in_factor
                new_zoom = self.zoom_level + self.zoom_step
            else:  # Zoom out
                zoom_factor = self.zoom_out_factor
                new_zoom = self.zoom_level - self.zoom_step
            
            # Check if zoom is within limits
            if self.zoom_range[0] <= new_zoom <= self.zoom_range[1]:
                self.zoom_level = new_zoom
                self.scale(zoom_factor, zoom_factor)
            
            # Accept the event to prevent scrolling
            event.accept()
        else:
            # Default wheel behavior for scrolling
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        """Handle key press events"""
        # No keyboard deletion - use toolbar button instead
        super().keyPressEvent(event)
    
    def contextMenuEvent(self, event):
        """Handle context menu events"""
        item = self.itemAt(event.pos())
        # If an edge, edge title, or its control points are under the cursor, delegate to the item's context menu
        if isinstance(item, (Edge, EdgeControlPoint, WaypointControlPoint, EdgeTitleItem)):
            return super().contextMenuEvent(event)
        
        menu = QMenu(self)
        
        if isinstance(item, Node):
            # Add node-specific actions
            add_child_action = menu.addAction("Add Child Node")
            add_child_action.triggered.connect(lambda: self.add_child_node(item, event.pos()))
            
            if item.parent_node:
                remove_from_parent = menu.addAction("Remove from Parent")
                remove_from_parent.triggered.connect(lambda: self.remove_node_from_parent(item))
            
            menu.addSeparator()
        
        # Add general actions
        add_node_action = menu.addAction("Add Node")
        add_node_action.triggered.connect(lambda: self.add_node_at_pos(event.pos()))
        
        menu.exec_(event.globalPos())
    
    def add_child_node(self, parent_node, pos):
        """Add a child node to the specified parent node"""
        if not parent_node.is_container:
            parent_node.setup_container()
        
        # Convert position to parent node's coordinate system
        scene_pos = self.mapToScene(pos)
        local_pos = parent_node.mapFromScene(scene_pos)
        
        # Create the child node without setting position yet (will be set by add_child_node)
        child = Node("Child Node", None, parent_node)
        
        # Set the action monitor reference (inherit from parent or get from main window)
        main_window = None
        if hasattr(self.parent(), 'action_monitor'):
            child.action_monitor = self.parent().action_monitor
            main_window = self.parent()
        elif parent_node.action_monitor:
            child.action_monitor = parent_node.action_monitor
            # Get main window
            if hasattr(self, 'window'):
                main_window = self.window()
            
        # Add child node at the clicked position
        parent_node.add_child_node(child, local_pos)
        
        # Record child node creation for undo
        if main_window and hasattr(main_window, 'record_node_creation'):
            main_window.record_node_creation(child, parent_node)
        
        # Make sure the parent node is large enough
        parent_node.update()
    
    def remove_node_from_parent(self, node):
        """Remove a node from its parent and add it to the main scene"""
        if node.parent_node:
            # Get the parent's scene position before removing
            parent_scene_pos = node.parent_node.scenePos()
            
            # Remove from parent
            node.parent_node.remove_child_node(node)
            
            # Add to main scene if not already there
            if node.scene() != self.scene:
                self.scene.addItem(node)
            
            # Position the node near the parent
            node.setPos(parent_scene_pos + QPointF(50, 50))
    
    def add_node_at_pos(self, pos):
        """Add a new node at the specified position"""
        scene_pos = self.mapToScene(pos)
        node = Node("New Node", scene_pos)
        
        # Set the action monitor reference from main window
        if hasattr(self.parent(), 'action_monitor'):
            node.action_monitor = self.parent().action_monitor
            
        self.scene.addItem(node)
    
    def delete_node(self, node):
        """Delete the specified node"""
        # Remove from parent if it has one
        if node.parent_node:
            node.parent_node.remove_child_node(node)
        
        # Remove from scene
        self.scene.removeItem(node)
        
        # Remove from window's nodes list
        window = self.window()
        if hasattr(window, 'nodes') and node in window.nodes:
            window.nodes.remove(node)
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        # No keyboard deletion - use toolbar button instead
        super().keyPressEvent(event)
                
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.RightButton:
            super().mousePressEvent(event)
            return
            
        # Get the item under the mouse
        item = self.itemAt(event.pos())
        
        # Handle node resizing first (highest priority)
        if isinstance(item, Node) and hasattr(item, 'is_over_resize_handle') and \
           item.is_over_resize_handle(item.mapFromScene(self.mapToScene(event.pos()))):
            # Let the node handle the resize operation
            super().mousePressEvent(event)
            return
        
        # Handle edge creation (only when Ctrl/Cmd is pressed)
        if event.button() == Qt.LeftButton and isinstance(item, Node) and \
           (event.modifiers() & Qt.ControlModifier):
            # Start edge creation
            self.edge_start_node = item
            self.temp_edge = Edge(item.scenePos())
            self.temp_edge.set_start_node(item)
            self.scene.addItem(self.temp_edge)
            return
            
        # Handle node selection and movement
        if event.button() == Qt.LeftButton:
            # If clicking on a control point (orange/blue dot), let it handle dragging/selection
            if isinstance(item, (EdgeControlPoint, WaypointControlPoint)):
                super().mousePressEvent(event)
                return
            # If clicking on an edge title, let it handle editing/selection
            if isinstance(item, EdgeTitleItem):
                super().mousePressEvent(event)
                return

            # If there's an edge under the cursor (even if covered by a node), prefer selecting it
            items_at_pos = self.items(event.pos())
            edge_under_cursor = None
            for it in items_at_pos:
                # Skip control points so they remain interactive
                if isinstance(it, (EdgeControlPoint, WaypointControlPoint)):
                    # Since control points are topmost and interactive, don't hijack this click
                    edge_under_cursor = None
                    break
                # If the title is under the cursor, don't hijack; let text item receive the event
                if isinstance(it, EdgeTitleItem):
                    super().mousePressEvent(event)
                    return
                if isinstance(it, Edge):
                    edge_under_cursor = it
                    break
            if edge_under_cursor is not None:
                # Handle edge selection with shift for multi-select
                if event.modifiers() & Qt.ShiftModifier:
                    edge_under_cursor.setSelected(not edge_under_cursor.isSelected())
                else:
                    for selected_item in self.scene.selectedItems():
                        if selected_item != edge_under_cursor:
                            selected_item.setSelected(False)
                    edge_under_cursor.setSelected(True)
                # Do not pass the event further so the node below doesn't grab it
                return
            
            if isinstance(item, Node):
                # If shift is pressed, toggle selection
                if event.modifiers() & Qt.ShiftModifier:
                    item.setSelected(not item.isSelected())
                # If not selected, select only this item
                elif not item.isSelected():
                    # Deselect all other items
                    for selected_item in self.scene.selectedItems():
                        if selected_item != item:
                            selected_item.setSelected(False)
                    item.setSelected(True)
                
                # Bring node to front
                item.setZValue(1000)
                
                # Start moving the item
                super().mousePressEvent(event)
                return
            else:
                # Clicked on empty space - clear selection if shift not held
                if not (event.modifiers() & Qt.ShiftModifier):
                    for selected_item in self.scene.selectedItems():
                        selected_item.setSelected(False)
                
                # Let the view handle rubber band selection
                super().mousePressEvent(event)
                return
        
        # Default behavior for other cases
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events"""
        if self.temp_edge is not None:
            # Update the temporary edge position
            scene_pos = self.mapToScene(event.pos())
            self.temp_edge.set_end_pos(scene_pos)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if event.button() == Qt.LeftButton and self.temp_edge is not None:
            # Check if we released on a node
            item = self.itemAt(event.pos())
            if isinstance(item, Node) and item != self.edge_start_node:
                # Connect the edge to the target node
                self.temp_edge.set_end_node(item)
                # Create control points for the edge
                self.temp_edge.create_control_points(self.scene)
                # Keep the edge in the scene
                if not hasattr(self.scene, 'edges'):
                    self.scene.edges = []
                self.scene.edges.append(self.temp_edge)
                
                # Record edge creation for undo
                main_window = None
                if hasattr(self, 'window'):
                    main_window = self.window()
                
                if main_window and hasattr(main_window, 'record_edge_creation'):
                    main_window.record_edge_creation(self.temp_edge)
            else:
                # Remove the temporary edge if not connected to a node
                self.scene.removeItem(self.temp_edge)
            
            self.temp_edge = None
            self.edge_start_node = None
        
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Ensure edge titles receive double-clicks to enter edit mode"""
        item = self.itemAt(event.pos())
        if isinstance(item, EdgeTitleItem):
            return super().mouseDoubleClickEvent(event)
        return super().mouseDoubleClickEvent(event)


class Node(QGraphicsItem):
    def __init__(self, title="Node", pos=None, parent=None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)
        self.setAcceptHoverEvents(True)  # Enable hover events
        
        # Node properties
        self.title = title
        self.min_width = 200  # Increased minimum width for better nesting
        self.min_height = 100  # Increased minimum height for better nesting
        self.width = 200
        self.height = self.min_height  # Initialize height
        self.title_height = 30
        self.padding = 10
        self.edge_roundness = 5.0
        self.resize_handle_size = 10
        self.resize_handle = QRectF()
        
        # User action monitoring
        self.action_monitor = None  # Will be set by the main window
        self.is_being_moved = False
        self.position_before_move = None  # Track position before movement for undo
        self._checking_parent = False  # Flag to prevent recursive parent checks
        
        # Node state
        self.child_nodes = []
        self.parent_node = None
        self.is_container = False
        self.inner_scene = None
        self.inner_view = None
        self.proxy = None
        self.inner_rect = QRectF()  # Initialize empty rect
        
        # Connected edges
        self.connected_edges = []
        
        # Node type property (None, "type1", or "type2")
        self.node_type = None
        
        # Initial state property (only for State nodes)
        self.is_initial = False
        
        # Set position if provided
        if pos is not None:
            # Clear position tracking to avoid recording initial position as a "move"
            self.position_before_move = None
            self.is_being_moved = False
            self.setPos(pos)
            print(f"[DEBUG] Node created: '{self.title}' at position ({pos.x():.2f}, {pos.y():.2f})")
        else:
            print(f"[DEBUG] Node created: '{self.title}' at default position (0.00, 0.00)")
            
        # Node colors (default blue)
        self.title_color = QColor("#3498db")  # Light blue color for title bar
        self.bg_color = QColor("#2c3e50")
        self.border_color = QColor("#747574")  # Default neutral border color
        self.border_width = 3  # Border width set to 3 pixels
        self.text_color = QColor("#ecf0f1")
        
        # Node title
        self.title_item = QGraphicsTextItem(self.title, self)
        self.title_item.setDefaultTextColor(self.text_color)
        self.title_item.setPos(self.padding, (self.title_height - self.title_item.boundingRect().height()) / 2)
        
        # Set the initial size and update the inner rect
        self.update_size()
    
    def set_node_type(self, node_type):
        """Set the node type and update title color and text accordingly"""
        self.node_type = node_type
        
        if node_type == "StateMachine":
            # Green title background for StateMachine
            self.title_color = QColor("#27ae60")  # Green
            # Update title
            self.title = "StateMachine"
            self.title_item.setPlainText("StateMachine")
        elif node_type == "State":
            # State title background is 40% darker than the StateMachine's title color
            base_sm = QColor("#27ae60")
            self.title_color = QColor(base_sm).darker(166)
            # Update title
            self.title = "State"
            self.title_item.setPlainText("State")
        else:
            # Default blue title background
            self.title_color = QColor("#3498db")  # Blue
        
        # Keep border consistent neutral for all types
        self.border_color = QColor("#747574")
        
        # Force redraw
        self.update()
    
    def set_initial_state(self, is_initial):
        """Mark this node as an initial state (only for State nodes)"""
        if self.node_type == "State":
            self.is_initial = is_initial
            # Force redraw to show/hide the indicator
            self.update()
            return True
        return False
    
    def setup_container(self):
        """Set up this node as a container for child nodes"""
        self.is_container = True
        self.inner_scene = QGraphicsScene()
        self.inner_scene.setBackgroundBrush(QColor(40, 40, 40, 30))  # Semi-transparent background
        
        # Create a child node area (slightly inset from the node's border)
        self.update_inner_rect()
    
    def update_inner_rect(self):
        """Update the inner rectangle for child nodes"""
        self.inner_rect = QRectF(
            self.padding,
            self.title_height + self.padding,
            max(0, self.width - 2 * self.padding),
            max(0, self.height - self.title_height - 2 * self.padding)
        )
        
        # Update child nodes if any
        for child in self.child_nodes:
            # Make sure children stay within bounds
            child_pos = child.pos()
            max_x = self.inner_rect.width() - child.boundingRect().width()
            max_y = self.inner_rect.height() - child.boundingRect().height()
            
            new_x = max(0, min(child_pos.x(), max_x))
            new_y = max(0, min(child_pos.y(), max_y))
            
            if new_x != child_pos.x() or new_y != child_pos.y():
                child.setPos(new_x, new_y)
    
    def add_child_node(self, node, pos=None):
        """Add a child node to this container node"""
        if not self.is_container:
            self.setup_container()
        
        # Make sure we have a valid inner_rect
        if not hasattr(self, 'inner_rect') or self.inner_rect.isNull():
            self.update_inner_rect()
        
        # Set this node as the parent
        node.setParentItem(self)
        node.parent_node = self
        
        # Keep the original title without adding parent prefix
        node.title_item.setPlainText(node.title)
        
        # Set position if provided, otherwise position below existing children
        if pos is not None:
            node.setPos(pos)
        else:
            # Position below existing children or at the top if no children
            if self.child_nodes:
                last_child = max(self.child_nodes, key=lambda c: c.y() + c.boundingRect().height())
                y_pos = last_child.y() + last_child.boundingRect().height() + 10
            else:
                y_pos = self.title_height + self.padding + 10
            
            x_pos = self.padding + 10  # Indent from left
            node.setPos(x_pos, y_pos)
        
        self.child_nodes.append(node)
        # Don't update size automatically - only resize when manually resized
        self.update()
    
    def remove_child_node(self, node):
        """Remove a child node from this container"""
        if node in self.child_nodes:
            self.child_nodes.remove(node)
            node.setParentItem(None)
            node.parent_node = None
    
    def paint(self, painter, option, widget=None):
        # Draw the main body (transparent)
        path = self._get_path()
        
        # Draw the title bar background (semi-transparent)
        title_rect = QRectF(0, 0, self.rect.width(), self.title_height)
        title_path = self._get_path(title_rect, round_bottom=False)
        
        # Semi-transparent title background
        title_bg_color = QColor(self.title_color)
        title_bg_color.setAlpha(180)  # Semi-transparent
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(title_bg_color))
        painter.drawPath(title_path.simplified())
        
        # Draw the border
        if self.isSelected():
            # Highlight border when selected (thicker yellow border)
            border_color = QColor("#f1c40f")  # Yellow for selection
            painter.setPen(QPen(border_color, self.border_width + 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            
            # Draw resize handle when selected
            painter.setBrush(QBrush(Qt.white))
            painter.drawRect(self.resize_handle)
        else:
            # Normal border with light blue color and specified width
            painter.setPen(QPen(self.border_color, self.border_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        
        # Draw the border path with the current pen
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        
        # Draw a subtle background for the container area
        if self.is_container and len(self.child_nodes) > 0:
            container_bg = QColor(255, 255, 255, 10)  # Very subtle white
            painter.setBrush(container_bg)
            painter.setPen(Qt.NoPen)
            container_rect = QRectF(
                self.padding,
                self.title_height + self.padding,
                max(0, self.width - 2 * self.padding),
                max(0, self.height - self.title_height - 2 * self.padding)
            )
            painter.drawRoundedRect(container_rect, self.edge_roundness, self.edge_roundness)
        
        # Draw initial state indicator (white circle at top-right corner) for State nodes marked as initial
        if self.is_initial and self.node_type == "State":
            circle_radius = 7.5  # 15 pixel diameter = 7.5 pixel radius
            margin = self.title_height / 2  # Half of title bar height
            circle_x = self.rect.width() - margin  # Equal distance from right edge
            circle_y = margin  # Equal distance from top edge
            
            painter.setBrush(QBrush(Qt.white))
            painter.setPen(QPen(QColor("#2c3e50"), 1))  # Thin dark border for contrast
            painter.drawEllipse(QPointF(circle_x, circle_y), circle_radius, circle_radius)
    
    def update_size(self):
        """Update the node size based on content"""
        # Store old size for comparison
        old_width = self.width
        old_height = self.height
        
        # Adjust width to fit content if needed
        text_width = self.title_item.boundingRect().width()
        min_content_width = text_width + 2 * self.padding
        
        # Calculate required width based on children if any
        if self.child_nodes:
            max_child_right = 0
            max_child_bottom = 0
            for child in self.child_nodes:
                child_rect = child.boundingRect()
                child_right = child.x() + child_rect.width()
                child_bottom = child.y() + child_rect.height()
                max_child_right = max(max_child_right, child_right)
                max_child_bottom = max(max_child_bottom, child_bottom)
            
            # Add padding to content width
            min_content_width = max(min_content_width, max_child_right + self.padding + 10)
            
            # Calculate height based on children
            self.height = max(self.min_height, max_child_bottom + self.padding + 10)
        else:
            # Default height if no children
            self.height = max(self.title_height * 2, self.min_height)
        
        # Update width (don't shrink below minimum or current content width)
        self.width = max(self.min_width, min_content_width, old_width)
        
        # Set the bounding rectangle
        self.rect = QRectF(0, 0, self.width, self.height)
        
        # Update inner rect if this is a container
        if self.is_container:
            self.update_inner_rect()
        
        # Update resize handle position
        self.update_handles()
        
        # Update the node if size changed
        if old_width != self.width or old_height != self.height:
            self.update()
            
            # Update parent node's size if this node has a parent
            if self.parent_node and isinstance(self.parent_node, Node):
                self.parent_node.update_size()
    
    def update_handles(self):
        """Update the position of the resize handle"""
        h = self.resize_handle_size
        r = self.rect
        self.resize_handle = QRectF(r.right() - h, r.bottom() - h, h, h)
    
    def update_descendant_edges(self):
        """Recursively update edges for this node and all its descendants"""
        # Update this node's edges
        for edge in self.connected_edges:
            edge.update_path()
        
        # Recursively update child nodes' edges
        if self.is_container and self.child_nodes:
            for child in self.child_nodes:
                child.update_descendant_edges()
    
    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
    
    def boundingRect(self):
        """Return the bounding rectangle of the node"""
        # Add padding for the border width and some extra for selection
        padding = max(2, self.border_width / 2 + 2)
        return self.rect.adjusted(-padding, -padding, padding, padding)
    
    def _get_path(self, rect=None, round_bottom=True):
        """Create a rounded rectangle path for the node"""
        if rect is None:
            rect = self.rect
            
        path = QPainterPath()
        radius = self.edge_roundness
        
        # Create a rounded rectangle path that matches the border width
        if round_bottom:
            # Full rounded rectangle (all corners rounded)
            path.addRoundedRect(rect, radius, radius)
        else:
            # Only top corners rounded
            path.moveTo(rect.left() + radius, rect.top())
            # Top edge
            path.lineTo(rect.right() - radius, rect.top())
            path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + radius)
            # Right edge
            path.lineTo(rect.right(), rect.bottom())
            # Bottom edge
            path.lineTo(rect.left(), rect.bottom())
            # Left edge
            path.lineTo(rect.left(), rect.top() + radius)
            path.quadTo(rect.left(), rect.top(), rect.left() + radius, rect.top())
            
        return path
    
    def is_over_resize_handle(self, pos):
        """Check if position is over the resize handle"""
        return hasattr(self, 'resize_handle') and self.resize_handle.contains(pos)
        
    def hoverMoveEvent(self, event):
        """Handle hover events for the resize handle"""
        if self.isSelected() and self.is_over_resize_handle(event.pos()):
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Handle hover leave event"""
        super().hoverLeaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press events for resizing and dot marking"""
        try:
            if event.button() == Qt.LeftButton:
                # Capture position before any movement for undo functionality (do this for all left clicks)
                if not self.is_over_resize_handle(event.pos()):
                    self.position_before_move = self.pos()
            
            if event.button() == Qt.LeftButton and self.isSelected():
                if self.is_over_resize_handle(event.pos()):
                    self.is_resizing = True
                    self.old_rect = self.rect
                    self.old_pos = event.pos()
                    # Capture rect before resizing for undo functionality
                    self.rect_before_resize = QRectF(self.rect)
                    event.accept()
                    return
                
                # Check if we clicked on the hover dot
                if hasattr(self, 'hover_dot') and self.hover_dot and self.hover_dot.isVisible():
                    # Get the hover dot's position and size
                    dot_rect = self.hover_dot.rect()
                    dot_center = self.hover_dot.pos()
                    dot_radius = dot_rect.width() / 2
                    
                    # Get mouse position in scene coordinates
                    mouse_pos = self.mapToScene(event.pos())
                    
                    # Calculate distance from mouse to dot center
                    dx = mouse_pos.x() - dot_center.x()
                    dy = mouse_pos.y() - dot_center.y()
                    distance_squared = dx*dx + dy*dy
                    
                    # Only proceed if click was within the dot's radius
                    if distance_squared <= (dot_radius * dot_radius):
                        try:
                            # Get the relative position from the hover dot
                            rel_pos = self.hover_dot.data(0)
                            if rel_pos:
                                # Create a new dot that will stay relative to the node
                                marked_dot = {
                                    'item': QGraphicsEllipseItem(-8, -8, 16, 16),
                                    'rel_pos': rel_pos  # Store relative position
                                }
                                
                                # Style the dot
                                marked_dot['item'].setBrush(QBrush(Qt.green))
                                marked_dot['item'].setPen(QPen(Qt.white, 1.5))
                                marked_dot['item'].setZValue(1000)
                                
                                # Position the dot on the border
                                self._update_marked_dot_position(marked_dot)
                                
                                # Add to scene
                                if self.scene():
                                    self.scene().addItem(marked_dot['item'])
                                
                                # Store the marked dot so it persists
                                if not hasattr(self, 'marked_dots'):
                                    self.marked_dots = []
                                self.marked_dots.append(marked_dot)
                                
                                # Update dot positions when node moves or resizes
                                if not hasattr(self, '_dot_update_connected'):
                                    self.scene().changed.connect(self._update_marked_dots_position)
                                    self._dot_update_connected = True
                                
                                event.accept()
                                return
                            
                        except Exception as e:
                            print(f"Error creating marked dot: {e}")
            
            super().mousePressEvent(event)
            
        except Exception as e:
            print(f"Error in mousePressEvent: {e}")
            super().mousePressEvent(event)
            
    def _update_marked_dots_position(self):
        """Update positions of all marked dots when the node moves or resizes"""
        if hasattr(self, 'marked_dots'):
            for dot in self.marked_dots:
                self._update_marked_dot_position(dot)
    
    def _update_marked_dot_position(self, dot):
        """Update the position of a single marked dot based on node's current bounds"""
        try:
            if dot and 'item' in dot and 'rel_pos' in dot:
                rel_x, rel_y = dot['rel_pos']
                rect = self.boundingRect()
                
                # Calculate absolute position based on relative position and current bounds
                x = rect.left() + rel_x * rect.width()
                y = rect.top() + rel_y * rect.height()
                
                # Convert to scene coordinates and update position
                scene_pos = self.mapToScene(QPointF(x, y))
                dot['item'].setPos(scene_pos)
        except Exception as e:
            print(f"Error updating marked dot position: {e}")
            
    def mouseDoubleClickEvent(self, event):
        """Handle double click events to edit node title"""
        # Check if the click was on the title area
        title_rect = QRectF(0, 0, self.width, self.title_height)
        if title_rect.contains(event.pos()):
            self.edit_title()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)
            
    def edit_title(self):
        """Enable editing of the node's title using a dialog"""
        from PyQt5.QtWidgets import QInputDialog
        
        # Get the parent widget for the dialog
        parent = None
        if self.scene() and self.scene().views():
            parent = self.scene().views()[0]
            
        # Show input dialog
        new_title, ok = QInputDialog.getText(
            parent, 
            'Edit Node Title', 
            'Enter new title:', 
            text=self.title
        )
        
        # Update the title if user clicked OK and entered text
        if ok and new_title.strip() and new_title != self.title:
            old_title = self.title
            self.title = new_title.strip()
            self.title_item.setPlainText(self.title)
            self.update()
            
            # Record the title change for undo
            if self.scene() and self.scene().views():
                view = self.scene().views()[0]
                if hasattr(view, 'window') and hasattr(view.window(), 'record_node_title_change'):
                    view.window().record_node_title_change(self, old_title, self.title)
        
    def mouseMoveEvent(self, event):
        """Handle mouse move events for resizing"""
        if hasattr(self, 'is_resizing') and self.is_resizing:
            # Calculate the position difference
            delta = event.pos() - self.old_pos
            new_rect = QRectF(self.old_rect)
            
            # Only allow resizing from bottom-right
            new_rect.setRight(self.old_rect.right() + delta.x())
            new_rect.setBottom(self.old_rect.bottom() + delta.y())
            
            # Enforce minimum size
            if new_rect.width() < self.min_width:
                new_rect.setRight(new_rect.left() + self.min_width)
            if new_rect.height() < self.min_height:
                new_rect.setBottom(new_rect.top() + self.min_height)
            
            # Update the node size
            self.prepareGeometryChange()
            self.rect = new_rect
            self.update_handles()
            self.update()
            
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events for resizing and movement"""
        if hasattr(self, 'is_resizing') and self.is_resizing:
            self.is_resizing = False
            
            # Record resize for undo if the rect actually changed
            if hasattr(self, 'rect_before_resize') and self.rect_before_resize != self.rect:
                print(f"[DEBUG] Node resized: '{self.title}' from size ({self.rect_before_resize.width():.2f}, {self.rect_before_resize.height():.2f}) to ({self.rect.width():.2f}, {self.rect.height():.2f}) at position ({self.pos().x():.2f}, {self.pos().y():.2f})")
                
                # Get the main window to record the undo action
                if self.scene() and hasattr(self.scene(), 'views') and self.scene().views():
                    view = self.scene().views()[0]
                    main_window = None
                    if hasattr(view, 'window'):
                        main_window = view.window()
                    
                    if main_window and hasattr(main_window, 'record_node_resize'):
                        main_window.record_node_resize(self, self.rect_before_resize, self.rect)
                
                self.rect_before_resize = None
            
            # After resizing, update Z-order of all nodes in the scene
            self.update_z_order()
        
        # Record movement for undo if position changed during drag
        position_actually_changed = False
        if self.position_before_move is not None and self.position_before_move != self.pos():
            position_actually_changed = True
            print(f"[DEBUG] Node moved: '{self.title}' from position ({self.position_before_move.x():.2f}, {self.position_before_move.y():.2f}) to ({self.pos().x():.2f}, {self.pos().y():.2f})")
            
            # Get the main window to record the undo action
            if self.scene() and hasattr(self.scene(), 'views') and self.scene().views():
                view = self.scene().views()[0]
                main_window = None
                if hasattr(view, 'window'):
                    main_window = view.window()
                
                if main_window and hasattr(main_window, 'record_node_movement'):
                    main_window.record_node_movement(self, self.position_before_move, self.pos())
            
            # Signal that node movement is complete
            if self.action_monitor:
                self.action_monitor.signal_action('node_moved')
            
            self.position_before_move = None
        
        # Reset the moving flag and check for parent relationship after drag is complete
        if self.is_being_moved:
            self.is_being_moved = False
            # Only check parent if position actually changed (i.e., it was a drag, not just a click)
            if position_actually_changed:
                # Now check if this node should be reparented after the drag is complete
                self._check_and_update_parent()
        
        super().mouseReleaseEvent(event)
        
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # Mark that the node is being moved
            self.is_being_moved = True
            # Update Z-order when position changes
            self.update_z_order()
            
        elif change == QGraphicsItem.ItemPositionHasChanged and self.scene():
            # Update edges for this node and all descendants recursively
            self.update_descendant_edges()
            
            # Don't check parent during drag to avoid flickering
            # Parent check will happen in mouseReleaseEvent after drag is complete
            
            # Only record movement when drag is complete (is_being_moved becomes False)
            # Don't record during the drag itself, as this fires many times
            # The actual recording will happen in mouseReleaseEvent
            
        elif change == QGraphicsItem.ItemSelectedHasChanged and self.scene():
            # When selection changes, ensure selected items are on top
            if value:  # If selected
                self.setZValue(1000)  # Very high z-value for selected items
            else:
                self.update_z_order()  # Return to size-based z-order
                
        elif change == QGraphicsItem.ItemSceneHasChanged and value:
            # When added to a scene, set initial z-order
            self.update_z_order()
            
        return super().itemChange(change, value)
        
    def update_z_order(self):
        """Update the Z-order of this node based on its size"""
        if not self.scene() or not hasattr(self, 'rect'):
            return
            
        # Don't update z-order if we're currently resizing
        if hasattr(self, 'is_resizing') and self.is_resizing:
            return
            
        # Calculate area of this node
        area = self.rect.width() * self.rect.height()
        
        # Find all other nodes that intersect with this one
        scene_rect = self.mapRectToScene(self.rect)
        colliding_items = self.scene().items(scene_rect, mode=Qt.IntersectsItemBoundingRect)
        
        # Filter to only get other nodes
        other_nodes = [item for item in colliding_items 
                      if isinstance(item, Node) and item != self]
        
        if not other_nodes:
            # No other nodes to compare with, use default z-value
            self.setZValue(0)
            return
            
        # Find the maximum z-value among nodes we overlap with that are smaller than us
        max_z = -1
        for node in other_nodes:
            if not hasattr(node, 'rect'):
                continue
                
            node_area = node.rect.width() * node.rect.height()
            if node_area < area:  # If the other node is smaller
                max_z = max(max_z, node.zValue())
        
        # Set our z-value to be higher than the highest z-value of smaller nodes we overlap with
        # But only if we're not already above them
        if max_z >= 0 and self.zValue() <= max_z:
            self.setZValue(max_z + 1)
    
    def _check_and_update_parent(self):
        """Check if this node is completely inside another node and update parent relationship"""
        if not self.scene():
            return
        
        # Prevent recursive calls
        if self._checking_parent:
            return
        
        # Don't check during resizing
        if hasattr(self, 'is_resizing') and self.is_resizing:
            return
        
        # Set flag to prevent recursion
        self._checking_parent = True
        
        try:
            # Get this node's bounding rect in scene coordinates
            my_scene_rect = self.sceneBoundingRect()
            
            # Find all nodes in the scene (excluding self and any descendants)
            all_nodes = [item for item in self.scene().items() if isinstance(item, Node) and item != self]
            
            # Find potential parent nodes (nodes that could contain this node)
            potential_parents = []
            for node in all_nodes:
                # Skip if this node is already a parent/ancestor of the candidate
                # (i.e., if the candidate is trying to become a parent of its own ancestor)
                if self._is_ancestor_of(node):
                    continue
                
                # Skip if the candidate is a child/descendant of this node
                # BUT don't skip if it's the direct parent - we want to keep it as a candidate
                # to verify it should still be the parent
                if node._is_ancestor_of(self) and node != self.parent_node:
                    continue
                
                # Get the candidate's bounding rect in scene coordinates
                node_scene_rect = node.sceneBoundingRect()
                
                # Check if this node is completely inside the candidate node's boundary
                # We need to check if all corners of my_scene_rect are inside node_scene_rect
                if node_scene_rect.contains(my_scene_rect):
                    potential_parents.append(node)
            
            # If we found potential parents, choose the smallest one (most specific container)
            if potential_parents:
                # Sort by area (smallest first)
                potential_parents.sort(key=lambda n: n.rect.width() * n.rect.height())
                new_parent = potential_parents[0]
                
                # Only update if the parent is different
                if new_parent != self.parent_node:
                    self._reparent_to(new_parent)
            else:
                # If not inside any node and has a parent, remove from parent
                if self.parent_node is not None:
                    self._remove_from_parent()
        finally:
            # Always reset the flag
            self._checking_parent = False
    
    def _is_ancestor_of(self, node):
        """Check if this node is an ancestor of the given node"""
        current = node.parent_node
        while current is not None:
            if current == self:
                return True
            current = current.parent_node
        return False
    
    def _reparent_to(self, new_parent):
        """Change the parent of this node to the specified parent"""
        # Save the current scene position and parent before any changes
        scene_pos = self.scenePos()
        old_parent = self.parent_node
        old_pos = QPointF(self.pos()) if old_parent else None
        
        # Remove from current parent if any
        if self.parent_node is not None:
            self.parent_node.remove_child_node(self)
        
        # Set up the new parent as a container if needed
        if not new_parent.is_container:
            new_parent.setup_container()
        
        # Temporarily disable position tracking to avoid triggering itemChange
        old_flags = self.flags()
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
        
        # Add to new parent (this will call setParentItem)
        # Pass None for pos so add_child_node doesn't set position yet
        new_parent.add_child_node(self, None)
        
        # Now convert scene position to new parent's local coordinates and set it
        local_pos = new_parent.mapFromScene(scene_pos)
        self.setPos(local_pos)
        
        # Re-enable position tracking
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        
        # Record the reparenting for undo
        if self.scene() and hasattr(self.scene(), 'views') and self.scene().views():
            view = self.scene().views()[0]
            main_window = None
            if hasattr(view, 'window'):
                main_window = view.window()
            
            if main_window and hasattr(main_window, 'record_node_reparent'):
                main_window.record_node_reparent(self, old_parent, new_parent, old_pos)
    
    def _remove_from_parent(self):
        """Remove this node from its parent and add to main scene"""
        if self.parent_node is None:
            return
        
        # Save state before removing from parent
        scene_pos = self.scenePos()
        old_parent = self.parent_node
        old_pos = QPointF(self.pos())
        
        # Store the scene reference
        scene = self.scene()
        
        # Remove from parent (this also calls setParentItem(None))
        self.parent_node.remove_child_node(self)
        
        # Add to main scene if needed
        if scene and self.scene() != scene:
            scene.addItem(self)
        
        # Restore scene position
        self.setPos(scene_pos)
        
        # Record the reparenting for undo (removing from parent = reparenting to None)
        if scene and hasattr(scene, 'views') and scene.views():
            view = scene.views()[0]
            main_window = None
            if hasattr(view, 'window'):
                main_window = view.window()
            
            if main_window and hasattr(main_window, 'record_node_reparent'):
                main_window.record_node_reparent(self, old_parent, None, old_pos)
            
    def get_border_intersection(self, point):
        """
        Find the intersection point between the node's border and a line 
        from the node's center to the given point.
        
        Args:
            point (QPointF): The point to which we're drawing the line from the center
            
        Returns:
            QPointF: The intersection point on the node's border
        """
        # Get the node's bounding rect in item coordinates
        rect = self.boundingRect()
        center = rect.center()
        
        # Ensure point is in item coordinates
        if hasattr(point, 'x') and hasattr(point, 'y'):
            if not isinstance(point, QPointF):
                point = QPointF(point)
            
        # If the point is the same as center, return the right edge point
        if point == center:
            return QPointF(rect.right(), center.y())
            
        # Calculate direction vector from center to point
        dx = point.x() - center.x()
        dy = point.y() - center.y()
        
        # Calculate intersection with each edge of the rectangle
        intersections = []
        
        # Right edge (x = rect.right())
        if abs(dx) > 1e-6:  # Avoid division by zero
            t = (rect.right() - center.x()) / dx
            y = center.y() + t * dy
            if rect.top() <= y <= rect.bottom():
                intersections.append((t, QPointF(rect.right(), y)))
        
        # Left edge (x = rect.left())
        if abs(dx) > 1e-6:  # Avoid division by zero
            t = (rect.left() - center.x()) / dx
            y = center.y() + t * dy
            if rect.top() <= y <= rect.bottom():
                intersections.append((t, QPointF(rect.left(), y)))
        
        # Bottom edge (y = rect.bottom())
        if abs(dy) > 1e-6:  # Avoid division by zero
            t = (rect.bottom() - center.y()) / dy
            x = center.x() + t * dx
            if rect.left() <= x <= rect.right():
                intersections.append((t, QPointF(x, rect.bottom())))
        
        # Top edge (y = rect.top())
        if abs(dy) > 1e-6:  # Avoid division by zero
            t = (rect.top() - center.y()) / dy
            x = center.x() + t * dx
            if rect.left() <= x <= rect.right():
                intersections.append((t, QPointF(x, rect.top())))
        
        # Find the intersection point with the smallest positive t value
        # This gives us the first intersection along the ray from center to point
        valid_intersections = [p for t, p in intersections if t > 0]
        if valid_intersections:
            # Return the closest intersection to the center
            return min(valid_intersections, 
                      key=lambda p: (p.x() - center.x())**2 + (p.y() - center.y())**2)
        
        # Fallback: return the right edge center if no valid intersection found
        return QPointF(rect.right(), center.y())


class NodeEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None  # Track the currently opened file
        self.initUI()

    def _relink_stored_edge_nodes(self, original_node_id, new_node):
        """Update pending edge actions to reference the recreated node."""
        stacks = [self.undo_stack]
        if hasattr(self, 'redo_stack'):
            stacks.append(self.redo_stack)

        for stack in stacks:
            if not stack:
                continue
            for action in stack:
                if not isinstance(action, dict):
                    continue
                if action.get('type') != 'edge_delete':
                    continue
                edge_data = action.get('edge_data')
                if not edge_data:
                    continue
                if edge_data.get('start_node_id') == original_node_id:
                    edge_data['start_node'] = new_node
                    edge_data['start_node_id'] = id(new_node)
                if edge_data.get('end_node_id') == original_node_id:
                    edge_data['end_node'] = new_node
                    edge_data['end_node_id'] = id(new_node)
    
    def initUI(self):
        # Set window properties
        self.setWindowTitle("The Modeller")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create toolbar
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        
        # Add file operation buttons at the left
        new_action = toolbar.addAction("New")
        new_action.setToolTip("New design (Ctrl+N)")
        new_action.setIcon(self.make_new_file_svg_icon(24))
        new_action.triggered.connect(self.new_design)
        new_action.setShortcut("Ctrl+N")
        
        save_action = toolbar.addAction("Save")
        save_action.setToolTip("Save design (Ctrl+S)")
        save_action.setIcon(self.make_save_svg_icon(24))
        save_action.triggered.connect(self.save_design)
        save_action.setShortcut("Ctrl+S")
        
        load_action = toolbar.addAction("Load")
        load_action.setToolTip("Load design (Ctrl+O)")
        load_action.setIcon(self.make_load_svg_icon(24))
        load_action.triggered.connect(self.load_design)
        load_action.setShortcut("Ctrl+O")
        
        toolbar.addSeparator()
        
        # Add an expanding spacer before actions to center the group
        left_spacer = QWidget()
        left_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(left_spacer)
        
        # Add node type buttons
        statemachine_action = toolbar.addAction("StateMachine")
        statemachine_action.setToolTip("Apply StateMachine type to selected node")
        statemachine_action.triggered.connect(lambda: self.apply_node_type("StateMachine"))
        
        state_action = toolbar.addAction("State")
        state_action.setToolTip("Apply State type to selected node")
        state_action.triggered.connect(lambda: self.apply_node_type("State"))

        # Set icons for StateMachine and State actions (SVG-based for crisp scaling) with labels
        sm_hex = "#27ae60"  # base StateMachine title color
        sm_qc = QColor(sm_hex)
        # 40% darker => factor ≈ 166 (since QColor.darker(200) => 50% darker)
        st_qc = QColor(sm_qc).darker(166)
        statemachine_action.setIcon(self.make_state_node_svg_icon(24, title_color=sm_hex, label="M"))
        state_action.setIcon(self.make_state_node_svg_icon(24, title_color=st_qc.name(), label="S"))
        
        toolbar.addSeparator()
        
        # Add Initial button to mark State nodes as initial
        initial_action = toolbar.addAction("Initial")
        initial_action.setToolTip("Mark selected State node as initial")
        initial_action.setIcon(self.make_initial_state_svg_icon(24))
        initial_action.triggered.connect(self.mark_as_initial)
        
        toolbar.addSeparator()
        
        # Undo/Redo actions with custom icons
        undo_action = toolbar.addAction("Undo")
        undo_action.setToolTip("Undo last action")
        undo_action.setIcon(self.make_undo_svg_icon(24))
        undo_action.triggered.connect(self.undo_action)
        undo_action.setShortcut("Ctrl+Z")

        redo_action = toolbar.addAction("Redo")
        redo_action.setToolTip("Redo last undone action")
        redo_action.setIcon(self.make_redo_svg_icon(24))
        redo_action.triggered.connect(self.redo_action)
        redo_action.setShortcut("Ctrl+Y")
        
        # Delete selected items action with custom red cross icon (SVG)
        delete_action = toolbar.addAction("Delete")
        delete_action.setToolTip("Delete selected items")
        delete_action.setIcon(self.make_red_cross_svg_icon(24))
        delete_action.triggered.connect(self.delete_selected_items)
        delete_action.setShortcut("Delete")  # Primary shortcut
        
        # Add Backspace as an alternative shortcut
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        backspace_shortcut = QShortcut(QKeySequence(Qt.Key_Backspace), self)
        backspace_shortcut.activated.connect(self.delete_selected_items)
        
        # Add an expanding spacer after actions to keep group centered
        right_spacer = QWidget()
        right_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(right_spacer)
        
        # Create a central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a graphics scene
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-1000, -1000, 2000, 2000)
        
        # Create the custom graphics view
        self.view = NodeEditorGraphicsView(self.scene, self)
        
        # Add the view to the layout
        layout.addWidget(self.view)
        
        # Set up context menu for adding nodes
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)
        
        # Keep track of nodes and edges
        self.nodes = []
        self.edges = []
        
        # Edge drawing state
        self.edge_start = None
        self.current_edge = None
        
        # Undo/redo stacks
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_stack_size = 50  # Limit stack size to prevent memory issues
        
        # Set up the status bar
        self.statusBar().showMessage("Ready")
        
        # Create the user action signal dot (15 pixels from right edge)
        self.action_signal_dot = UserActionSignalDot()
        
        # Add spacing widget to position dot 15 pixels from right edge
        spacer = QWidget()
        spacer.setFixedWidth(15)
        
        # Add the dot widget to the status bar (right side)
        self.statusBar().addPermanentWidget(self.action_signal_dot)
        self.statusBar().addPermanentWidget(spacer)
        
        # Initialize the user action monitor
        self.action_monitor = UserActionMonitor(self.action_signal_dot)
        
        # Create a simple menu
        self.createMenu()
        
        # Show the window
        self.show()
    
    def apply_node_type(self, node_type):
        """Apply a node type to all selected nodes"""
        selected_items = self.scene.selectedItems()
        
        # Filter to only Node items
        nodes = [item for item in selected_items if isinstance(item, Node)]
        
        if not nodes:
            self.statusBar().showMessage("No nodes selected")
            return
        
        # Apply the type to all selected nodes and record for undo
        for node in nodes:
            # Record the old type and title before changing
            old_type = node.node_type
            old_title = node.title  # Capture title before it gets changed
            node.set_node_type(node_type)
            # Record the type change for undo
            self.record_node_type_change(node, old_type, node_type, old_title)
        
        # Update status bar
        type_name = "StateMachine (Green)" if node_type == "StateMachine" else "State (Orange)"
        self.statusBar().showMessage(f"Applied {type_name} to {len(nodes)} node(s)")
    
    def mark_as_initial(self):
        """Mark selected State nodes as initial states"""
        selected_items = self.scene.selectedItems()
        
        # Filter to only Node items
        nodes = [item for item in selected_items if isinstance(item, Node)]
        
        if not nodes:
            self.statusBar().showMessage("No nodes selected")
            return
        
        # Count how many nodes were successfully marked
        marked_count = 0
        non_state_count = 0
        
        for node in nodes:
            # Toggle initial state for State nodes
            if node.node_type == "State":
                previous_state = node.is_initial
                new_state = not previous_state
                # Record before changing so undo can revert
                self.record_node_initial_change(node, previous_state, new_state)
                # Toggle the initial state
                node.set_initial_state(new_state)
                marked_count += 1
            else:
                non_state_count += 1
        
        # Update status bar with appropriate message
        if marked_count > 0 and non_state_count == 0:
            self.statusBar().showMessage(f"Toggled initial state for {marked_count} State node(s)")
        elif marked_count > 0 and non_state_count > 0:
            self.statusBar().showMessage(f"Toggled initial state for {marked_count} State node(s). {non_state_count} non-State node(s) ignored")
        else:
            self.statusBar().showMessage("No State nodes selected. Only State nodes can be marked as initial")
    
    def record_node_movement(self, node, old_pos, new_pos):
        """Record a node movement for undo functionality"""
        # Add to undo stack
        self.undo_stack.append({
            'type': 'node_move',
            'node': node,
            'old_pos': QPointF(old_pos),  # Make a copy
            'new_pos': QPointF(new_pos)   # Make a copy
        })
        
        # Limit stack size
        if len(self.undo_stack) > self.max_undo_stack_size:
            self.undo_stack.pop(0)  # Remove oldest entry
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
    
    def record_node_creation(self, node, parent):
        """Record a node creation for undo functionality"""
        self.undo_stack.append({
            'type': 'node_create',
            'node': node,
            'parent': parent,
            'position': QPointF(node.pos())
        })
        
        # Limit stack size
        if len(self.undo_stack) > self.max_undo_stack_size:
            self.undo_stack.pop(0)
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
    
    def record_node_deletion(self, node):
        """Record a node deletion for undo functionality"""
        # Capture node state before deletion
        self.undo_stack.append({
            'type': 'node_delete',
            'node_data': {
                'title': node.title,
                'position': QPointF(node.pos()),
                'node_type': node.node_type,
                'is_initial': node.is_initial,
                'rect': QRectF(node.rect) if hasattr(node, 'rect') else None,
                'parent': node.parent_node,
                'node_id': id(node)
            }
        })
        
        # Limit stack size
        if len(self.undo_stack) > self.max_undo_stack_size:
            self.undo_stack.pop(0)
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
    
    def record_node_type_change(self, node, old_type, new_type, old_title):
        """Record a node type change for undo functionality"""
        self.undo_stack.append({
            'type': 'node_type_change',
            'node': node,
            'old_type': old_type,
            'new_type': new_type,
            'old_title': old_title  # Capture the title before the type change
        })
        
        # Limit stack size
        if len(self.undo_stack) > self.max_undo_stack_size:
            self.undo_stack.pop(0)
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
    
    def record_node_resize(self, node, old_rect, new_rect):
        """Record a node resize for undo functionality"""
        self.undo_stack.append({
            'type': 'node_resize',
            'node': node,
            'old_rect': QRectF(old_rect),  # Make a copy
            'new_rect': QRectF(new_rect)   # Make a copy
        })
        
        # Limit stack size
        if len(self.undo_stack) > self.max_undo_stack_size:
            self.undo_stack.pop(0)
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
    
    def record_edge_creation(self, edge):
        """Record an edge creation for undo functionality"""
        self.undo_stack.append({
            'type': 'edge_create',
            'edge': edge,
            'start_node': edge._start_node,
            'end_node': edge._end_node
        })
        
        # Limit stack size
        if len(self.undo_stack) > self.max_undo_stack_size:
            self.undo_stack.pop(0)
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
    
    def record_edge_deletion(self, edge):
        """Record an edge deletion for undo functionality"""
        from edge import Edge
        self.undo_stack.append({
            'type': 'edge_delete',
            'edge_data': {
                'start_node': edge._start_node,
                'end_node': edge._end_node,
                'start_node_id': id(edge._start_node) if edge._start_node else None,
                'end_node_id': id(edge._end_node) if edge._end_node else None,
                'title': edge.title_item.toPlainText() if edge.title_item else "",
                'waypoint_ratio': edge.waypoint_ratio if edge.waypoint_ratio is not None else 0.5,
                'start_offset': edge.get_endpoint_offset(is_start=True),
                'end_offset': edge.get_endpoint_offset(is_start=False)
            }
        })
        
        # Limit stack size
        if len(self.undo_stack) > self.max_undo_stack_size:
            self.undo_stack.pop(0)
    
    def record_edge_connection_change(self, edge, is_start, old_offset, new_offset):
        """Record an edge connection point change for undo functionality"""
        self.undo_stack.append({
            'type': 'edge_connection_change',
            'edge': edge,
            'is_start': is_start,
            'old_offset': QPointF(old_offset),
            'new_offset': QPointF(new_offset)
        })
        
        # Limit stack size
        if len(self.undo_stack) > self.max_undo_stack_size:
            self.undo_stack.pop(0)
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
    
    def record_edge_waypoint_change(self, edge, old_ratio, new_ratio):
        """Record an edge waypoint adjustment for undo functionality"""
        self.undo_stack.append({
            'type': 'edge_waypoint_change',
            'edge': edge,
            'old_ratio': old_ratio,
            'new_ratio': new_ratio
        })
        
        # Limit stack size
        if len(self.undo_stack) > self.max_undo_stack_size:
            self.undo_stack.pop(0)
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
    
    def record_node_title_change(self, node, old_title, new_title):
        """Record a node title change for undo functionality"""
        self.undo_stack.append({
            'type': 'node_title_change',
            'node': node,
            'old_title': old_title,
            'new_title': new_title
        })
        
        # Limit stack size
        if len(self.undo_stack) > self.max_undo_stack_size:
            self.undo_stack.pop(0)
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
    
    def record_edge_title_change(self, edge, old_title, new_title):
        """Record an edge title change for undo functionality"""
        self.undo_stack.append({
            'type': 'edge_title_change',
            'edge': edge,
            'old_title': old_title,
            'new_title': new_title
        })
        
        # Limit stack size
        if len(self.undo_stack) > self.max_undo_stack_size:
            self.undo_stack.pop(0)
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()

    def record_node_initial_change(self, node, was_initial, is_initial):
        """Record toggling of a node's initial state."""
        self.undo_stack.append({
            'type': 'node_initial_change',
            'node': node,
            'was_initial': was_initial,
            'is_initial': is_initial
        })
        if len(self.undo_stack) > self.max_undo_stack_size:
            self.undo_stack.pop(0)
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
    
    def record_node_reparent(self, node, old_parent, new_parent, old_pos):
        """Record a node reparenting for undo functionality"""
        self.undo_stack.append({
            'type': 'node_reparent',
            'node': node,
            'old_parent': old_parent,
            'new_parent': new_parent,
            'old_pos': QPointF(old_pos) if old_pos else None,
            'new_pos': QPointF(node.pos())
        })
        
        # Limit stack size
        if len(self.undo_stack) > self.max_undo_stack_size:
            self.undo_stack.pop(0)
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
    
    def undo_action(self):
        """Undo the last action"""
        if not self.undo_stack:
            self.statusBar().showMessage("Nothing to undo", 2000)
            return
        
        # Validate the action before processing
        if not self.validate_undo_action(self.undo_stack[-1]):
            # Remove invalid action and try next one
            self.undo_stack.pop()
            self.statusBar().showMessage("Cannot undo: References deleted items", 2000)
            self.undo_action()
            return
        
        # Get the last action from the stack
        action = self.undo_stack.pop()
        action_type = action['type']
        
        if action_type == 'node_move':
            node = action['node']
            old_pos = action['old_pos']
            
            # Check if the node still exists in the scene
            if node.scene() == self.scene:
                # Temporarily disable position tracking to avoid recording this as a new move
                node.position_before_move = None
                node.is_being_moved = False
                
                new_pos = action['new_pos']
                print(f"[DEBUG] UNDO node move: '{node.title}' from position ({new_pos.x():.2f}, {new_pos.y():.2f}) back to ({old_pos.x():.2f}, {old_pos.y():.2f})")
                
                # Move the node back to its old position
                node.setPos(old_pos)
                
                # Update edges
                node.update_descendant_edges()
                
                self.statusBar().showMessage(f"Undone: Node moved back to previous position", 2000)
            else:
                self.statusBar().showMessage("Cannot undo: Node no longer exists", 2000)
                return
        
        elif action_type == 'node_create':
            # Undo node creation by deleting the node
            node = action['node']
            parent = action['parent']
            
            if node.scene() == self.scene:
                print(f"[DEBUG] UNDO node create: Deleting node '{node.title}' at position ({node.pos().x():.2f}, {node.pos().y():.2f})")
                
                # Remove from parent's child list if it has a parent
                if parent and node in parent.child_nodes:
                    parent.child_nodes.remove(node)
                
                # Remove all edges connected to this node
                edges_to_remove = []
                if hasattr(self.scene, 'edges') and self.scene.edges:
                    for edge in self.scene.edges[:]:
                        if edge._start_node == node or edge._end_node == node:
                            edges_to_remove.append(edge)
                
                for edge in edges_to_remove:
                    # Remove from scene's edges list
                    if hasattr(self.scene, 'edges') and edge in self.scene.edges:
                        self.scene.edges.remove(edge)
                    # Remove control points and edge from scene
                    if edge.start_control and edge.start_control.scene():
                        self.scene.removeItem(edge.start_control)
                    if edge.end_control and edge.end_control.scene():
                        self.scene.removeItem(edge.end_control)
                    if edge.waypoint_control and edge.waypoint_control.scene():
                        self.scene.removeItem(edge.waypoint_control)
                    if edge.title_item and edge.title_item.scene():
                        self.scene.removeItem(edge.title_item)
                    self.scene.removeItem(edge)
                
                # Remove from scene and nodes list
                self.scene.removeItem(node)
                if node in self.nodes:
                    self.nodes.remove(node)
                
                self.statusBar().showMessage(f"Undone: Node '{node.title}' creation deleted", 2000)
            else:
                self.statusBar().showMessage("Cannot undo: Node already deleted", 2000)
                return
        
        elif action_type == 'node_delete':
            # Undo node deletion by recreating the node
            node_data = action['node_data']
            
            # Create a new node with the saved data (don't pass position to constructor yet)
            node = Node(node_data['title'], None, node_data['parent'])
            node.action_monitor = self.action_monitor
            
            # Restore node type
            if node_data['node_type']:
                node.set_node_type(node_data['node_type'])
                # Update title
                node.title = node_data['title']
                node.title_item.setPlainText(node_data['title'])
            
            # Restore initial state
            node.is_initial = node_data['is_initial']
            
            # Restore rect if available
            if node_data['rect']:
                node.rect = node_data['rect']
                if hasattr(node, 'update_handles'):
                    node.update_handles()
            
            # Add to scene and set position
            if node_data['parent']:
                node_data['parent'].add_child_node(node)
                # For child nodes, set position after adding to parent
                # The position is relative to the parent
                node.setPos(node_data['position'])
                print(f"[DEBUG] UNDO node delete: Recreated node '{node.title}' at position ({node_data['position'].x():.2f}, {node_data['position'].y():.2f}) as child of '{node_data['parent'].title}'")
            else:
                self.scene.addItem(node)
                self.nodes.append(node)
                # For top-level nodes, set position directly
                node.setPos(node_data['position'])
                print(f"[DEBUG] UNDO node delete: Recreated node '{node.title}' at position ({node_data['position'].x():.2f}, {node_data['position'].y():.2f})")

            # Update any stored edge deletion records to reference this new node instance
            self._relink_stored_edge_nodes(node_data['node_id'], node)

            # Create a mapping from old node ID to the restored node
            node_id_mapping = {node_data['node_id']: node}
            
            # Helper function to find a node by ID in all nodes (including children)
            def find_node_by_id(node_id):
                # Check top-level nodes
                for n in self.nodes:
                    if id(n) == node_id:
                        return n
                    # Check child nodes recursively
                    def check_children(parent):
                        for child in parent.child_nodes:
                            if id(child) == node_id:
                                return child
                            result = check_children(child)
                            if result:
                                return result
                        return None
                    result = check_children(n)
                    if result:
                        return result
                return None
            
            # Restore connected edges
            from edge import Edge
            if 'connected_edges' in action and action['connected_edges']:
                for edge_data in action['connected_edges']:
                    # Find the start and end nodes by ID
                    start_node = None
                    end_node = None
                    
                    # Check if start node is the restored node
                    if edge_data['start_node_id'] == node_data['node_id']:
                        start_node = node
                    else:
                        # Find start node in all nodes (including children)
                        start_node = find_node_by_id(edge_data['start_node_id'])
                    
                    # Check if end node is the restored node
                    if edge_data['end_node_id'] == node_data['node_id']:
                        end_node = node
                    else:
                        # Find end node in all nodes (including children)
                        end_node = find_node_by_id(edge_data['end_node_id'])
                    
                    # Only restore edges where both nodes exist
                    if start_node and end_node:
                        # Create new edge
                        edge = Edge(start_node.scenePos())
                        edge.set_start_node(start_node)
                        edge.set_end_node(end_node)
                        edge.set_title(edge_data['title'])
                        edge.waypoint_ratio = edge_data['waypoint_ratio']
                        
                        # Add to scene
                        self.scene.addItem(edge)
                        edge.create_control_points(self.scene)
                        
                        # Restore connection offsets
                        if edge.start_control:
                            edge.start_control.offset = edge_data['start_offset']
                            edge.start_control.update_position()  # Update control point position
                        if edge.end_control:
                            edge.end_control.offset = edge_data['end_offset']
                            edge.end_control.update_position()  # Update control point position
                        
                        # Update path to reflect the restored offsets
                        edge.update_path()
                        
                        # Add to edges list
                        if not hasattr(self.scene, 'edges'):
                            self.scene.edges = []
                        self.scene.edges.append(edge)
            
            self.statusBar().showMessage(f"Undone: Node '{node_data['title']}' and {len(action.get('connected_edges', []))} edge(s) restored", 2000)
            action['restored_node'] = node
        
        elif action_type == 'node_type_change':
            # Undo node type change
            node = action['node']
            old_type = action['old_type']
            old_title = action['old_title']
            
            if node.scene() == self.scene:
                # Restore the old type
                node.set_node_type(old_type)
                # Restore the original title (set_node_type may have changed it)
                node.title = old_title
                node.title_item.setPlainText(old_title)
                type_name = old_type if old_type else "None"
                self.statusBar().showMessage(f"Undone: Node type restored to {type_name}", 2000)
            else:
                self.statusBar().showMessage("Cannot undo: Node no longer exists", 2000)
                return
        
        elif action_type == 'node_resize':
            # Undo node resize
            node = action['node']
            old_rect = action['old_rect']
            
            if node.scene() == self.scene:
                new_rect = action['new_rect']
                print(f"[DEBUG] UNDO node resize: '{node.title}' from size ({new_rect.width():.2f}, {new_rect.height():.2f}) back to ({old_rect.width():.2f}, {old_rect.height():.2f}) at position ({node.pos().x():.2f}, {node.pos().y():.2f})")
                
                # Restore the old rect
                node.prepareGeometryChange()
                node.rect = old_rect
                if hasattr(node, 'update_handles'):
                    node.update_handles()
                node.update()
                self.statusBar().showMessage(f"Undone: Node '{node.title}' resized back", 2000)
            else:
                self.statusBar().showMessage("Cannot undo: Node no longer exists", 2000)
                return
        
        elif action_type == 'node_initial_change':
            node = action['node']
            was_initial = action['was_initial']
            if node.scene() == self.scene and node.node_type == "State":
                node.set_initial_state(was_initial)
                state_text = "initial" if was_initial else "non-initial"
                self.statusBar().showMessage(f"Undone: Node marked as {state_text}", 2000)
            else:
                self.statusBar().showMessage("Cannot undo: Node no longer exists", 2000)
                return

        
        elif action_type == 'edge_create':
            # Undo edge creation by deleting the edge
            from edge import Edge
            edge = action['edge']
            if edge.scene() == self.scene:
                # Remove from scene's edges list
                if hasattr(self.scene, 'edges') and edge in self.scene.edges:
                    self.scene.edges.remove(edge)
                # Remove control points and edge from scene, and null out references
                if edge.start_control and edge.start_control.scene():
                    self.scene.removeItem(edge.start_control)
                    edge.start_control = None
                if edge.end_control and edge.end_control.scene():
                    self.scene.removeItem(edge.end_control)
                    edge.end_control = None
                if edge.waypoint_control and edge.waypoint_control.scene():
                    self.scene.removeItem(edge.waypoint_control)
                    edge.waypoint_control = None
                if edge.title_item and edge.title_item.scene():
                    self.scene.removeItem(edge.title_item)
                self.scene.removeItem(edge)
                self.statusBar().showMessage(f"Undone: Edge creation deleted", 2000)
            else:
                self.statusBar().showMessage("Cannot undo: Edge already deleted", 2000)
                return
        
        elif action_type == 'edge_delete':
            # Undo edge deletion by recreating the edge
            from edge import Edge
            edge_data = action['edge_data']

            def find_node_by_id(target_id):
                if target_id is None:
                    return None
                for n in self.nodes:
                    if id(n) == target_id:
                        return n
                    def check_children(parent):
                        for child in parent.child_nodes:
                            if id(child) == target_id:
                                return child
                            result = check_children(child)
                            if result:
                                return result
                        return None
                    result = check_children(n)
                    if result:
                        return result
                return None

            start_node = edge_data.get('start_node')
            end_node = edge_data.get('end_node')

            if (not start_node or start_node.scene() != self.scene) and edge_data.get('start_node_id'):
                start_node = find_node_by_id(edge_data['start_node_id'])
            if (not end_node or end_node.scene() != self.scene) and edge_data.get('end_node_id'):
                end_node = find_node_by_id(edge_data['end_node_id'])
            
            if start_node and end_node:
                # Create new edge
                edge = Edge(start_node.scenePos())
                edge.set_start_node(start_node)
                edge.set_end_node(end_node)
                edge.set_title(edge_data['title'])
                # Ensure waypoint_ratio has a default value if None
                edge.waypoint_ratio = edge_data['waypoint_ratio'] if edge_data['waypoint_ratio'] is not None else 0.5
                
                # Add to scene
                self.scene.addItem(edge)
                edge.create_control_points(self.scene)
                
                # Restore/snap connection offsets to node boundaries
                saved_start = QPointF(edge_data['start_offset']) if 'start_offset' in edge_data else None
                saved_end = QPointF(edge_data['end_offset']) if 'end_offset' in edge_data else None
                edge.snap_endpoints_to_nodes(saved_start=saved_start, saved_end=saved_end)
                
                # Add to edges list
                if not hasattr(self.scene, 'edges'):
                    self.scene.edges = []
                self.scene.edges.append(edge)
                
                self.statusBar().showMessage(f"Undone: Edge '{edge_data['title']}' restored", 2000)
                action['restored_edge'] = edge
            else:
                self.statusBar().showMessage("Cannot undo: Connected nodes no longer exist", 2000)
                return
        
        elif action_type == 'edge_connection_change':
            # Undo edge connection point change
            edge = action['edge']
            is_start = action['is_start']
            old_offset = action['old_offset']
            
            if edge.scene() == self.scene:
                # Restore the old offset
                if is_start and edge.start_control:
                    edge.start_control.offset = old_offset
                    edge.start_control.update_position()
                elif not is_start and edge.end_control:
                    edge.end_control.offset = old_offset
                    edge.end_control.update_position()
                
                # Update the edge path
                edge.update_path()
                
                point_name = "start" if is_start else "end"
                self.statusBar().showMessage(f"Undone: Edge {point_name} connection point restored", 2000)
            else:
                self.statusBar().showMessage("Cannot undo: Edge no longer exists", 2000)
                return
        
        elif action_type == 'edge_waypoint_change':
            # Undo edge waypoint adjustment
            edge = action['edge']
            old_ratio = action['old_ratio']
            
            if edge.scene() == self.scene:
                # Restore the old waypoint ratio (use default if None)
                edge.waypoint_ratio = old_ratio if old_ratio is not None else 0.5
                
                # Update the edge path
                edge.update_path()
                
                self.statusBar().showMessage(f"Undone: Edge waypoint adjusted back", 2000)
            else:
                self.statusBar().showMessage("Cannot undo: Edge no longer exists", 2000)
                return
        
        elif action_type == 'node_title_change':
            # Undo node title change
            node = action['node']
            old_title = action['old_title']
            
            if node.scene() == self.scene:
                # Restore the old title
                node.title = old_title
                node.title_item.setPlainText(old_title)
                node.update()
                self.statusBar().showMessage(f"Undone: Node title restored to '{old_title}'", 2000)
            else:
                self.statusBar().showMessage("Cannot undo: Node no longer exists", 2000)
                return
        
        elif action_type == 'edge_title_change':
            # Undo edge title change
            edge = action['edge']
            old_title = action['old_title']
            
            if edge.scene() == self.scene:
                # Restore the old title
                edge.set_title(old_title)
                self.statusBar().showMessage(f"Undone: Edge title restored to '{old_title}'", 2000)
            else:
                self.statusBar().showMessage("Cannot undo: Edge no longer exists", 2000)
                return
        
        elif action_type == 'node_reparent':
            # Undo node reparenting
            node = action['node']
            old_parent = action['old_parent']
            new_parent = action['new_parent']
            old_pos = action['old_pos']
            
            if node.scene() == self.scene or (node.parent_node and node.parent_node.scene() == self.scene):
                # Print debug info
                old_parent_name = old_parent.title if old_parent else "main scene"
                new_parent_name = new_parent.title if new_parent else "main scene"
                print(f"[DEBUG] UNDO node reparent: '{node.title}' from parent '{new_parent_name}' back to '{old_parent_name}' at position ({old_pos.x():.2f}, {old_pos.y():.2f})" if old_pos else f"[DEBUG] UNDO node reparent: '{node.title}' from parent '{new_parent_name}' back to '{old_parent_name}'")
                
                # Temporarily disable parent checking to avoid recording this change
                node._checking_parent = True
                
                try:
                    # Remove from current parent
                    if node.parent_node is not None:
                        node.parent_node.remove_child_node(node)
                    
                    # Restore to old parent
                    if old_parent is not None:
                        # Re-add to old parent
                        if not old_parent.is_container:
                            old_parent.setup_container()
                        old_parent.add_child_node(node, None)
                        # Restore old position in parent's coordinate system
                        if old_pos:
                            node.setPos(old_pos)
                    else:
                        # Add back to main scene
                        if node.scene() != self.scene:
                            self.scene.addItem(node)
                        # Restore old position in scene coordinates
                        if old_pos:
                            node.setPos(old_pos)
                    
                    # Update edges
                    node.update_descendant_edges()
                    
                    parent_name = old_parent.title if old_parent else "main scene"
                    self.statusBar().showMessage(f"Undone: Node '{node.title}' reparented back to '{parent_name}'", 2000)
                finally:
                    node._checking_parent = False
            else:
                self.statusBar().showMessage("Cannot undo: Node no longer exists", 2000)
                return
        
        # After successful undo, push this action onto the redo stack
        if hasattr(self, 'redo_stack'):
            self.redo_stack.append(action)
            if len(self.redo_stack) > self.max_undo_stack_size:
                self.redo_stack.pop(0)

        # Signal the undo action
        if hasattr(self, 'action_monitor'):
            # Add undo action type if not already present
            if 'undo' not in self.action_monitor.actions:
                self.action_monitor.add_action_type('undo', QColor("#9B59B6"), 300)  # Purple
            self.action_monitor.signal_action('undo')

    def redo_action(self):
        """Redo the last undone action"""
        if not hasattr(self, 'redo_stack') or not self.redo_stack:
            self.statusBar().showMessage("Nothing to redo", 2000)
            return

        action = self.redo_stack.pop()
        action_type = action['type']

        if action_type == 'node_move':
            node = action['node']
            old_pos = action['old_pos']
            new_pos = action['new_pos']

            if node.scene() == self.scene:
                print(f"[DEBUG] REDO node move: '{node.title}' from position ({old_pos.x():.2f}, {old_pos.y():.2f}) to ({new_pos.x():.2f}, {new_pos.y():.2f})")
                
                # Make sure this synthetic move is not recorded as another user move
                node.position_before_move = None
                node.is_being_moved = False

                # Force the visual update by ensuring the position actually changes
                # Use prepareGeometryChange to notify the scene of the upcoming change
                node.prepareGeometryChange()
                node.setPos(new_pos)
                node.update()
                node.update_descendant_edges()
                self.statusBar().showMessage("Redone: Node moved to new position", 2000)
            else:
                self.statusBar().showMessage("Cannot redo: Node no longer exists", 2000)
                return

        elif action_type == 'node_create':
            node = action['node']
            parent = action['parent']
            position = action.get('position', node.pos())

            if node.scene() == self.scene:
                self.statusBar().showMessage("Cannot redo: Node already exists", 2000)
                return

            if parent:
                parent.add_child_node(node, pos=position)
                print(f"[DEBUG] REDO node create: Recreated node '{node.title}' at position ({position.x():.2f}, {position.y():.2f}) as child of '{parent.title}'")
            else:
                self.scene.addItem(node)
                if node not in self.nodes:
                    self.nodes.append(node)
                node.setPos(position)
                print(f"[DEBUG] REDO node create: Recreated node '{node.title}' at position ({position.x():.2f}, {position.y():.2f})")

            self.statusBar().showMessage(f"Redone: Node '{node.title}' creation restored", 2000)

        elif action_type == 'node_delete':
            node = action.get('restored_node')
            node_data = action.get('node_data', {})

            if not node or node.scene() != self.scene:
                self.statusBar().showMessage("Cannot redo: Node no longer exists", 2000)
                return

            title = getattr(node, 'title', node_data.get('title', ""))
            print(f"[DEBUG] REDO node delete: Deleting node '{title}' at position ({node.pos().x():.2f}, {node.pos().y():.2f})")
            self.delete_node(node, record_for_undo=False)
            self.statusBar().showMessage(f"Redone: Node '{title}' deleted again", 2000)

        elif action_type == 'node_type_change':
            node = action['node']
            new_type = action['new_type']

            if node.scene() == self.scene:
                node.set_node_type(new_type)
                type_name = new_type if new_type else "None"
                self.statusBar().showMessage(f"Redone: Node type changed to {type_name}", 2000)
            else:
                self.statusBar().showMessage("Cannot redo: Node no longer exists", 2000)
                return

        elif action_type == 'node_resize':
            node = action['node']
            new_rect = action['new_rect']

            if node.scene() == self.scene:
                old_rect = action['old_rect']
                print(f"[DEBUG] REDO node resize: '{node.title}' from size ({old_rect.width():.2f}, {old_rect.height():.2f}) to ({new_rect.width():.2f}, {new_rect.height():.2f}) at position ({node.pos().x():.2f}, {node.pos().y():.2f})")
                
                node.prepareGeometryChange()
                node.rect = new_rect
                if hasattr(node, 'update_handles'):
                    node.update_handles()
                node.update()
                self.statusBar().showMessage(f"Redone: Node '{node.title}' resized", 2000)
            else:
                self.statusBar().showMessage("Cannot redo: Node no longer exists", 2000)
                return

        elif action_type == 'node_initial_change':
            node = action['node']
            is_initial = action['is_initial']
            if node.scene() == self.scene and node.node_type == "State":
                node.set_initial_state(is_initial)
                state_text = "initial" if is_initial else "non-initial"
                self.statusBar().showMessage(f"Redone: Node marked as {state_text}", 2000)
            else:
                self.statusBar().showMessage("Cannot redo: Node no longer exists", 2000)
                return

        elif action_type == 'edge_create':
            from edge import Edge
            edge = action['edge']
            start_node = action.get('start_node')
            end_node = action.get('end_node')

            if not start_node or not end_node:
                self.statusBar().showMessage("Cannot redo: Connected nodes no longer exist", 2000)
                return

            if start_node.scene() != self.scene or end_node.scene() != self.scene:
                self.statusBar().showMessage("Cannot redo: Connected nodes no longer exist", 2000)
                return

            if edge.scene() != self.scene:
                edge.set_start_node(start_node)
                edge.set_end_node(end_node)
                self.scene.addItem(edge)
                edge.create_control_points(self.scene)
                if not hasattr(self.scene, 'edges'):
                    self.scene.edges = []
                if edge not in self.scene.edges:
                    self.scene.edges.append(edge)

            self.statusBar().showMessage("Redone: Edge creation restored", 2000)

        elif action_type == 'edge_delete':
            edge = action.get('restored_edge')
            edge_data = action.get('edge_data', {})

            if not edge or edge.scene() != self.scene:
                self.statusBar().showMessage("Cannot redo: Edge no longer exists", 2000)
                return

            title = edge.title_item.toPlainText() if edge.title_item else edge_data.get('title', "")
            edge.delete_edge(record_for_undo=False)
            self.statusBar().showMessage(f"Redone: Edge '{title}' deleted again", 2000)

        elif action_type == 'edge_connection_change':
            edge = action['edge']
            is_start = action['is_start']
            new_offset = action['new_offset']

            if edge.scene() == self.scene:
                if is_start and edge.start_control:
                    edge.start_control.offset = new_offset
                    edge.start_control.update_position()
                elif not is_start and edge.end_control:
                    edge.end_control.offset = new_offset
                    edge.end_control.update_position()

                edge.update_path()
                point_name = "start" if is_start else "end"
                self.statusBar().showMessage(f"Redone: Edge {point_name} connection point changed", 2000)
            else:
                self.statusBar().showMessage("Cannot redo: Edge no longer exists", 2000)
                return

        elif action_type == 'edge_waypoint_change':
            edge = action['edge']
            new_ratio = action['new_ratio']

            if edge.scene() == self.scene:
                edge.waypoint_ratio = new_ratio if new_ratio is not None else 0.5
                edge.update_path()
                self.statusBar().showMessage("Redone: Edge waypoint adjusted", 2000)
            else:
                self.statusBar().showMessage("Cannot redo: Edge no longer exists", 2000)
                return

        elif action_type == 'node_title_change':
            node = action['node']
            new_title = action['new_title']

            if node.scene() == self.scene:
                node.title = new_title
                node.title_item.setPlainText(new_title)
                node.update()
                self.statusBar().showMessage(f"Redone: Node title changed to '{new_title}'", 2000)
            else:
                self.statusBar().showMessage("Cannot redo: Node no longer exists", 2000)
                return

        elif action_type == 'edge_title_change':
            edge = action['edge']
            new_title = action['new_title']

            if edge.scene() == self.scene:
                edge.set_title(new_title)
                self.statusBar().showMessage(f"Redone: Edge title changed to '{new_title}'", 2000)
            else:
                self.statusBar().showMessage("Cannot redo: Edge no longer exists", 2000)
                return
        
        elif action_type == 'node_reparent':
            # Redo node reparenting
            node = action['node']
            old_parent = action['old_parent']
            new_parent = action['new_parent']
            new_pos = action['new_pos']
            
            if node.scene() == self.scene or (node.parent_node and node.parent_node.scene() == self.scene):
                # Print debug info
                old_parent_name = old_parent.title if old_parent else "main scene"
                new_parent_name = new_parent.title if new_parent else "main scene"
                print(f"[DEBUG] REDO node reparent: '{node.title}' from parent '{old_parent_name}' to '{new_parent_name}' at position ({new_pos.x():.2f}, {new_pos.y():.2f})" if new_pos else f"[DEBUG] REDO node reparent: '{node.title}' from parent '{old_parent_name}' to '{new_parent_name}'")
                
                # Temporarily disable parent checking to avoid recording this change
                node._checking_parent = True
                
                try:
                    # Remove from current parent
                    if node.parent_node is not None:
                        node.parent_node.remove_child_node(node)
                    
                    # Restore to new parent
                    if new_parent is not None:
                        # Re-add to new parent
                        if not new_parent.is_container:
                            new_parent.setup_container()
                        new_parent.add_child_node(node, None)
                        # Restore new position in parent's coordinate system
                        if new_pos:
                            node.setPos(new_pos)
                    else:
                        # Add back to main scene
                        if node.scene() != self.scene:
                            self.scene.addItem(node)
                        # Restore new position in scene coordinates
                        if new_pos:
                            node.setPos(new_pos)
                    
                    # Update edges
                    node.update_descendant_edges()
                    
                    parent_name = new_parent.title if new_parent else "main scene"
                    self.statusBar().showMessage(f"Redone: Node '{node.title}' reparented to '{parent_name}'", 2000)
                finally:
                    node._checking_parent = False
            else:
                self.statusBar().showMessage("Cannot redo: Node no longer exists", 2000)
                return

        else:
            self.statusBar().showMessage("Cannot redo: Unknown action type", 2000)
            return

        # After successful redo, push this action back onto the undo stack
        if hasattr(self, 'undo_stack'):
            self.undo_stack.append(action)
            if len(self.undo_stack) > self.max_undo_stack_size:
                self.undo_stack.pop(0)

        if hasattr(self, 'action_monitor'):
            if 'redo' not in self.action_monitor.actions:
                self.action_monitor.add_action_type('redo', QColor("#1ABC9C"), 300)
            self.action_monitor.signal_action('redo')
    
    def delete_selected_items(self):
        """Delete all selected items (nodes and edges)"""
        from edge import Edge
        
        selected_items = self.scene.selectedItems()
        
        for item in selected_items:
            if isinstance(item, Edge):
                item.delete_edge()
            elif isinstance(item, Node):
                self.delete_node(item)
    
    def new_design(self):
        """Clear the current design and start fresh"""
        # Ask for confirmation if there are items in the scene
        if self.nodes or (hasattr(self.scene, 'edges') and self.scene.edges):
            reply = QMessageBox.question(
                self,
                "New Design",
                "Are you sure you want to clear the current design?\nAny unsaved changes will be lost.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        # Clear the scene
        self.scene.clear()
        
        # Clear nodes list
        self.nodes.clear()
        
        # Clear edges list
        if hasattr(self.scene, 'edges'):
            self.scene.edges.clear()
        else:
            self.scene.edges = []
        
        if hasattr(self, 'edges'):
            self.edges.clear()
        
        # Clear undo/redo stacks
        if hasattr(self, 'undo_stack'):
            self.undo_stack.clear()
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
        
        # Clear current file and update window title
        self.current_file = None
        self.update_window_title()
        
        # Update status bar
        self.statusBar().showMessage("New design created")
    
    def save_design(self):
        """Save the current design to a JSON file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Design",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            # Collect all nodes recursively (including children)
            def collect_all_nodes(node_list):
                all_nodes = []
                for node in node_list:
                    all_nodes.append(node)
                    # Recursively collect child nodes
                    if hasattr(node, 'child_nodes') and node.child_nodes:
                        all_nodes.extend(collect_all_nodes(node.child_nodes))
                return all_nodes
            
            all_nodes = collect_all_nodes(self.nodes)
            
            # Serialize nodes
            nodes_data = []
            for node in all_nodes:
                # For child nodes, pos() is already in parent's local coordinates
                # For top-level nodes, pos() is in scene coordinates
                node_data = {
                    'title': node.title,
                    'pos': {'x': node.pos().x(), 'y': node.pos().y()},
                    'rect': {
                        'x': node.rect.x(),
                        'y': node.rect.y(),
                        'width': node.rect.width(),
                        'height': node.rect.height()
                    },
                    'node_type': getattr(node, 'node_type', None),
                    'is_container': node.is_container,
                    'is_initial': getattr(node, 'is_initial', False),
                    'parent_id': id(node.parent_node) if hasattr(node, 'parent_node') and node.parent_node else None,
                    'id': id(node)  # Use object id as unique identifier
                }
                nodes_data.append(node_data)
            
            # Serialize edges (check both self.edges and self.scene.edges)
            edges_data = []
            edges_list = None
            if hasattr(self.scene, 'edges') and self.scene.edges:
                edges_list = self.scene.edges
            elif hasattr(self, 'edges') and self.edges:
                edges_list = self.edges
            
            if edges_list:
                for edge in edges_list:
                    # Save control point offsets for accurate positioning
                    start_offset = None
                    end_offset = None
                    
                    if hasattr(edge, 'start_offset') and edge.start_offset:
                        start_offset = {'x': edge.start_offset.x(), 'y': edge.start_offset.y()}
                    elif hasattr(edge, 'start_control') and edge.start_control and hasattr(edge.start_control, 'offset'):
                        start_offset = {'x': edge.start_control.offset.x(), 'y': edge.start_control.offset.y()}
                    
                    if hasattr(edge, 'end_offset') and edge.end_offset:
                        end_offset = {'x': edge.end_offset.x(), 'y': edge.end_offset.y()}
                    elif hasattr(edge, 'end_control') and edge.end_control and hasattr(edge.end_control, 'offset'):
                        end_offset = {'x': edge.end_control.offset.x(), 'y': edge.end_control.offset.y()}
                    
                    edge_data = {
                        'start_node_id': id(edge._start_node) if edge._start_node else None,
                        'end_node_id': id(edge._end_node) if edge._end_node else None,
                        'title': edge.title_item.toPlainText() if hasattr(edge, 'title_item') else "",
                        'waypoint_ratio': edge.waypoint_ratio if hasattr(edge, 'waypoint_ratio') else 0.5,
                        'start_offset': start_offset,
                        'end_offset': end_offset
                    }
                    edges_data.append(edge_data)
            
            # Create the design data structure
            design_data = {
                'nodes': nodes_data,
                'edges': edges_data
            }
            
            # Write to file (mode 'w' truncates existing file first)
            # Explicitly truncate and write to ensure clean save
            with open(file_path, 'w') as f:
                f.truncate(0)  # Explicitly clear file content
                json.dump(design_data, f, indent=2)
                f.flush()  # Ensure data is written to disk
            
            # Update current file and window title
            self.current_file = file_path
            self.update_window_title()
            
            self.statusBar().showMessage(f"Design saved to {file_path}")
            QMessageBox.information(self, "Success", "Design saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save design: {str(e)}")
            self.statusBar().showMessage("Failed to save design")
    
    def load_design(self):
        """Load a design from a JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Design",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            # Read from file
            with open(file_path, 'r') as f:
                design_data = json.load(f)
            
            # Clear existing design
            self.scene.clear()
            self.nodes.clear()
            
            # Clear edges from both locations
            if hasattr(self.scene, 'edges'):
                self.scene.edges.clear()
            else:
                self.scene.edges = []
            
            if hasattr(self, 'edges'):
                self.edges.clear()
            
            # Create a mapping from old IDs to new node objects
            id_to_node = {}
            
            # First pass: Create all nodes without parent relationships
            for node_data in design_data.get('nodes', []):
                pos = QPointF(node_data['pos']['x'], node_data['pos']['y'])
                node = Node(node_data['title'], pos)
                
                # Set the action monitor reference
                node.action_monitor = self.action_monitor
                
                # Restore rect
                rect_data = node_data['rect']
                node.rect = QRectF(
                    rect_data['x'],
                    rect_data['y'],
                    rect_data['width'],
                    rect_data['height']
                )
                
                # Update resize handle position after restoring rect
                if hasattr(node, 'update_handles'):
                    node.update_handles()
                
                # Restore node type
                if node_data.get('node_type'):
                    node.set_node_type(node_data['node_type'])
                
                # Restore the original title from JSON (after set_node_type which may overwrite it)
                node.title = node_data['title']
                node.title_item.setPlainText(node_data['title'])
                
                # Restore initial state property
                node.is_initial = node_data.get('is_initial', False)
                
                # Restore container status
                node.is_container = node_data.get('is_container', False)
                
                # Update inner rect for containers
                if node_data.get('is_container') and hasattr(node, 'update_inner_rect'):
                    node.update_inner_rect()
                
                # Map old ID to new node
                id_to_node[node_data['id']] = node
                
                # Store parent_id for second pass
                node._temp_parent_id = node_data.get('parent_id')
            
            # Second pass: Establish parent-child relationships
            for node_data in design_data.get('nodes', []):
                node = id_to_node[node_data['id']]
                parent_id = node_data.get('parent_id')
                
                if parent_id and parent_id in id_to_node:
                    # This node has a parent - add as child with saved position
                    parent_node = id_to_node[parent_id]
                    # Position is already in parent's local coordinates from save
                    saved_pos = QPointF(node_data['pos']['x'], node_data['pos']['y'])
                    parent_node.add_child_node(node, saved_pos)
                else:
                    # This is a top-level node - add to scene and nodes list
                    self.scene.addItem(node)
                    self.nodes.append(node)
                
                # Clean up temporary attribute
                if hasattr(node, '_temp_parent_id'):
                    delattr(node, '_temp_parent_id')
            
            # Recreate edges
            for edge_data in design_data.get('edges', []):
                start_node_id = edge_data.get('start_node_id')
                end_node_id = edge_data.get('end_node_id')
                
                if start_node_id in id_to_node and end_node_id in id_to_node:
                    start_node = id_to_node[start_node_id]
                    end_node = id_to_node[end_node_id]
                    
                    # Create edge
                    edge = Edge(start_node.scenePos())
                    edge.set_start_node(start_node)
                    edge.set_end_node(end_node)
                    edge.set_title(edge_data['title'])
                    # Ensure waypoint_ratio has a default value if None
                    edge.waypoint_ratio = edge_data['waypoint_ratio'] if edge_data['waypoint_ratio'] is not None else 0.5
                    
                    # Add to scene
                    self.scene.addItem(edge)
                    edge.create_control_points(self.scene)
                    
                    # Restore connection offsets
                    if edge.start_control:
                        start_offset = edge_data.get('start_offset')
                        if isinstance(start_offset, dict):
                            start_offset = QPointF(start_offset.get('x', 0), start_offset.get('y', 0))
                        if isinstance(start_offset, QPointF):
                            edge.start_control.offset = QPointF(start_offset)
                            edge.start_offset = QPointF(start_offset)
                    if edge.end_control:
                        end_offset = edge_data.get('end_offset')
                        if isinstance(end_offset, dict):
                            end_offset = QPointF(end_offset.get('x', 0), end_offset.get('y', 0))
                        if isinstance(end_offset, QPointF):
                            edge.end_control.offset = QPointF(end_offset)
                            edge.end_offset = QPointF(end_offset)
                    
                    # Update path
                    edge.update_path()
                    
                    # Add to edges list
                    if not hasattr(self.scene, 'edges'):
                        self.scene.edges = []
                    self.scene.edges.append(edge)
            
            # Clear undo/redo stacks for the new design
            if hasattr(self, 'undo_stack'):
                self.undo_stack.clear()
            if hasattr(self, 'redo_stack'):
                self.redo_stack.clear()
            
            # Update current file and window title
            self.current_file = file_path
            self.update_window_title()
            
            self.statusBar().showMessage(f"Design loaded from {file_path}")
            QMessageBox.information(self, "Success", "Design loaded successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load design: {str(e)}")
            self.statusBar().showMessage("Failed to load design")
    
    def createMenu(self):
        # Create menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # New action
        new_action = file_menu.addAction("New")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_design)
        
        file_menu.addSeparator()
        
        # Save action
        save_action = file_menu.addAction("Save")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_design)
        
        # Load action
        load_action = file_menu.addAction("Load")
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load_design)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = file_menu.addAction("Exit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        # Zoom in action
        zoom_in_action = view_menu.addAction("Zoom In")
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoomIn)
        
        # Zoom out action
        zoom_out_action = view_menu.addAction("Zoom Out")
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoomOut)
        
        # Reset zoom action
        reset_zoom_action = view_menu.addAction("Reset Zoom")
        reset_zoom_action.setShortcut("Ctrl+0")
        reset_zoom_action.triggered.connect(self.resetZoom)

    def make_red_cross_circle_icon(self, size=24, cross_width=3, circle_width=2,
                                   cross_color=QColor("#ff3b30"), circle_color=QColor("#ff3b30")) -> QIcon:
        """Create a red cross inside a circle icon for toolbar buttons."""
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)

        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Circle
        painter.setPen(QPen(circle_color, circle_width))
        painter.setBrush(Qt.NoBrush)
        r = size / 2 - circle_width
        center = pm.rect().center()
        painter.drawEllipse(center, r, r)

        # Cross
        painter.setPen(QPen(cross_color, cross_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        margin = int(size * 0.28)
        painter.drawLine(margin, margin, size - margin, size - margin)
        painter.drawLine(size - margin, margin, margin, size - margin)
        painter.end()

        return QIcon(pm)

    def make_red_cross_svg_icon(self, size=24) -> QIcon:
        """Create a crisp red cross 'X' icon from inline SVG (scales cleanly)."""
        svg = f"""
        <svg width=\"{size}\" height=\"{size}\" viewBox=\"0 0 24 24\" fill=\"none\"
             xmlns=\"http://www.w3.org/2000/svg\">
          <path d=\"M6 6 L18 18 M18 6 L6 18\"
                stroke=\"#E74C3C\" stroke-width=\"3\" stroke-linecap=\"round\"/>
        </svg>
        """
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        renderer.render(painter)
        painter.end()
        return QIcon(pm)
    
    def make_state_node_svg_icon(self, size=24, title_color="#e67e22", label=None) -> QIcon:
        """Create a node-like icon: rounded rect with colored title bar (SVG).
        Optionally draws a centered label (e.g., 'S' or 'M')."""
        border_color = "#747574"
        body_color = "#2c3e50"
        radius = 4
        bar_h = 8
        stroke_w = 2
        # Optional centered label
        label_svg = ""
        if label:
            # White, bold, centered. Position slightly below center for visual balance.
            # font-size chosen to fit within 24x24 while readable.
            label_svg = f"<text x=\"12\" y=\"15\" text-anchor=\"middle\" dominant-baseline=\"middle\" \
                             font-family=\"Arial, Helvetica, sans-serif\" font-size=\"9\" font-weight=\"700\" \
                             fill=\"#FFFFFF\">{label}</text>"
        svg = f"""
        <svg width=\"{size}\" height=\"{size}\" viewBox=\"0 0 24 24\" fill=\"none\"
             xmlns=\"http://www.w3.org/2000/svg\">\n          <defs>\n            <clipPath id=\"rrect\">\n              <rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"{radius}\" ry=\"{radius}\"/>\n            </clipPath>\n          </defs>\n          <rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"{radius}\" ry=\"{radius}\" fill=\"{body_color}\"/>\n          <g clip-path=\"url(#rrect)\">\n            <rect x=\"3\" y=\"3\" width=\"18\" height=\"{bar_h}\" fill=\"{title_color}\"/>\n          </g>\n          <rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"{radius}\" ry=\"{radius}\" stroke=\"{border_color}\" stroke-width=\"{stroke_w}\" fill=\"none\"/>\n          {label_svg}\n        </svg>\n        """
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        renderer.render(painter)
        painter.end()
        return QIcon(pm)
    
    def make_initial_state_svg_icon(self, size=24) -> QIcon:
        """Create an icon with a white circle (representing initial state indicator)."""
        svg = f"""
        <svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none"
             xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="6" fill="#FFFFFF" stroke="#2c3e50" stroke-width="2"/>
        </svg>
        """
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        renderer.render(painter)
        painter.end()
        return QIcon(pm)
    
    def make_undo_svg_icon(self, size=24) -> QIcon:
        """Create an undo icon with a curved arrow pointing left."""
        svg = f"""
        <svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none"
             xmlns="http://www.w3.org/2000/svg">
          <path d="M9 14 L4 9 L9 4" stroke="#3498db" stroke-width="2.5" 
                stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <path d="M4 9 L13 9 C16.866 9 20 12.134 20 16 C20 16.552 19.552 17 19 17" 
                stroke="#3498db" stroke-width="2.5" stroke-linecap="round" fill="none"/>
        </svg>
        """
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        renderer.render(painter)
        painter.end()
        return QIcon(pm)
    
    def make_redo_svg_icon(self, size=24) -> QIcon:
        """Create a redo icon with a curved arrow pointing right."""
        svg = f"""
        <svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none"
             xmlns="http://www.w3.org/2000/svg">
          <path d="M15 14 L20 9 L15 4" stroke="#3498db" stroke-width="2.5"
                stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <path d="M20 9 L11 9 C7.134 9 4 12.134 4 16 C4 16.552 4.448 17 5 17"
                stroke="#3498db" stroke-width="2.5" stroke-linecap="round" fill="none"/>
        </svg>
        """
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        renderer.render(painter)
        painter.end()
        return QIcon(pm)
    
    def make_new_file_svg_icon(self, size=24) -> QIcon:
        """Create a new file icon."""
        svg = f"""
        <svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none"
             xmlns="http://www.w3.org/2000/svg">
          <path d="M14 2 L14 8 L20 8" stroke="#3498db" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <path d="M14 2 L6 2 C4.895 2 4 2.895 4 4 L4 20 C4 21.105 4.895 22 6 22 L18 22 C19.105 22 20 21.105 20 20 L20 8 L14 2 Z"
                stroke="#3498db" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <path d="M9 12 L15 12 M12 9 L12 15" stroke="#3498db" stroke-width="2"
                stroke-linecap="round" fill="none"/>
        </svg>
        """
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        renderer.render(painter)
        painter.end()
        return QIcon(pm)
    
    def make_save_svg_icon(self, size=24) -> QIcon:
        """Create a save/floppy disk icon."""
        svg = f"""
        <svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none"
             xmlns="http://www.w3.org/2000/svg">
          <path d="M19 21 L5 21 C3.895 21 3 20.105 3 19 L3 5 C3 3.895 3.895 3 5 3 L16 3 L21 8 L21 19 C21 20.105 20.105 21 19 21 Z"
                stroke="#3498db" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <path d="M7 3 L7 8 L15 8 L15 3" stroke="#3498db" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <rect x="7" y="13" width="10" height="5" stroke="#3498db" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        </svg>
        """
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        renderer.render(painter)
        painter.end()
        return QIcon(pm)
    
    def make_load_svg_icon(self, size=24) -> QIcon:
        """Create a load/open folder icon."""
        svg = f"""
        <svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none"
             xmlns="http://www.w3.org/2000/svg">
          <path d="M22 19 C22 20.105 21.105 21 20 21 L4 21 C2.895 21 2 20.105 2 19 L2 5 C2 3.895 2.895 3 4 3 L9 3 L11 6 L20 6 C21.105 6 22 6.895 22 8 L22 19 Z"
                stroke="#3498db" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <path d="M12 11 L12 17 M9 14 L12 11 L15 14" stroke="#3498db" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        </svg>
        """
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        renderer.render(painter)
        painter.end()
        return QIcon(pm)
    
    def zoomIn(self):
        self.view.scale(self.view.zoom_in_factor, self.view.zoom_in_factor)
        self.view.zoom_level += self.view.zoom_step
    
    def zoomOut(self):
        if self.view.zoom_level > self.view.zoom_range[0]:
            self.view.scale(self.view.zoom_out_factor, self.view.zoom_out_factor)
            self.view.zoom_level -= self.view.zoom_step
    
    def resetZoom(self):
        # Reset the view's transformation matrix
        self.view.resetTransform()
        self.view.zoom_level = 0
    
    def update_window_title(self):
        """Update the window title to show the current file name"""
        if self.current_file:
            import os
            filename = os.path.basename(self.current_file)
            self.setWindowTitle(f"The Modeller - {filename}")
        else:
            self.setWindowTitle("The Modeller")
        
    def show_context_menu(self, pos):
        """Show the context menu for nodes"""
        # Map the view coordinates to scene coordinates
        scene_pos = self.view.mapToScene(pos)
        
        # Get the item at the cursor position
        item = self.view.itemAt(pos)
        
        # Create the context menu
        context_menu = QMenu(self)
        
        # If right-clicked on a node, show node-specific options
        if isinstance(item, Node):
            # Add child node action
            add_child_action = context_menu.addAction("Add Child Node")
            add_child_action.triggered.connect(lambda: self.view.add_child_node(item, pos))
            
            # If the node has a parent, add option to remove from parent
            if item.parent_node:
                remove_parent_action = context_menu.addAction("Remove from Parent")
                remove_parent_action.triggered.connect(lambda: self.view.remove_node_from_parent(item))
            
            # Add delete action
            delete_action = context_menu.addAction("Delete Node")
            delete_action.triggered.connect(lambda: self.delete_node(item))
            
            context_menu.addSeparator()
        
        # Always show add node option
        add_node_action = context_menu.addAction("Add Node")
        add_node_action.triggered.connect(lambda: self.add_node(scene_pos))
        
        # Show the menu at the cursor position
        context_menu.exec_(self.view.mapToGlobal(pos))
    
    def add_node(self, pos, parent=None):
        """Add a new node at the specified position"""
        node = Node(f"Node {len(self.nodes) + 1}", pos, parent)
        
        # Set the action monitor reference
        node.action_monitor = self.action_monitor
        
        if parent and isinstance(parent, Node):
            # If parent is provided, add as child
            parent.add_child_node(node)
        else:
            # Otherwise add to the main scene
            self.scene.addItem(node)
            self.nodes.append(node)
            
        # Select the new node
        for item in self.scene.selectedItems():
            item.setSelected(False)
        node.setSelected(True)
        
        # Record node creation for undo
        self.record_node_creation(node, parent)
            
        return node
    
    def delete_node(self, node, record_for_undo=True):
        """Delete a node and all its children, removing connected edges first."""
        if not node:
            return False

        # Collect edges connected to this node
        connected_edges = []
        if hasattr(self.scene, 'edges') and self.scene.edges:
            connected_edges = [edge for edge in self.scene.edges
                               if edge._start_node == node or edge._end_node == node]

        # Delete connected edges first so undo can restore them individually
        for edge in connected_edges:
            edge.delete_edge(record_for_undo=record_for_undo)

        # Record node deletion for undo (before actually deleting)
        # Only record if this is a top-level deletion (not a recursive child deletion)
        if record_for_undo:
            self.record_node_deletion(node)

        # Recursively delete all child nodes (without recording them for undo)
        for child in node.child_nodes[:]:  # Create a copy of the list to iterate over
            if not self.delete_node(child, record_for_undo=False):
                return False

        # Remove from parent's child list if it has a parent
        if node.parent_node and node in node.parent_node.child_nodes:
            node.parent_node.child_nodes.remove(node)

        # Remove from the scene and nodes list
        self.scene.removeItem(node)
        if node in self.nodes:
            self.nodes.remove(node)

        # Don't update the parent node's size when deleting a child
        # This prevents unwanted resizing of parent nodes
        return True

    def validate_undo_action(self, action):
        """Validate that an undo action can still be performed"""
        action_type = action['type']
        
        if action_type == 'node_move':
            # Check if node still exists in scene
            node = action['node']
            return node.scene() == self.scene
            
        elif action_type == 'node_create':
            # For create undo (which means delete), node must exist
            node = action['node']
            parent = action['parent']
            if node.scene() != self.scene:
                return False
            if parent and node not in parent.child_nodes:
                return False
            return True
            
        elif action_type == 'node_delete':
            # For delete undo (which means recreate), node must NOT exist
            node_data = action['node_data']
            
            # Helper to check if node exists by ID
            def node_exists(node_id):
                for n in self.nodes:
                    if id(n) == node_id:
                        return True
                    # Check child nodes recursively
                    def check_children(parent):
                        for child in parent.child_nodes:
                            if id(child) == node_id:
                                return True
                            result = check_children(child)
                            if result:
                                return result
                        return False
                    result = check_children(n)
                    if result:
                        return True
                return False
            
            return not node_exists(node_data['node_id'])
            
        elif action_type == 'node_type_change':
            # Node must exist
            node = action['node']
            return node.scene() == self.scene
            
        return True  # Default to True for unknown action types
