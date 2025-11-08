from PyQt5.QtCore import QLineF, Qt, QPointF, QRectF
from PyQt5.QtGui import QPen, QPainterPath, QColor, QBrush, QPainterPathStroker
from PyQt5.QtWidgets import QGraphicsPathItem, QGraphicsItem, QGraphicsEllipseItem, QGraphicsTextItem


class EdgeControlPoint(QGraphicsEllipseItem):
    """A draggable control point for edge connection points"""
    
    def __init__(self, edge, node, is_start=True, parent=None):
        super().__init__(-5, -5, 10, 10, parent)  # 10x10 circle centered at origin
        
        self.edge = edge
        self.node = node
        self.is_start = is_start
        
        # Offset from node center (in node's local coordinates)
        self.offset = QPointF(0, 0)
        
        # Colors
        self.normal_color = QColor(100, 150, 200)
        self.hover_color = QColor(150, 200, 255)
        
        # Set appearance
        self.setBrush(QBrush(self.normal_color))
        self.setPen(QPen(Qt.white, 1))
        
        # Set flags
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        
        self.setZValue(2000)  # Draw above everything, including selected nodes (which use 1000)
        
        # Update position
        self.update_position()
    
    def update_position(self):
        """Update the position of the control point"""
        # Get the border intersection point
        border_pos = self.edge.get_connection_point(self.is_start)
        self.setPos(border_pos)
    
    def hoverEnterEvent(self, event):
        """Handle hover enter"""
        self.setBrush(QBrush(self.hover_color))
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Handle hover leave"""
        self.setBrush(QBrush(self.normal_color))
        super().hoverLeaveEvent(event)
    
    def contextMenuEvent(self, event):
        """Handle right-click context menu"""
        from PyQt5.QtWidgets import QMenu
        menu = QMenu()
        delete_action = menu.addAction("Delete Edge")
        action = menu.exec_(event.screenPos())
        
        if action == delete_action:
            self.edge.delete_edge()
        
        event.accept()
    
    def itemChange(self, change, value):
        """Handle item changes"""
        if change == QGraphicsItem.ItemPositionChange:
            # Constrain the point to the node's border
            new_pos = value
            
            # Convert to node's local coordinates
            local_pos = self.node.mapFromScene(new_pos)
            
            # Get the border intersection
            if hasattr(self.node, 'get_border_intersection'):
                border_intersection = self.node.get_border_intersection(local_pos)
                
                # Convert back to scene coordinates
                scene_pos = self.node.mapToScene(border_intersection)
                
                # Update the offset
                self.offset = border_intersection
                
                return scene_pos
            else:
                return new_pos
        
        if change == QGraphicsItem.ItemPositionHasChanged:
            # Update the edge path
            self.edge.update_path()
        
        return super().itemChange(change, value)


class EdgeTitleItem(QGraphicsTextItem):
    """Text item for edge title that supports double-click editing"""
    def __init__(self, edge):
        super().__init__("")
        self.edge = edge
        self._orig_text = ""
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setDefaultTextColor(QColor(255, 255, 255))
        self.setZValue(10)
        # Keep text size constant when zooming
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

    def mouseDoubleClickEvent(self, event):
        self._orig_text = self.toPlainText()
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus(Qt.MouseFocusReason)
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        # Commit changes on focus out
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.edge.set_title(self.toPlainText())
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter):
            self.clearFocus()
            event.accept()
            return
        if key == Qt.Key_Escape:
            self.setPlainText(self._orig_text)
            self.clearFocus()
            event.accept()
            return
        super().keyPressEvent(event)


class WaypointControlPoint(QGraphicsEllipseItem):
    """A draggable control point for adjusting edge waypoints"""
    
    def __init__(self, edge, parent=None):
        super().__init__(-5, -5, 10, 10, parent)  # 10x10 circle
        
        self.edge = edge
        
        # Colors
        self.normal_color = QColor(255, 150, 100)  # Orange
        self.hover_color = QColor(255, 200, 150)
        
        # Set appearance
        self.setBrush(QBrush(self.normal_color))
        self.setPen(QPen(Qt.white, 1))
        
        # Set flags
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        
        self.setZValue(2000)  # Draw above everything, including selected nodes (which use 1000)
    
    def hoverEnterEvent(self, event):
        """Handle hover enter"""
        self.setBrush(QBrush(self.hover_color))
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Handle hover leave"""
        self.setBrush(QBrush(self.normal_color))
        super().hoverLeaveEvent(event)
    
    def contextMenuEvent(self, event):
        """Handle right-click context menu"""
        from PyQt5.QtWidgets import QMenu
        menu = QMenu()
        delete_action = menu.addAction("Delete Edge")
        action = menu.exec_(event.screenPos())
        
        if action == delete_action:
            self.edge.delete_edge()
        
        event.accept()
    
    def itemChange(self, change, value):
        """Handle item changes"""
        if change == QGraphicsItem.ItemPositionChange:
            # Constrain movement to only horizontal (X-axis)
            new_pos = value
            # Keep the Y position fixed, only allow X to change
            if hasattr(self, 'fixed_y'):
                new_pos.setY(self.fixed_y)
            
            # Calculate the ratio (0-1) of the waypoint position between start and end
            if self.edge._start_node and self.edge._end_node:
                start_pos = self.edge.get_connection_point(is_start=True)
                end_pos = self.edge.get_connection_point(is_start=False)
                dx = end_pos.x() - start_pos.x()
                if abs(dx) > 0.1:  # Avoid division by zero
                    # Calculate ratio based on new position
                    ratio = (new_pos.x() - start_pos.x()) / dx
                    # Clamp ratio between 0 and 1
                    ratio = max(0.0, min(1.0, ratio))
                    self.edge.waypoint_ratio = ratio
            
            return new_pos
        
        if change == QGraphicsItem.ItemPositionHasChanged:
            # Update the edge path
            self.edge.update_path()
        
        return super().itemChange(change, value)


class Edge(QGraphicsPathItem):
    """An edge with orthogonal (90-degree) routing between nodes"""
    _title_seq = 1  # class-level counter for default titles
    
    def __init__(self, start_pos, parent=None):
        super().__init__(parent)
        self._start_pos = start_pos
        self._end_pos = start_pos
        self._start_node = None
        self._end_node = None
        
        # Control points for dragging
        self.start_control = None
        self.end_control = None
        self.waypoint_control = None
        
        # Custom offsets (in node's local coordinates)
        self.start_offset = None
        self.end_offset = None
        self.custom_mid_x = None  # Custom X position for the vertical segment
        self.waypoint_ratio = 0.5  # Ratio (0-1) of waypoint position between start and end X
        
        # Edge styling
        self.edge_color = QColor(100, 150, 200)  # Light blue
        self.selected_color = QColor(255, 140, 0)  # Orange (match node selection)
        # Pre-create pens for normal and selected states
        self.normal_pen = QPen(self.edge_color, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        self.selected_pen = QPen(self.selected_color, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        # Set initial pen
        self.setPen(self.normal_pen)
        # Arrow styling
        self.arrow_size = 10.0
        self._arrow_end = None
        self._arrow_prev = None

        # Title label
        self.title_item = EdgeTitleItem(self)
        self.title_item.setParentItem(self)
        self.setZValue(-1)  # Draw below nodes
        self.setFlag(QGraphicsPathItem.ItemIsSelectable)
        self.setFlag(QGraphicsPathItem.ItemIsFocusable)  # Allow keyboard events
        self.setAcceptHoverEvents(True)
        
        # Create a wider invisible stroke for easier selection
        self._selection_pen = QPen(Qt.transparent, 15)  # 15px wide invisible hit area
        
        self.update_path()
    
    def set_end_pos(self, pos):
        """Set the end position for temporary edge drawing"""
        self._end_pos = pos
        self.update_path()
    
    def set_start_pos(self, pos):
        """Set the start position"""
        self._start_pos = pos
        self.update_path()
    
    def set_start_node(self, node):
        """Set the start node and register with it"""
        if self._start_node is not None and hasattr(self._start_node, 'connected_edges'):
            if self in self._start_node.connected_edges:
                self._start_node.connected_edges.remove(self)
        
        self._start_node = node
        if node is not None and hasattr(node, 'connected_edges'):
            if self not in node.connected_edges:
                node.connected_edges.append(self)
        self.update_path()
    
    def set_end_node(self, node):
        """Set the end node and register with it"""
        if self._end_node is not None and hasattr(self._end_node, 'connected_edges'):
            if self in self._end_node.connected_edges:
                self._end_node.connected_edges.remove(self)
        
        self._end_node = node
        if node is not None and hasattr(node, 'connected_edges'):
            if self not in node.connected_edges:
                node.connected_edges.append(self)
        self.update_path()
    
    def create_control_points(self, scene):
        """Create draggable control points for the edge"""
        # Only create if they don't already exist
        if self.start_control is None:
            self.start_control = EdgeControlPoint(self, self._start_node, is_start=True)
            scene.addItem(self.start_control)
        
        if self.end_control is None:
            self.end_control = EdgeControlPoint(self, self._end_node, is_start=False)
            scene.addItem(self.end_control)
        
        if self.waypoint_control is None:
            self.waypoint_control = WaypointControlPoint(self)
            scene.addItem(self.waypoint_control)
        
        # Ensure control points (especially the orange waypoint) are positioned immediately
        # rather than waiting for the next user interaction to trigger an update.
        self.update_path()
        # Set a default title once the edge is fully connected
        self._ensure_default_title()
    
    def get_connection_point(self, is_start):
        """Get the connection point for start or end of edge"""
        if is_start:
            node = self._start_node
            offset = self.start_offset
            control = self.start_control
            other_node = self._end_node
        else:
            node = self._end_node
            offset = self.end_offset
            control = self.end_control
            other_node = self._start_node
        
        # If we have a custom offset from control point, use it
        if control and control.offset:
            offset = control.offset
            if is_start:
                self.start_offset = offset
            else:
                self.end_offset = offset
        
        # If we have a custom offset, use it
        if offset is not None:
            return node.mapToScene(offset)
        
        # Otherwise, calculate based on the other node's position
        if other_node:
            other_center = other_node.scenePos()
        else:
            # Use end_pos if no other node
            other_center = self._end_pos if is_start else self._start_pos
        
        local_other = node.mapFromScene(other_center)
        if hasattr(node, 'get_border_intersection'):
            intersection = node.get_border_intersection(local_other)
            return node.mapToScene(intersection)
        else:
            return node.scenePos()
    
    def update_path(self):
        """Update the edge path with orthogonal routing"""
        path = QPainterPath()
        
        # Get start and end positions
        start_pos = self._start_pos
        end_pos = self._end_pos
        
        # Use node positions if connected
        if self._start_node is not None:
            start_pos = self._start_node.scenePos()
        
        if self._end_node is not None:
            end_pos = self._end_node.scenePos()
        
        # Reset arrow reference points
        self._arrow_end = None
        self._arrow_prev = None
        # Only use orthogonal routing if BOTH nodes are connected
        if self._start_node is not None and self._end_node is not None:
            # ORTHOGONAL ROUTING (both nodes connected)
            # Get the actual start and end positions using custom offsets if available
            actual_start_pos = self.get_connection_point(is_start=True)
            actual_end_pos = self.get_connection_point(is_start=False)
            
            # Calculate waypoints for 90-degree routing
            dx = actual_end_pos.x() - actual_start_pos.x()
            
            # Calculate mid_x based on ratio between start and end
            # This makes the waypoint move proportionally when endpoints change
            mid_x = actual_start_pos.x() + dx * self.waypoint_ratio
            
            waypoint1 = QPointF(mid_x, actual_start_pos.y())
            waypoint2 = QPointF(mid_x, actual_end_pos.y())
            
            # Draw orthogonal path: horizontal -> vertical -> horizontal
            path.moveTo(actual_start_pos)
            path.lineTo(waypoint1)
            path.lineTo(waypoint2)
            path.lineTo(actual_end_pos)
            # Arrow should follow the last segment (waypoint2 -> end)
            self._arrow_prev = waypoint2
            self._arrow_end = actual_end_pos
            
            # Update control point positions if they exist
            if self.start_control:
                self.start_control.update_position()
            if self.end_control:
                self.end_control.update_position()
            
            # Position and update waypoint control
            if self.waypoint_control:
                # Calculate the Y position for the waypoint
                waypoint_mid_y = (actual_start_pos.y() + actual_end_pos.y()) / 2
                self.waypoint_control.fixed_y = waypoint_mid_y
                
                # X position is already calculated as mid_x using the ratio
                # Always update the position
                waypoint_pos = QPointF(mid_x, waypoint_mid_y)
                self.waypoint_control.setPos(waypoint_pos)
        else:
            # STRAIGHT LINE (temporary edge while dragging)
            actual_start_pos = start_pos
            if self._start_node is not None and hasattr(self._start_node, 'get_border_intersection'):
                local_end = self._start_node.mapFromScene(end_pos)
                local_intersection = self._start_node.get_border_intersection(local_end)
                actual_start_pos = self._start_node.mapToScene(local_intersection)
            
            # Draw straight line
            path.moveTo(actual_start_pos)
            path.lineTo(end_pos)
            self._arrow_prev = actual_start_pos
            self._arrow_end = end_pos
        
        self.setPath(path)
        # Update title position along the path (midpoint)
        self.update_title_position()
        
        # Derive arrow direction from the final segment of the path to ensure
        # it always points toward the connecting node's border, regardless of
        # how waypoints were computed.
        try:
            p = self.path()
            count = p.elementCount()
            if count >= 2:
                end_el = p.elementAt(count - 1)
                prev_el = p.elementAt(count - 2)
                self._arrow_end = QPointF(end_el.x, end_el.y)
                self._arrow_prev = QPointF(prev_el.x, prev_el.y)
        except Exception:
            # If for any reason we can't read the path elements, keep previous values
            pass
    
    def itemChange(self, change, value):
        """Handle item changes"""
        # No color change on selection - edge stays light blue
        return super().itemChange(change, value)

    def set_title(self, text: str):
        """Set the edge title text"""
        self.title_item.setPlainText(text)
        self.update_title_position()

    def _ensure_default_title(self):
        """Assign a default title like 'Edge N' after connection if empty."""
        if self._start_node is not None and self._end_node is not None:
            if not self.title_item.toPlainText():
                self.set_title(f"Edge {Edge._title_seq}")
                Edge._title_seq += 1

    def update_title_position(self):
        """Reposition the title at the midpoint of the path with a small offset"""
        p = self.path()
        if p.isEmpty():
            return
        try:
            mid = p.pointAtPercent(0.5)
        except Exception:
            return
        # Center the text horizontally and place slightly above the path
        br = self.title_item.boundingRect()
        offset_y = 6
        self.title_item.setPos(mid.x() - br.width() / 2.0, mid.y() - br.height() - offset_y)
    
    def mousePressEvent(self, event):
        """Handle mouse press to set focus"""
        self.setFocus()
        super().mousePressEvent(event)
    
    def contextMenuEvent(self, event):
        """Handle right-click context menu on edge"""
        from PyQt5.QtWidgets import QMenu, QInputDialog
        menu = QMenu()
        edit_title_action = menu.addAction("Edit Title…")
        delete_action = menu.addAction("Delete Edge")
        action = menu.exec_(event.screenPos())
        
        if action == edit_title_action:
            current = self.title_item.toPlainText()
            text, ok = QInputDialog.getText(None, "Edit Edge Title", "Title:", text=current)
            if ok:
                self.set_title(text)
        elif action == delete_action:
            self.delete_edge()
        
        event.accept()
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        # No keyboard deletion - use toolbar button instead
        super().keyPressEvent(event)
    
    def delete_edge(self):
        """Delete this edge and clean up"""
        # Remove from connected nodes
        if self._start_node and hasattr(self._start_node, 'connected_edges'):
            if self in self._start_node.connected_edges:
                self._start_node.connected_edges.remove(self)
        
        if self._end_node and hasattr(self._end_node, 'connected_edges'):
            if self in self._end_node.connected_edges:
                self._end_node.connected_edges.remove(self)
        
        # Remove control points
        if self.start_control and self.start_control.scene():
            self.start_control.scene().removeItem(self.start_control)
        if self.end_control and self.end_control.scene():
            self.end_control.scene().removeItem(self.end_control)
        if self.waypoint_control and self.waypoint_control.scene():
            self.waypoint_control.scene().removeItem(self.waypoint_control)
        
        # Remove from scene
        if self.scene():
            self.scene().removeItem(self)
    
    def shape(self):
        """Return a wider shape for easier selection"""
        # Create a path stroker with wider pen for hit detection
        stroker = QPainterPathStroker()
        stroker.setWidth(15)  # 15px wide hit area
        stroker.setCapStyle(Qt.RoundCap)
        stroker.setJoinStyle(Qt.RoundJoin)
        return stroker.createStroke(self.path())
    
    def paint(self, painter, option, widget=None):
        """Custom painting"""
        # Switch edge color when selected
        if self.isSelected():
            painter.setPen(self.selected_pen)
            # Keep title white
            self.title_item.setDefaultTextColor(QColor(255, 255, 255))
        else:
            painter.setPen(self.normal_pen)
            # Keep title white
            self.title_item.setDefaultTextColor(QColor(255, 255, 255))
        painter.drawPath(self.path())
        
        # Draw arrow head at the end of the edge
        if self._arrow_end is not None and self._arrow_prev is not None:
            end = self._arrow_end
            prev = self._arrow_prev
            dx = end.x() - prev.x()
            dy = end.y() - prev.y()
            length = (dx*dx + dy*dy) ** 0.5
            if length > 0.0001:
                # Normalize direction
                ux = dx / length
                uy = dy / length
                # Base of arrow triangle
                base_x = end.x() - ux * self.arrow_size
                base_y = end.y() - uy * self.arrow_size
                # Perpendicular vector
                px = -uy
                py = ux
                width = self.arrow_size * 0.6
                left_x = base_x + px * width
                left_y = base_y + py * width
                right_x = base_x - px * width
                right_y = base_y - py * width
                # Use same color as current pen
                painter.setBrush(painter.pen().color())
                from PyQt5.QtGui import QPolygonF
                polygon = QPolygonF([end, QPointF(left_x, left_y), QPointF(right_x, right_y)])
                painter.drawPolygon(polygon)
