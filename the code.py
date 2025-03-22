from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, 
                         QGraphicsLineItem, QGraphicsTextItem, QGraphicsItem, QPushButton, QVBoxLayout, 
                         QWidget, QHBoxLayout, QColorDialog, QFontDialog, QMenu, QAction, QInputDialog,
                         QToolBar, QMainWindow, QFileDialog, QGraphicsRectItem)
from PyQt5.QtGui import QPainter, QBrush, QPen, QFont, QColor, QIcon, QPixmap, QImage
from PyQt5.QtCore import Qt, QPointF, QRectF, QBuffer, QByteArray, QIODevice
import sys
import json
import os
import random

class MindMapNode(QGraphicsEllipseItem):
    def __init__(self, x, y, text="New Idea", color=Qt.yellow, node_type="ellipse", width=100, height=60):
        super().__init__(0, 0, width, height)
        self.width = width
        self.height = height
        self.node_type = node_type
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.black, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setPos(x, y)
        
        # For rectangular nodes
        if node_type == "rectangle":
            self.rect_item = QGraphicsRectItem(0, 0, width, height, self)
            self.rect_item.setBrush(QBrush(color))
            self.rect_item.setPen(QPen(Qt.black, 2))
            self.setRect(0, 0, 0, 0)  # Hide the ellipse
        
        # Center text in the node
        self.text_item = QGraphicsTextItem(text, self)
        self.text_item.setFont(QFont("Arial", 10))
        self.text_item.setDefaultTextColor(Qt.black)
        self.text_item.setTextWidth(width - 20)
        # Center the text
        text_x = -self.text_item.boundingRect().width() / 2 + width / 2
        text_y = -self.text_item.boundingRect().height() / 2 + height / 2
        self.text_item.setPos(text_x, text_y)
        self.text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        
        self.connections = []  # Store connected lines and nodes
        self.parent_connection = None  # Reference to parent connection
        self.level = 0  # Hierarchy level
        self.children = []  # Child nodes
        self.collapsed = False  # For collapsing/expanding subtrees
        self.notes = ""  # For storing additional notes
        
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # Update all connected lines
            for line, other_node in self.connections:
                self.update_connection_line(line, self, other_node)
            
            # If this node has a parent connection, update it
            if self.parent_connection and self.parent_connection[0]:
                parent_line, parent_node = self.parent_connection
                self.update_connection_line(parent_line, parent_node, self)
                
            # Move all children recursively
            if hasattr(self, 'prev_pos') and self.children:
                delta_x = value.x() - self.prev_pos.x()
                delta_y = value.y() - self.prev_pos.y()
                self.move_children(delta_x, delta_y)
            
            # Store the position for next time
            self.prev_pos = value
            
        return super().itemChange(change, value)

    def update_connection_line(self, line, from_node, to_node):
        # Calculate better connection points based on node shapes
        if from_node.node_type == "ellipse":
            start_point = self.calculate_ellipse_edge_point(from_node, to_node)
        else:
            start_point = self.calculate_rectangle_edge_point(from_node, to_node)
            
        if to_node.node_type == "ellipse":
            end_point = self.calculate_ellipse_edge_point(to_node, from_node)
        else:
            end_point = self.calculate_rectangle_edge_point(to_node, from_node)
            
        line.setLine(start_point.x(), start_point.y(), end_point.x(), end_point.y())
    
    def calculate_ellipse_edge_point(self, ellipse_node, target_node):
        # Calculate the point on the edge of the ellipse that intersects with the line to target
        ellipse_center = ellipse_node.scenePos() + QPointF(ellipse_node.width/2, ellipse_node.height/2)
        target_center = target_node.scenePos() + QPointF(target_node.width/2, target_node.height/2)
        
        # Vector from ellipse center to target
        dx = target_center.x() - ellipse_center.x()
        dy = target_center.y() - ellipse_center.y()
        
        # Normalize the vector
        length = (dx**2 + dy**2)**0.5
        if length == 0:
            return ellipse_center
            
        dx, dy = dx/length, dy/length
        
        # Calculate the point on the ellipse edge
        # Simple approximation: use the semi-major and semi-minor axes
        a = ellipse_node.width / 2
        b = ellipse_node.height / 2
        
        # Parametric equation approximation
        t = min(abs(a/dx) if dx != 0 else float('inf'), 
                abs(b/dy) if dy != 0 else float('inf'))
        
        edge_x = ellipse_center.x() + dx * t
        edge_y = ellipse_center.y() + dy * t
        
        return QPointF(edge_x, edge_y)
    
    def calculate_rectangle_edge_point(self, rect_node, target_node):
        # Calculate the point on the edge of the rectangle that intersects with the line to target
        rect_center = rect_node.scenePos() + QPointF(rect_node.width/2, rect_node.height/2)
        target_center = target_node.scenePos() + QPointF(target_node.width/2, target_node.height/2)
        
        # Rectangle bounds
        left = rect_center.x() - rect_node.width/2
        right = rect_center.x() + rect_node.width/2
        top = rect_center.y() - rect_node.height/2
        bottom = rect_center.y() + rect_node.height/2
        
        # Calculate intersection with rectangle edges
        dx = target_center.x() - rect_center.x()
        dy = target_center.y() - rect_center.y()
        
        # Prevent division by zero
        if dx == 0:
            return QPointF(rect_center.x(), top if dy < 0 else bottom)
        if dy == 0:
            return QPointF(left if dx < 0 else right, rect_center.y())
        
        # Calculate intersections with all four sides
        tx1 = (left - rect_center.x()) / dx
        tx2 = (right - rect_center.x()) / dx
        ty1 = (top - rect_center.y()) / dy
        ty2 = (bottom - rect_center.y()) / dy
        
        # Find the relevant intersection point
        t = min(max(tx1, tx2), max(ty1, ty2))
        
        return QPointF(rect_center.x() + dx * t, rect_center.y() + dy * t)
    
    def move_children(self, delta_x, delta_y):
        for child in self.children:
            current_pos = child.pos()
            child.setPos(current_pos.x() + delta_x, current_pos.y() + delta_y)
    
    def toggle_collapse(self):
        self.collapsed = not self.collapsed
        for child in self.children:
            child.setVisible(not self.collapsed)
            # If expanding and child was collapsed, keep its children hidden
            if not self.collapsed and child.collapsed:
                self.hide_all_children(child)
            
            # If this child has connections, toggle their visibility too
            for line, _ in child.connections:
                line.setVisible(not self.collapsed)
            
            # If this child has a parent connection, toggle its visibility
            if child.parent_connection and child.parent_connection[0]:
                child.parent_connection[0].setVisible(not self.collapsed)
    
    def hide_all_children(self, node):
        for child in node.children:
            child.setVisible(False)
            # Hide connection to parent
            if child.parent_connection and child.parent_connection[0]:
                child.parent_connection[0].setVisible(False)
            # Hide connections to others
            for line, _ in child.connections:
                line.setVisible(False)
            # Recursively hide grandchildren
            self.hide_all_children(child)
            
    def contextMenuEvent(self, event):
        menu = QMenu()
        
        # Add menu items
        change_color_action = menu.addAction("Change Color")
        change_shape_action = menu.addAction("Toggle Shape")
        change_font_action = menu.addAction("Change Font")
        add_child_action = menu.addAction("Add Child Node")
        add_notes_action = menu.addAction("Add/Edit Notes")
        
        if self.children:
            if self.collapsed:
                collapse_action = menu.addAction("Expand Subtree")
            else:
                collapse_action = menu.addAction("Collapse Subtree")
        else:
            collapse_action = None
        
        delete_action = menu.addAction("Delete Node")
        
        # Show the menu and get the selected action
        action = menu.exec_(event.screenPos())
        
        # Handle the menu actions
        if action == change_color_action:
            color = QColorDialog.getColor()
            if color.isValid():
                self.setBrush(QBrush(color))
                if hasattr(self, 'rect_item') and self.rect_item:
                    self.rect_item.setBrush(QBrush(color))
        
        elif action == change_shape_action:
            if self.node_type == "ellipse":
                self.node_type = "rectangle"
                self.rect_item = QGraphicsRectItem(0, 0, self.width, self.height, self)
                self.rect_item.setBrush(self.brush())
                self.rect_item.setPen(self.pen())
                self.setRect(0, 0, 0, 0)  # Hide the ellipse
            else:
                self.node_type = "ellipse"
                if hasattr(self, 'rect_item') and self.rect_item:
                    self.scene().removeItem(self.rect_item)
                    self.rect_item = None
                self.setRect(0, 0, self.width, self.height)
            
            # Update connections
            for line, other_node in self.connections:
                self.update_connection_line(line, self, other_node)
            if self.parent_connection and self.parent_connection[0]:
                parent_line, parent_node = self.parent_connection
                self.update_connection_line(parent_line, parent_node, self)
        
        elif action == change_font_action:
            font, ok = QFontDialog.getFont(self.text_item.font())
            if ok:
                self.text_item.setFont(font)
        
        elif action == add_child_action:
            view = self.scene().views()[0]
            view.add_child_node(self)
        
        elif action == add_notes_action:
            text, ok = QInputDialog.getMultiLineText(None, "Node Notes", 
                                           "Enter notes for this node:", self.notes)
            if ok:
                self.notes = text
        
        elif collapse_action and action == collapse_action:
            self.toggle_collapse()
        
        elif action == delete_action:
            self.delete_node()
    
    def delete_node(self):
        # Delete connections
        for line, other_node in self.connections:
            # Remove this connection from the other node's list
            other_node.connections = [(l, n) for l, n in other_node.connections if n != self]
            self.scene().removeItem(line)
        
        # Delete parent connection if it exists
        if self.parent_connection and self.parent_connection[0]:
            parent_line, parent_node = self.parent_connection
            # Remove this node from parent's children list
            parent_node.children.remove(self)
            self.scene().removeItem(parent_line)
        
        # Delete all children recursively
        for child in list(self.children):  # Use list to avoid modification during iteration
            child.delete_node()
        
        # Finally remove this node
        self.scene().removeItem(self)

class MindMapView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(-5000, -5000, 10000, 10000)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.scale_factor = 1.0
        
        self.nodes = []
        self.selected_nodes = []  # Stores selected nodes for connecting
        self.root_node = None
        self.last_mouse_pos = None
        self.connection_mode = "automatic"  # Can be "automatic", "manual", or "hierarchical"
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def add_node(self):
        # Get the center of the current view
        view_center = self.mapToScene(self.viewport().rect().center())
        x, y = view_center.x(), view_center.y()
        
        node = MindMapNode(x, y)
        self.scene.addItem(node)
        self.nodes.append(node)
        
        # If no root node exists, set this as the root
        if not self.root_node:
            self.root_node = node
            # Make the root node a bit special - different color and size
            node.setBrush(QBrush(Qt.green))
            node.setRect(0, 0, 120, 80)
            node.width = 120
            node.height = 80
            
            # Update text position
            text_x = -node.text_item.boundingRect().width() / 2 + node.width / 2
            text_y = -node.text_item.boundingRect().height() / 2 + node.height / 2
            node.text_item.setPos(text_x, text_y)
            
            # Set default text for root node
            node.text_item.setPlainText("Main Topic")
        
        return node
    
    def add_child_node(self, parent_node, text="New Idea"):
        # Calculate position for the new node
        parent_pos = parent_node.scenePos()
        
        # Determine if we should place it horizontally or vertically based on level
        if parent_node.level == 0:  # Root level, place children horizontally
            offset_x = 200
            offset_y = (len(parent_node.children) - len(parent_node.children) / 2) * 100
            x = parent_pos.x() + offset_x
            y = parent_pos.y() + offset_y
        else:  # Non-root level, place children vertically in a cascading manner
            offset_x = 180
            offset_y = 80 + len(parent_node.children) * 20
            x = parent_pos.x() + offset_x
            y = parent_pos.y() + offset_y
        
        # Create the new node
        child_node = MindMapNode(x, y, text)
        child_node.level = parent_node.level + 1
        
        # Make visually distinct based on level
        color_map = {
            0: Qt.green,
            1: Qt.yellow,
            2: QColor(255, 200, 100),  # Orange
            3: QColor(100, 200, 255),  # Light blue
            4: QColor(200, 150, 255),  # Purple
        }
        
        # If level is beyond our map, use a random color
        if child_node.level >= len(color_map):
            color = QColor(random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
        else:
            color = color_map[child_node.level]
        
        child_node.setBrush(QBrush(color))
        
        # Adjust size based on level
        if child_node.level == 1:
            width, height = 100, 60
        else:
            width, height = 90, 50
        
        child_node.setRect(0, 0, width, height)
        child_node.width = width
        child_node.height = height
        
        # Update text position
        text_x = -child_node.text_item.boundingRect().width() / 2 + width / 2
        text_y = -child_node.text_item.boundingRect().height() / 2 + height / 2
        child_node.text_item.setPos(text_x, text_y)
        
        self.scene.addItem(child_node)
        self.nodes.append(child_node)
        
        # Connect to parent
        line = QGraphicsLineItem()
        line.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        self.scene.addItem(line)
        
        # Update line position
        child_node.update_connection_line(line, parent_node, child_node)
        
        # Set up parent-child relationship
        parent_node.children.append(child_node)
        child_node.parent_connection = (line, parent_node)
        
        # If parent is collapsed, hide the child
        if parent_node.collapsed:
            child_node.setVisible(False)
            line.setVisible(False)
        
        return child_node
    
    def connect_nodes(self):
        if self.connection_mode == "manual" and len(self.selected_nodes) == 2:
            node1, node2 = self.selected_nodes
            line = QGraphicsLineItem()
            line.setPen(QPen(Qt.black, 2, Qt.DashLine))  # Dashed line for non-hierarchical connections
            self.scene.addItem(line)
            
            # Set the line position
            node1.update_connection_line(line, node1, node2)
            
            # Add to connections
            node1.connections.append((line, node2))
            node2.connections.append((line, node1))
            
            self.selected_nodes.clear()
    
    def show_context_menu(self, position):
        # Convert position to scene coordinates
        scene_pos = self.mapToScene(position)
        
        # Check if there's an item at this position
        item = self.scene.itemAt(scene_pos, self.transform())
        
        # If there's no item, show the scene context menu
        if not item or not isinstance(item, MindMapNode):
            menu = QMenu()
            add_node_action = menu.addAction("Add New Node")
            add_central_action = menu.addAction("Add Central Topic")
            
            if self.nodes:  # Only show if there are nodes to arrange
                arrange_action = menu.addAction("Auto-Arrange Nodes")
            else:
                arrange_action = None
                
            action = menu.exec_(self.mapToGlobal(position))
            
            if action == add_node_action:
                node = MindMapNode(scene_pos.x(), scene_pos.y())
                self.scene.addItem(node)
                self.nodes.append(node)
            
            elif action == add_central_action:
                # If there's already a root node, just add a normal node
                if self.root_node:
                    node = MindMapNode(scene_pos.x(), scene_pos.y(), "New Topic")
                else:
                    node = MindMapNode(scene_pos.x(), scene_pos.y(), "Main Topic")
                    node.setBrush(QBrush(Qt.green))
                    node.setRect(0, 0, 120, 80)
                    node.width = 120
                    node.height = 80
                    self.root_node = node
                
                self.scene.addItem(node)
                self.nodes.append(node)
            
            elif arrange_action and action == arrange_action:
                self.auto_arrange_nodes()
    
    def auto_arrange_nodes(self):
        if not self.root_node:
            return
        
        # Reset positions
        self.position_node(self.root_node, 0, 0, 1)
        
        # Center the root node in the view
        self.centerOn(self.root_node)
    
    def position_node(self, node, x, y, level_spacing):
        """Recursively position a node and all its children"""
        node.setPos(x, y)
        
        if not node.children:
            return
        
        # Number of children
        n = len(node.children)
        
        if node.level == 0:  # Root level spacing
            start_angle = -60
            end_angle = 60
            radius = 300
        else:  # Other levels
            start_angle = -50
            end_angle = 50
            radius = 200
        
        # Distribute children in fan/radial layout
        angle_step = (end_angle - start_angle) / (n - 1) if n > 1 else 0
        
        for i, child in enumerate(node.children):
            if n == 1:
                angle = 0  # Single child goes straight out
            else:
                angle = start_angle + i * angle_step
            
            # Convert angle to radians
            rad = angle * 3.14159 / 180
            
            # Calculate new position
            child_x = x + radius * level_spacing * 0.8 * (node.level + 1) * (1/1.5) * (1/level_spacing) * (node.level + 1/2) * (1 if angle >= 0 else -1)
            
            # Adjust vertical positioning based on level and index
            if node.level == 0:
                # For first level, arrange in a semicircle
                child_x = x + radius * level_spacing * (1/level_spacing) * (node.level + 1) * 0.8 * (1 if i > n//2 else -1)
                child_y = y + (i - n//2) * 80
            else:
                # For deeper levels, cascade down
                child_y = y + (i + 1) * 70 * level_spacing
            
            # Update connection line
            if child.parent_connection and child.parent_connection[0]:
                child.update_connection_line(child.parent_connection[0], node, child)
            
            # Recursively position the child's children
            self.position_node(child, child_x, child_y, level_spacing * 0.8)
    
    def mousePressEvent(self, event):
        # Store the current position for use in mouseReleaseEvent
        self.last_mouse_pos = self.mapToScene(event.pos())
        
        item = self.itemAt(event.pos())
        if isinstance(item, MindMapNode) and event.button() == Qt.LeftButton:
            # If in manual connection mode, handle node selection
            if self.connection_mode == "manual":
                if item not in self.selected_nodes:
                    self.selected_nodes.append(item)
                    item.setBrush(QBrush(Qt.cyan))  # Highlight selected node
                
                if len(self.selected_nodes) > 2:
                    # Deselect the oldest node
                    old_node = self.selected_nodes.pop(0)
                    old_node.setBrush(QBrush(Qt.yellow))  # Reset color
        
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        # If in automatic connection mode, check if we're connecting nodes
        if self.connection_mode == "automatic" and event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, MindMapNode):
                # Check if we started the drag on a different node
                if self.last_mouse_pos:
                    start_item = self.scene.itemAt(self.last_mouse_pos, self.transform())
                    if isinstance(start_item, MindMapNode) and start_item != item:
                        # Connect these two nodes
                        line = QGraphicsLineItem()
                        line.setPen(QPen(Qt.black, 2, Qt.DashLine))
                        self.scene.addItem(line)
                        
                        # Set line position
                        start_item.update_connection_line(line, start_item, item)
                        
                        # Add to connections
                        start_item.connections.append((line, item))
                        item.connections.append((line, start_item))
        
        super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
            self.scale_factor *= zoom_in_factor
        else:
            self.scale(zoom_out_factor, zoom_out_factor)
            self.scale_factor *= zoom_out_factor
    
    def export_to_image(self, file_path):
        """Export the current mind map to an image file"""
        # Create a new scene that only contains nodes visible in our view
        visible_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        
        # Get the scene rect that contains all items
        items_rect = self.scene.itemsBoundingRect()
        
        # Use the larger of the two
        export_rect = items_rect.united(visible_rect)
        
        # Create a new image with the appropriate size
        image = QImage(export_rect.width(), export_rect.height(), QImage.Format_ARGB32)
        image.fill(Qt.white)
        
        # Create a painter to render the scene to the image
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Render the scene
        self.scene.render(painter, QRectF(), export_rect)
        painter.end()
        
        # Save the image to the specified file
        image.save(file_path)
    
    def save_mindmap(self, file_path):
        """Save the mind map to a JSON file"""
        data = {
            "nodes": [],
            "connections": [],
            "root_node_index": -1
        }
        
        # Save nodes
        for i, node in enumerate(self.nodes):
            if node == self.root_node:
                data["root_node_index"] = i
            
            node_data = {
                "id": i,
                "x": node.scenePos().x(),
                "y": node.scenePos().y(),
                "text": node.text_item.toPlainText(),
                "color": node.brush().color().name(),
                "node_type": node.node_type,
                "width": node.width,
                "height": node.height,
                "level": node.level,
                "notes": node.notes,
                "collapsed": node.collapsed,
                "children": [self.nodes.index(child) for child in node.children]
            }
            data["nodes"].append(node_data)
        
        # Save connections (excluding parent-child connections which are saved in children lists)
        for i, node in enumerate(self.nodes):
            for _, connected_node in node.connections:
                j = self.nodes.index(connected_node)
                if i < j:  # Save each connection only once
                    data["connections"].append([i, j])
        
        # Write to file
        with open(file_path, 'w') as f:
            json.dump(data, f)
    
    def load_mindmap(self, file_path):
        """Load a mind map from a JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Clear current scene
        self.scene.clear()
        self.nodes.clear()
        self.selected_nodes.clear()
        self.root_node = None
        
        # Create nodes
        for node_data in data["nodes"]:
            node = MindMapNode(
                node_data["x"], 
                node_data["y"], 
                node_data["text"],
                QColor(node_data["color"]),
                node_data["node_type"],
                node_data["width"],
                node_data["height"]
            )
            node.level = node_data["level"]
            node.notes = node_data["notes"]
            node.collapsed = node_data["collapsed"]
            self.scene.addItem(node)
            self.nodes.append(node)
        
        # Set root node
        if data["root_node_index"] >= 0:
            self.root_node = self.nodes[data["root_node_index"]]
        
        # Set up parent-child relationships
        for i, node_data in enumerate(data["nodes"]):
            for child_idx in node_data["children"]:
                self.nodes[i].children.append(self.nodes[child_idx])
                
                # Create the connection line
                line = QGraphicsLineItem()
                line.setPen(QPen(Qt.black, 2, Qt.SolidLine))
                self.scene.addItem(line)
                
                # Set parent connection for the child
                self.nodes[child_idx].parent_connection = (line, self.nodes[i])
                
                # Update line position
                self.nodes[child_idx].update_connection_line(
                    line, self.nodes[i], self.nodes[child_idx]
                )
                
                # Apply collapsed state
                if self.nodes[i].collapsed:
                    self.nodes[child_idx].setVisible(False)
                    line.setVisible(False)
        
        # Create non-hierarchical connections
        for i,
