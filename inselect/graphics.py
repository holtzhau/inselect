__all__ = ['GraphicsView', 'GraphicsScene', 'BoxResizable']


import numpy as np
from PySide import QtCore, QtGui

from mouse import MouseEvents
from key_handler import KeyHandler
import image_viewer


class GraphicsView(KeyHandler, MouseEvents, QtGui.QGraphicsView):
    def __init__(self, parent=None):
        QtGui.QGraphicsView.__init__(self, parent)
        MouseEvents.__init__(self, parent_class=QtGui.QGraphicsView)
        KeyHandler.__init__(self, parent_class=QtGui.QGraphicsView)
        self.scrollBarValuesOnMousePress = QtCore.QPoint()
        self.is_resizing = False
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        self.items = []
        self.parent = parent
        # Setup key handlers
        self.add_key_handler(QtCore.Qt.Key_Delete, self.delete_boxes)
        self.add_key_handler(QtCore.Qt.Key_Z, self.zoom_to_selection)
        self.add_key_handler(QtCore.Qt.Key_Up, self.move_boxes, 0, -1)
        self.add_key_handler(QtCore.Qt.Key_Up, self.move_boxes, 0, -1)
        self.add_key_handler(QtCore.Qt.Key_Right, self.move_boxes, 1, 0)
        self.add_key_handler(QtCore.Qt.Key_Down, self.move_boxes, 0, 1)
        self.add_key_handler(QtCore.Qt.Key_Left, self.move_boxes, -1, 0)
        self.add_key_handler((QtCore.Qt.ControlModifier, QtCore.Qt.Key_Up), self.move_boxes, 0, -1, 0, 0)
        self.add_key_handler((QtCore.Qt.ControlModifier, QtCore.Qt.Key_Right), self.move_boxes, 1, 0, 0, 0)
        self.add_key_handler((QtCore.Qt.ControlModifier, QtCore.Qt.Key_Down), self.move_boxes, 0, 1, 0, 0)
        self.add_key_handler((QtCore.Qt.ControlModifier, QtCore.Qt.Key_Left), self.move_boxes, -1, 0, 0, 0)
        self.add_key_handler((QtCore.Qt.ShiftModifier, QtCore.Qt.Key_Up), self.move_boxes, 0, 0, 0, -1)
        self.add_key_handler((QtCore.Qt.ShiftModifier, QtCore.Qt.Key_Right), self.move_boxes, 0, 0, 1, 0)
        self.add_key_handler((QtCore.Qt.ShiftModifier, QtCore.Qt.Key_Down), self.move_boxes, 0, 0, 0, 1)
        self.add_key_handler((QtCore.Qt.ShiftModifier, QtCore.Qt.Key_Left), self.move_boxes, 0, 0, -1, 0)
        self.add_key_handler(QtCore.Qt.Key_N, self.select_next)
        self.add_key_handler(QtCore.Qt.Key_P, self.select_previous)

    def add_item(self, item):
        # Insert into the list so as to ease prev/next navigation
        band_size = int(self.scene().height()/20)
        item_box = item.boundingRect()
        insert_at = len(self.items)
        for i in range(len(self.items)):
            box = self.items[i].boundingRect()
            item_box_band = int(item_box.y()/band_size)
            box_band = int(box.y()/band_size)
            if item_box_band > box_band:
                continue
            if item_box_band < box_band or item_box.x() < box.x():
                insert_at = i
                break
        self.items.insert(insert_at, item)
        # Add the item to the sidebar
        window = self.parent
        sidebar = self.parent.sidebar
        icon = window.get_icon(item)
        list_item = image_viewer.ListItem(icon, "", box=item)
        item.list_item = list_item
        sidebar.insertItem(insert_at, list_item)

    def remove_item(self, item):
        self.items.remove(item)
        self.scene().removeItem(item)

    def set_scale(self, scale):
        self.scale_factor = scale
        self.scale(scale, scale)

    def zoom_to_selection(self):
        """Zoom the view to the current selection"""
        box = self._get_selection_box()
        if box is not None:
            self.fitInView(box[0][0], box[0][1], box[1][0] - box[0][0], box[1][1] - box[0][1],
                           QtCore.Qt.KeepAspectRatio)

    def move_boxes(self, tl_dx, tl_dy, br_dx=None, br_dy=None):
        """Move the selected boxes

        If only two values are specified, the top left and bottom right corners
        are moved equally (so the entire box is moved). If four values are
        specified, then the top left and bottom right corners are moved independently.

        Parameters
        ----------
        tl_dx : int
            X increment for top left corner/box
        tl_dy : int
            Y increment for top left corner/box
        br_dx : int
            X increment for bottom right corner or None
        br_dy : int
            Y increment for bottom right corner or None
        """
        selected_boxes = self.scene().selectedItems()
        for box in selected_boxes:
            box.move_box(tl_dx, tl_dy, br_dx, br_dy)

    def delete_boxes(self):
        """Delete all selected boxes"""
        sidebar = self.parent.sidebar
        selected_boxes = self.scene().selectedItems()
        for box in selected_boxes:
            sidebar.takeItem(sidebar.row(box.list_item))
            self.remove_item(box)

    def deselect_all(self):
        """Deselect all items in the scene"""
        for item in self.scene().selectedItems():
            item.setSelected(False)

    def select_next(self):
        """Select the next object in the scene"""
        if len(self.items) == 0:
            return
        selected = self.scene().selectedItems()
        if len(selected) > 0:
            to_select = (self.items.index(selected[0]) + 1) % len(self.items)
        else:
            to_select = 0
        self.deselect_all()
        self.items[to_select].setSelected(True)
        self.ensure_selection_visible()

    def select_previous(self):
        """Select the previous object in the scene"""
        if len(self.items) == 0:
            return
        selected = self.scene().selectedItems()
        if len(selected) > 0:
            to_select = (self.items.index(selected[0]) - 1) % len(self.items)
        else:
            to_select = 0
        self.deselect_all()
        self.items[to_select].setSelected(True)
        self.ensure_selection_visible()

    def ensure_selection_visible(self):
        """Ensure the selected boxes are visible

        Notes
        -----
        Doing on this on a mouse-triggered selection change event might cause the box to move.
        """
        box = self._get_selection_box()
        if box is not None:
            self.ensureVisible(box[0][0], box[0][1], box[1][0] - box[0][0], box[1][1] - box[0][1])

    def _get_selection_box(self):
        """Return the bounding box of selected items

        Returns
        --------
        tuple
            (top_left, bottom_right) where each tuple is formed of (x,y) or None if there is no selection
        """
        tl = None
        br = None
        for item in self.scene().selectedItems():
            box = item.boundingRect()
            if tl is None:
                tl = (box.left(), box.top())
                br = (box.right(), box.bottom())
            else:
                tl = (min(tl[0], box.left()), min(tl[1], box.top()))
                br = (max(br[0], box.right()), max(br[1], box.bottom()))
        if tl is None:
            return None
        return tl, br

    def wheelEvent(self, event):
        if (event.modifiers() & QtCore.Qt.ControlModifier):
            if event.delta() > 0:
                scale = 1.2
            else:
                scale = 0.8
            self.set_scale(scale)
            return
        QtGui.QGraphicsView.wheelEvent(self, event)

    def _mouse_left(self, x, y):
        pass

    def _mouse_right(self, x, y):
        pass

    def _mouse_middle(self, x, y):
        x = self.horizontalScrollBar().value()
        y = self.verticalScrollBar().value()
        self.scrollBarValuesOnMousePress.setX(x)
        self.scrollBarValuesOnMousePress.setY(y)

    def _mouse_grow_box(self, x, y):
        state = self._mouse_state

        s = self.mapToScene(*state['pressed_at'])
        e = self.mapToScene(x, y)

        w, h = (e.toPoint().x() - s.toPoint().x(),
                e.toPoint().y() - s.toPoint().y())

        self.scene().update()

    def _mouse_middle_release(self, x, y):
        pass

    def _mouse_right_release(self, x, y):
        state = self._mouse_state

        box_x, box_y = state['pressed_at']

        x1, y1 = min(box_x, x), min(box_y, y)
        x2, y2 = max(box_x, x), max(box_y, y)

        s = self.mapToScene(x1, y1)
        e = self.mapToScene(x2, y2)

        w = np.abs(s.x() - e.x())
        h = np.abs(s.y() - e.y())

        if w > 5 and h > 5:
            box = BoxResizable(QtCore.QRectF(s.x(), s.y(), w, h),
                               scene=self.scene())

            b = box.boundingRect()
            box.setZValue(max(1000, 1E9 - b.width() * b.height()))
            box.updateResizeHandles()

            self.add_item(box)

    def _mouse_left_release(self, x, y):
        pass

    def _mouse_move(self, x, y):
        state = self._mouse_state

        if state['button'] == 'right':
            self._mouse_grow_box(x, y)

        if state['button'] == 'middle':
            press_x, press_y = state['pressed_at']

            x = self.scrollBarValuesOnMousePress.x() - x + \
                press_x
            y = self.scrollBarValuesOnMousePress.y() - y + \
                press_y

            self.horizontalScrollBar().setValue(x)
            self.horizontalScrollBar().update()

            self.verticalScrollBar().setValue(y)
            self.verticalScrollBar().update()


class GraphicsScene(MouseEvents, QtGui.QGraphicsScene):
    def __init__(self, parent=None):
        QtGui.QGraphicsScene.__init__(self, parent)
        MouseEvents.__init__(self, parent_class=QtGui.QGraphicsScene)

    def setGraphicsView(self, view):
        self.view = view


class BoxResizable(QtGui.QGraphicsRectItem):
    def __init__(self, rect, parent=None, color=QtCore.Qt.blue,
                 transparent=False, scene=None):
        QtGui.QGraphicsRectItem.__init__(self, rect, parent, scene)
        self._rect = rect
        self._scene = scene
        self.orig_rect = QtCore.QRectF(rect)
        self.mouseOver = False
        self.handle_size = 4.0
        self.mouse_press_pos = None
        self.mouse_move_pos = None
        self.mouse_is_pressed = False
        self.mouse_press_area = None
        self.color = color
        self.transparent = transparent
        self.setFlags(QtGui.QGraphicsItem.ItemIsFocusable)
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
        self.setFlag(QtGui.QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptsHoverEvents(True)
        self.updateResizeHandles()

    def shape(self):
        path = QtGui.QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def hoverEnterEvent(self, event):
        self.updateResizeHandles()
        self.mouseOver = True
        b = self.boundingRect()
        if self.isSelected():
            self.setZValue(1E9)
        else:
            self.setZValue(max(1000, 1E9 - b.width() * b.height()))

    def hoverLeaveEvent(self, event):
        self.prepareGeometryChange()
        self.mouseOver = False
        self.scene().view.is_resizing = False
        b = self.boundingRect()
        self.setZValue(max(1000, 1E9 - b.width() * b.height()))

    def hoverMoveEvent(self, event):
        if any([self.top_left_handle.contains(event.pos()),
               self.bottom_right_handle.contains(event.pos())]):

            self.setCursor(QtCore.Qt.SizeFDiagCursor)
            self.scene().view.is_resizing = True

        elif (self.top_right_handle.contains(event.pos()) or
              self.bottom_left_handle.contains(event.pos())):

            self.setCursor(QtCore.Qt.SizeBDiagCursor)
            self.scene().view.is_resizing = True

        else:
            self.setCursor(QtCore.Qt.SizeAllCursor)
            self.scene().view.is_resizing = False

        b = self.boundingRect()
        if self.isSelected():
            self.setZValue(1E9)
        else:
            self.setZValue(max(1000, 1E9 - b.width() * b.height()))
        QtGui.QGraphicsRectItem.hoverMoveEvent(self, event)

    def mousePressEvent(self, event):
        """
        Capture mouse press events and find where the mosue was pressed
        on the object.
        """
        self.mouse_press_pos = event.scenePos().x(), event.scenePos().y()

        if event.button() == QtCore.Qt.LeftButton:
            self.mouse_is_pressed = True
            self.rect_press = QtCore.QRectF(self._rect)

            # Top left corner
            if self.top_left_handle.contains(event.pos()):
                self.mouse_press_area = 'topleft'
            # top right corner
            elif self.top_right_handle.contains(event.pos()):
                self.mouse_press_area = 'topright'
            #  bottom left corner
            elif self.bottom_left_handle.contains(event.pos()):
                self.mouse_press_area = 'bottomleft'
            # bottom right corner
            elif self.bottom_right_handle.contains(event.pos()):
                self.mouse_press_area = 'bottomright'
            # entire rectangle
            else:
                self.mouse_press_area = None

            QtGui.QGraphicsRectItem.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """
        Capture nmouse press events.
        """
        self.mouse_is_pressed = False
        self._rect = self._rect.normalized()
        self.updateResizeHandles()
        QtGui.QGraphicsRectItem.mouseReleaseEvent(self, event)

    def mouseMoveEvent(self, event):
        """
        Handle mouse move events.
        """
        def delta():
            x0, y0 = self.mouse_press_pos
            x1, y1 = self.mouse_move_pos

            return QtCore.QPoint(x0 - x1, y0 - y1)

        self.mouse_move_pos = (event.scenePos().x(), event.scenePos().y())
        if self.mouse_is_pressed:
            if self.mouse_press_area:
                self.prepareGeometryChange()
                # Move top left corner
                if self.mouse_press_area == 'topleft':
                    self._rect.setTopLeft(self.rect_press.topLeft() - delta())
                # Move top right corner
                elif self.mouse_press_area == 'topright':
                    self._rect.setTopRight(
                        self.rect_press.topRight() - delta())
                # Move bottom left corner
                elif self.mouse_press_area == 'bottomleft':
                    self._rect.setBottomLeft(
                        self.rect_press.bottomLeft() - delta())
                # Move bottom right corner
                elif self.mouse_press_area == 'bottomright':
                    self._rect.setBottomRight(
                        self.rect_press.bottomRight() - delta())

                event.accept()
                self.updateResizeHandles()

                return

            self.updateResizeHandles()
            QtGui.QGraphicsRectItem.mouseMoveEvent(self, event)

    def boundingRect(self):
        """
        Return bounding rectangle
        """
        return self._boundingRect

    def move_box(self, tl_dx, tl_dy, br_dx=None, br_dy=None):
        """Move the box

        If only two values are specified, the top left and bottom right corners
        are moved equally (so the entire box is moved). If four values are
        specified, then the top left and bottom right corners are moved independently.

        Parameters
        ----------
        tl_dx : int
            X increment for top left corner/box
        tl_dy : int
            Y increment for top left corner/box
        br_dx : int
            X increment for bottom right corner or None
        br_dy : int
            Y increment for bottom right corner or None
        """
        if br_dx is None or br_dy is None:
            self._rect.moveTo(self._rect.x() + tl_dx, self._rect.y() + tl_dy)
        else:
            tl = self._rect.topLeft()
            br = self._rect.bottomRight()
            self._rect.setCoords(tl.x() + tl_dx, tl.y() + tl_dy, br.x() + br_dx, br.y() + br_dy)
        self.updateResizeHandles()

    def updateResizeHandles(self):
        """
        Update bounding rectangle and resize handles
        """
        self.prepareGeometryChange()

        self.offset = self.handle_size * \
            (self._scene.view.mapToScene(1, 0) -
             self._scene.view.mapToScene(0, 1)).x()
        self._boundingRect = self._rect.adjusted(-self.offset, -self.offset,
                                                 self.offset, self.offset)

        self.offset1 = (self._scene.view.mapToScene(1, 0) -
                        self._scene.view.mapToScene(0, 1)).x()
        self._innerRect = self._rect.adjusted(self.offset1, self.offset1,
                                              -self.offset1, -self.offset1)

        b = self._boundingRect
        self.top_left_handle = QtCore.QRectF(b.topLeft().x(),
                                             b.topLeft().y(),
                                             2*self.offset,
                                             2*self.offset)

        self.top_right_handle = QtCore.QRectF(b.topRight().x() - 2*self.offset,
                                              b.topRight().y(),
                                              2*self.offset,
                                              2*self.offset)

        self.bottom_left_handle = QtCore.QRectF(
            b.bottomLeft().x(),
            b.bottomLeft().y() - 2*self.offset,
            2*self.offset,
            2*self.offset)

        self.bottom_right_handle = QtCore.QRectF(
            b.bottomRight().x() - 2*self.offset,
            b.bottomRight().y() - 2*self.offset,
            2*self.offset,
            2*self.offset)

        if self.isSelected():
            self.setZValue(1E9)
        else:
            self.setZValue(max(1000, 1E9 - b.width() * b.height()))

    def map_rect_to_scene(self, map_rect):
        rect = map_rect
        target_rect = QtCore.QRectF(rect)
        t = rect.topLeft()
        b = rect.bottomRight()
        target_rect.setTopLeft(QtCore.QPointF(t.x() + self.pos().x(),
                                              t.y() + self.pos().y()))
        target_rect.setBottomRight(QtCore.QPointF(b.x() + self.pos().x(),
                                                  b.y() + self.pos().y()))
        return target_rect

    def paint(self, painter, option, widget):
        """
        Paint Widget
        """
        # Paint rectangle
        if self.isSelected():
            color = QtCore.Qt.red
        else:
            color = self.color

        painter.setPen(QtGui.QPen(color, 0, QtCore.Qt.SolidLine))
        painter.drawRect(self._rect)

        if not self.transparent:
            rect = self._innerRect
            if rect.width() > 0 and rect.height() != 0:
                # normalize negative widths and heights, during resizing
                x1, y1 = rect.x(), rect.y()
                x2, y2 = rect.x() + rect.width(), rect.y() + rect.height()
                rect = QtCore.QRectF(min(x1, x2), min(y1, y2),
                                     abs(rect.width()), abs(rect.height()))
                target_rect = self.map_rect_to_scene(rect)
                painter.drawPixmap(rect, self.scene().image.pixmap(),
                                   target_rect)

        # If mouse is over, draw handles
        if self.mouseOver:
            painter.drawRect(self.top_left_handle)
            painter.drawRect(self.top_right_handle)
            painter.drawRect(self.bottom_left_handle)
            painter.drawRect(self.bottom_right_handle)
