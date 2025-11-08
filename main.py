import sys
import math
import json
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, 
                             QMainWindow, QVBoxLayout, QWidget, QGraphicsItem,
                             QGraphicsRectItem, QGraphicsTextItem, QGraphicsPathItem,
                             QGraphicsEllipseItem, QMenu, QAction, QLineEdit, QSizePolicy,
                             QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF, QByteArray
from PyQt5.QtGui import QPainter, QPen, QColor, QWheelEvent, QBrush, QFont, QPainterPath, QIcon, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from edge import Edge, EdgeControlPoint, WaypointControlPoint, EdgeTitleItem

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
        # Call the parent method to draw the default background
        super().drawBackground(painter, rect)
        
        # Set up the pen for minor grid lines (10% darker)
        minor_pen = QPen(QColor(120, 120, 120, 100))  # Slightly darker gray with transparency
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
        major_pen = QPen(QColor(90, 90, 90, 150))  # Slightly darker gray
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
        
        # Create and add the child node
        child = Node("Child Node", local_pos, parent_node)
        parent_node.add_child_node(child)
        
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
        self.scene.addItem(node)
    
    def delete_node(self, node):
        """Delete the specified node"""
        if node.parent_node:
            node.parent_node.remove_child_node(node)
        self.scene.removeItem(node)
    
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
        
        # Set position if provided
        if pos is not None:
            self.setPos(pos)
            
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
            if event.button() == Qt.LeftButton and self.isSelected():
                if self.is_over_resize_handle(event.pos()):
                    self.is_resizing = True
                    self.old_rect = self.rect
                    self.old_pos = event.pos()
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
            self.title = new_title.strip()
            self.title_item.setPlainText(self.title)
            self.update()
        
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
        """Handle mouse release events for resizing"""
        if hasattr(self, 'is_resizing') and self.is_resizing:
            self.is_resizing = False
            # After resizing, update Z-order of all nodes in the scene
            self.update_z_order()
        super().mouseReleaseEvent(event)
        
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # Update Z-order when position changes
            self.update_z_order()
            
        elif change == QGraphicsItem.ItemPositionHasChanged and self.scene():
            # Update edges for this node and all descendants recursively
            self.update_descendant_edges()
            
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
        self.initUI()
    
    def initUI(self):
        # Set window properties
        self.setWindowTitle("The Modeller")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create toolbar
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        
        # Add an expanding spacer before actions to center the group
        left_spacer = QWidget()
        left_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(left_spacer)
        
        # Add node type buttons
        statemachine_action = toolbar.addAction("StateMachine")
        statemachine_action.setToolTip("Apply StateMachine type (Green) to selected node")
        statemachine_action.triggered.connect(lambda: self.apply_node_type("StateMachine"))
        
        state_action = toolbar.addAction("State")
        state_action.setToolTip("Apply State type (Orange) to selected node")
        state_action.triggered.connect(lambda: self.apply_node_type("State"))

        # Set icons for StateMachine and State actions (SVG-based for crisp scaling) with labels
        sm_hex = "#27ae60"  # base StateMachine title color
        sm_qc = QColor(sm_hex)
        # 40% darker => factor ≈ 166 (since QColor.darker(200) => 50% darker)
        st_qc = QColor(sm_qc).darker(166)
        statemachine_action.setIcon(self.make_state_node_svg_icon(24, title_color=sm_hex, label="M"))
        state_action.setIcon(self.make_state_node_svg_icon(24, title_color=st_qc.name(), label="S"))
        
        toolbar.addSeparator()
        
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
        
        # Set up the status bar
        self.statusBar().showMessage("Ready")
        
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
        
        # Apply the type to all selected nodes
        for node in nodes:
            node.set_node_type(node_type)
        
        # Update status bar
        type_name = "StateMachine (Green)" if node_type == "StateMachine" else "State (Orange)"
        self.statusBar().showMessage(f"Applied {type_name} to {len(nodes)} node(s)")
    
    def delete_selected_items(self):
        """Delete all selected items (nodes and edges)"""
        from edge import Edge
        
        selected_items = self.scene.selectedItems()
        
        for item in selected_items:
            if isinstance(item, Edge):
                item.delete_edge()
            elif isinstance(item, Node):
                self.view.delete_node(item)
    
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
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(design_data, f, indent=2)
            
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
                    
                    # Restore waypoint ratio
                    if 'waypoint_ratio' in edge_data:
                        edge.waypoint_ratio = edge_data['waypoint_ratio']
                    
                    # Restore control point offsets
                    if edge_data.get('start_offset'):
                        offset_data = edge_data['start_offset']
                        edge.start_offset = QPointF(offset_data['x'], offset_data['y'])
                    
                    if edge_data.get('end_offset'):
                        offset_data = edge_data['end_offset']
                        edge.end_offset = QPointF(offset_data['x'], offset_data['y'])
                    
                    # Add to scene
                    self.scene.addItem(edge)
                    
                    # Add to edges list (prefer scene.edges)
                    if hasattr(self.scene, 'edges'):
                        self.scene.edges.append(edge)
                    elif hasattr(self, 'edges'):
                        self.edges.append(edge)
                    
                    # Create control points
                    edge.create_control_points(self.scene)
                    
                    # Restore title
                    if edge_data.get('title'):
                        edge.set_title(edge_data['title'])
                    
                    # Update path
                    edge.update_path()
            
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
            
        return node
    
    def delete_node(self, node):
        """Delete a node and all its children"""
        if not node:
            return
            
        # Recursively delete all child nodes
        for child in node.child_nodes[:]:  # Create a copy of the list to iterate over
            self.delete_node(child)
        
        # Remove all edges connected to this node
        edges_to_remove = []
        for edge in self.edges[:]:
            if edge.source == node or edge.target == node:
                edges_to_remove.append(edge)
        
        for edge in edges_to_remove:
            self.scene.removeItem(edge)
            if edge in self.edges:
                self.edges.remove(edge)
        
        # Remove from parent's child list if it has a parent
        if node.parent_node and node in node.parent_node.child_nodes:
            node.parent_node.child_nodes.remove(node)
        
        # Remove from the scene and nodes list
        self.scene.removeItem(node)
        if node in self.nodes:
            self.nodes.remove(node)
        
        # Don't update the parent node's size when deleting a child
    # This prevents unwanted resizing of parent nodes

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
