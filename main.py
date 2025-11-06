import sys
import math
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, 
                             QMainWindow, QVBoxLayout, QWidget, QGraphicsItem,
                             QGraphicsRectItem, QGraphicsTextItem, QGraphicsPathItem,
                             QGraphicsEllipseItem, QMenu, QAction, QLineEdit)
from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF
from PyQt5.QtGui import QPainter, QPen, QColor, QWheelEvent, QBrush, QFont, QPainterPath

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
        
    def drawBackground(self, painter, rect):
        """Draw the background grid"""
        # Call the parent method to draw the default background
        super().drawBackground(painter, rect)
        
        # Set up the pen for minor grid lines
        minor_pen = QPen(QColor(200, 200, 200, 100))  # Light gray with transparency
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
            
        # Draw major grid lines
        major_pen = QPen(QColor(150, 150, 150, 150))  # Slightly darker gray
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

    def contextMenuEvent(self, event):
        """Handle context menu events"""
        item = self.itemAt(event.pos())
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
        # Delete selected items when Delete or Backspace is pressed
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            selected_items = self.scene.selectedItems()
            for item in selected_items:
                if isinstance(item, Node):
                    self.delete_node(item)
        else:
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
            
        # Handle node selection and movement
        if event.button() == Qt.LeftButton:
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
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        super().mouseReleaseEvent(event)


class ConnectionPoint(QGraphicsEllipseItem):
    def __init__(self, node, position, index, parent=None):
        size = 8
        super().__init__(-size/2, -size/2, size, size, parent)
        self.node = node
        self.position = position  # 'top', 'right', 'bottom', 'left'
        self.index = index
        self.setBrush(QBrush(Qt.white))
        self.setPen(QPen(Qt.black, 1))
        self.setZValue(100)  # Make sure connection points are above nodes
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.setVisible(False)  # Hidden by default, shown on hover
        
    def itemChange(self, change, value):
        # No edge-related updates needed anymore
        return super().itemChange(change, value)
        
    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(Qt.red))
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(Qt.white))
        super().hoverLeaveEvent(event)


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
        
        # Hover dot
        self.hover_dot = None
        
        # Connection points
        self.connection_points = []
        self.connection_positions = ['top', 'right', 'bottom', 'left']
        
        # Set position if provided
        if pos is not None:
            self.setPos(pos)
            
        # Node colors
        self.title_color = QColor("#3498db")  # Light blue color for title bar
        self.bg_color = QColor("#2c3e50")
        self.border_color = QColor("#3498db")  # Same light blue as title
        self.border_width = 5  # Border width set to 5 pixels
        self.text_color = QColor("#ecf0f1")
        
        # Node title
        self.title_item = QGraphicsTextItem(self.title, self)
        self.title_item.setDefaultTextColor(self.text_color)
        self.title_item.setPos(self.padding, (self.title_height - self.title_item.boundingRect().height()) / 2)
        
        # Set the initial size and update the inner rect
        self.update_size()
    
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
        """Update the position of the resize handle and connection points"""
        h = self.resize_handle_size
        r = self.rect
        self.resize_handle = QRectF(r.right() - h, r.bottom() - h, h, h)
        
        # Update connection points
        if not self.connection_points:
            self.create_connection_points()
        
        # Update positions of existing connection points
        for point in self.connection_points:
            self.position_connection_point(point)
    
    def create_connection_points(self):
        """Create connection points for the node"""
        # Clear existing points
        for point in self.connection_points:
            if point.scene():
                point.scene().removeItem(point)
        self.connection_points = []
        
        # Create new connection points
        for i, pos in enumerate(self.connection_positions):
            point = ConnectionPoint(self, pos, i, self)
            self.connection_points.append(point)
            if self.scene():
                self.scene().addItem(point)
            self.position_connection_point(point)
    
    def position_connection_point(self, point):
        """Position a connection point based on its position type"""
        rect = self.rect
        if point.position == 'top':
            x = rect.left() + (rect.width() / (len(self.connection_positions) + 1)) * (point.index + 1)
            y = rect.top()
        elif point.position == 'right':
            x = rect.right()
            y = rect.top() + (rect.height() / (len(self.connection_positions) + 1)) * (point.index + 1)
        elif point.position == 'bottom':
            x = rect.left() + (rect.width() / (len(self.connection_positions) + 1)) * (point.index + 1)
            y = rect.bottom()
        else:  # left
            x = rect.left()
            y = rect.top() + (rect.height() / (len(self.connection_positions) + 1)) * (point.index + 1)
            
        point.setPos(self.mapToScene(x, y))
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSceneHasChanged and value:
            # Add connection points to scene
            if self.scene():
                self.create_connection_points()
        elif change == QGraphicsItem.ItemPositionChange and self.scene():
            # Update connection points when node moves
            for point in self.connection_points:
                self.position_connection_point(point)
        return super().itemChange(change, value)
    
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
        """Handle hover events for the resize handle and show hover dot on border"""
        if self.isSelected() and self.is_over_resize_handle(event.pos()):
            self.setCursor(Qt.SizeFDiagCursor)
            self._hide_hover_dot()
        else:
            self.setCursor(Qt.ArrowCursor)
            # Get cursor position in item coordinates
            item_pos = event.pos()
            # Get the border intersection in item coordinates
            border_point = self.get_border_intersection(item_pos)
            # Convert to scene coordinates for positioning the dot
            scene_border_point = self.mapToScene(border_point)
            self._show_hover_dot(scene_border_point)
        super().hoverMoveEvent(event)
        
    def hoverLeaveEvent(self, event):
        """Hide hover dot when leaving the node"""
        self._hide_hover_dot()
        super().hoverLeaveEvent(event)
        
    def _show_hover_dot(self, pos):
        """Show the hover dot at the specified position in scene coordinates"""
        if not self.scene():
            return
            
        # Remove existing hover dot if it exists
        self._hide_hover_dot()
        
        try:
            # Calculate the border point in item coordinates
            item_pos = self.mapFromScene(pos)
            border_point = self.get_border_intersection(item_pos)
            scene_pos = self.mapToScene(border_point)
            
            # Create a new hover dot
            self.hover_dot = QGraphicsEllipseItem(-8, -8, 16, 16)
            self.hover_dot.setBrush(QBrush(QColor(255, 0, 0, 200)))  # Semi-transparent red
            self.hover_dot.setPen(QPen(Qt.white, 1.5))  # White border
            self.hover_dot.setZValue(1000)  # Make sure it's on top
            self.hover_dot.setPos(scene_pos)
            
            # Store the relative position on the border (0-1 range for x and y)
            rect = self.boundingRect()
            rel_x = (border_point.x() - rect.left()) / rect.width()
            rel_y = (border_point.y() - rect.top()) / rect.height()
            self.hover_dot.setData(0, (rel_x, rel_y))  # Store relative position
            
            # Add to scene
            self.scene().addItem(self.hover_dot)
            self.hover_dot.show()
            
        except Exception as e:
            print(f"Error showing hover dot: {e}")
            self._hide_hover_dot()
    
    def _hide_hover_dot(self):
        """Hide the hover dot"""
        if hasattr(self, 'hover_dot') and self.hover_dot is not None:
            try:
                if self.scene() and self.hover_dot in self.scene().items():
                    self.hover_dot.hide()
                    self.scene().removeItem(self.hover_dot)
            except Exception as e:
                print(f"Error hiding hover dot: {e}")
            finally:
                self.hover_dot = None
        
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
            
    def itemChange(self, change, value):
        """Handle item changes to update marked dots"""
        if change == QGraphicsItem.ItemPositionHasChanged or \
           change == QGraphicsItem.ItemTransformHasChanged:
            if hasattr(self, 'marked_dots'):
                self._update_marked_dots_position()
        return super().itemChange(change, value)
        
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
        self.setWindowTitle("Node Editor")
        self.setGeometry(100, 100, 1200, 800)
        
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
    
    def createMenu(self):
        # Create menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
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
