from PySide import QtCore, QtGui

from .qt_util import read_qt_image
from .graphics import GraphicsView, GraphicsScene, BoxResizable

from segment import segment_edges, segment_intensity

from multiprocessing import Process, Queue
import os
import sys
import csv

import cv2


class ImageViewer(QtGui.QMainWindow):
    def __init__(self, app, filename=None):
        super(ImageViewer, self).__init__()
        self.app = app
        self.wireframe_mode = 0
        self.view = GraphicsView(wireframe_mode=self.wireframe_mode)
        self.scene = GraphicsScene()
        self.view.setViewportUpdateMode(QtGui.QGraphicsView.FullViewportUpdate)
        self.view.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.view.setUpdatesEnabled(True)
        self.view.setMouseTracking(True)
        self.scene.setGraphicsView(self.view)
        self.view.setScene(self.scene)
        self.view.setCacheMode(QtGui.QGraphicsView.CacheBackground)
        self.setCentralWidget(self.view)
        self.view.move_box = BoxResizable(QtCore.QRectF(10, 10, 100, 100),
                                          color=QtCore.Qt.red,
                                          transparent=True,
                                          scene=self.scene)
        self.scene.addItem(self.view.move_box)
        self.view.move_box.setVisible(False)
        if not self.wireframe_mode:
            self.view.move_box.setZValue(1E9)

        if filename is None:
            image = QtGui.QImage()
        else:
            image = read_qt_image(filename)

        item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap.fromImage(image))
        self.scene.addItem(item)
        self.image_item = item
        self.scene.image = item
        self.create_actions()
        self.create_menus()

        self.setWindowTitle("Image Viewer")
        self.resize(500, 400)
        if filename:
            self.open(filename)

    def open(self, filename=None):
        if not filename:
            filename, _ = QtGui.QFileDialog.getOpenFileName(
                self, "Open File", QtCore.QDir.currentPath())
        if filename:
            self.filename = filename
            image = read_qt_image(filename)
            if image.isNull():
                QtGui.QMessageBox.information(self, "Image Viewer",
                                              "Cannot load %s." % filename)
                return
            for item in list(self.view.items):
                self.view.remove_item(item)

            self.image_item.setPixmap(QtGui.QPixmap.fromImage(image))
            self.scene.setSceneRect(0, 0, image.width(), image.height())
            self.segment_action.setEnabled(True)
            self.export_action.setEnabled(True)
            self.zoom_in_action.setEnabled(True)
            self.zoom_out_action.setEnabled(True)

    def zoom_in(self):
        self.view.set_scale(1.2)

    def zoom_out(self):
        self.view.set_scale(0.8)

    def about(self):
        QtGui.QMessageBox.about(self, "Insect Selector",
                                "Stefan van der Walt\nPieter Holtzhausen")

    def add_box(self, rect):
        x, y, w, h = rect
        s = QtCore.QPoint(x, y)
        e = QtCore.QPoint(x + w, y + h)
        qrect = QtCore.QRectF(s.x(), s.y(), e.x() - s.x(), e.y() - s.y())
        box = BoxResizable(qrect,
                           transparent=self.wireframe_mode,
                           scene=self.scene)
        self.view.add_item(box)
        if not self.wireframe_mode:
            b = box.boundingRect()
            box.setZValue(max(1000, 1E9 - b.width() * b.height()))
            box.updateResizeHandles()

    def segment(self):
        self.progressDialog = QtGui.QProgressDialog(self)
        self.progressDialog.setWindowTitle("Segmenting...")
        self.progressDialog.setValue(0)
        self.progressDialog.setMaximum(0)
        self.progressDialog.setMinimum(0)
        self.progressDialog.show()
        image = cv2.imread(self.filename)

        def f(image, results_queue, window=None):
            rects = segment_edges(image,
                                  window=window,
                                  variance_threshold=100,
                                  size_filter=1)
            results_queue.put(rects)

        results = Queue()
        window = None
        selected = self.scene.selectedItems()
        if selected:
            selected = selected[0]
            window_rect = selected.map_rect_to_scene(selected._rect)
            p = window_rect.topLeft()
            window = [p.x(), p.y(), window_rect.width(), window_rect.height()]
            rects = segment_intensity(image, window=window)
            self.view.remove_item(selected)
        else:
            p = Process(target=f, args=[image, results, window])
            p.start()
            while p.is_alive():
                self.app.processEvents()
                p.join(0.1)
            rects, display = results.get()
        for rect in rects:
            self.add_box(rect)
        self.display = display
        self.progressDialog.hide()

    def export(self):
        path = QtGui.QFileDialog.getExistingDirectory(
            self, "Export Destination", QtCore.QDir.currentPath())
        image = cv2.imread(self.filename)

        for i, item in enumerate(self.view.items):
            b = item._rect
            print b
            x, y, w, h = b.x(), b.y(), b.width(), b.height()
            extract = image[y:y+h, x:x+w]
            print extract.shape, i
            cv2.imwrite(os.path.join(path, "image%s.png" % i), extract)

    def select_all(self):
        for item in self.view.items:
            item.setSelected(True)

    def create_actions(self):
        self.open_action = QtGui.QAction(
            self.style().standardIcon(QtGui.QStyle.SP_DirIcon),
            "&Open Image", self, shortcut="ctrl+O",
            triggered=self.open)

        self.exit_action = QtGui.QAction(
            "E&xit", self, shortcut="alt+f4", triggered=self.close)

        self.select_all_action = QtGui.QAction(
            "Select &All", self, shortcut="ctrl+A", triggered=self.select_all)

        self.zoom_in_action = QtGui.QAction(
            self.style().standardIcon(QtGui.QStyle.SP_ArrowUp),
            "Zoom &In", self, enabled=False, shortcut="Ctrl++",
            triggered=self.zoom_in)

        self.zoom_out_action = QtGui.QAction(
            self.style().standardIcon(QtGui.QStyle.SP_ArrowDown),
            "Zoom &Out", self, enabled=False, shortcut="Ctrl+-",
            triggered=self.zoom_out)

        self.about_action = QtGui.QAction("&About", self, triggered=self.about)

        self.segment_action = QtGui.QAction(
            self.style().standardIcon(QtGui.QStyle.SP_ComputerIcon),
            "&Segment", self, shortcut="f5", enabled=False,
            statusTip="Segment",
            triggered=self.segment)

        self.save_action = QtGui.QAction(
            self.style().standardIcon(QtGui.QStyle.SP_DesktopIcon),
            "&Save Boxes", self, shortcut="ctrl+s", enabled=False,
            statusTip="Save Boxes",
            triggered=self.save_boxes)

        self.import_action = QtGui.QAction(
            self.style().standardIcon(QtGui.QStyle.SP_DesktopIcon),
            "&Import Boxes", self, shortcut="ctrl+i", enabled=False,
            statusTip="Import Boxes",
            triggered=self.import_boxes)

        self.export_action = QtGui.QAction(
            self.style().standardIcon(QtGui.QStyle.SP_FileIcon),
            "&Export Images...", self, shortcut="", enabled=False,
            statusTip="Export",
            triggered=self.export)

    def save_boxes(self):
        file_name, filtr = QtGui.QFileDialog.getSaveFileName(
            self,
            "QFileDialog.getSaveFileName()",
            self.file_name + ".csv",
            "All Files (*);;CSV Files (*.csv)", "",
            QtGui.QFileDialog.Options())
        if file_name:
            with open(file_name, 'w') as csvfile:
                writer = csv.writer(csvfile, delimiter=' ')
                for item in self.view.items:
                    rect = item.rect()
                    box = [rect.left(), rect.top(),
                           rect.width(), rect.height()]
                    width = self.image_item.pixmap().width()
                    height = self.image_item.pixmap().height()
                    box[0] /= width
                    box[1] /= height
                    box[2] /= width
                    box[3] /= height
                    writer.writerow(box)

    def import_boxes(self):
        files, filtr = QtGui.QFileDialog.getOpenFileNames(
            self,
            "QFileDialog.getOpenFileNames()", "../data",
            "All Files (*);;Text Files (*.csv)", "",
            QtGui.QFileDialog.Options())

        if files:
            width = self.image_item.pixmap().width()
            height = self.image_item.pixmap().height()
            for file_name in files:
                with open(file_name, 'r') as csvfile:
                    reader = csv.reader(csvfile, delimiter=' ')
                    for row in reader:
                        rect = [float(x) for x in row]
                        rect[0] *= width
                        rect[1] *= height
                        rect[2] *= width
                        rect[3] *= height
                        self.add_box(rect)

    def create_menus(self):
        self.toolbar = self.addToolBar("Edit")
        self.toolbar.addAction(self.open_action)
        self.toolbar.addAction(self.segment_action)
        self.toolbar.addAction(self.zoom_in_action)
        self.toolbar.addAction(self.zoom_out_action)
        self.toolbar.addAction(self.save_action)
        self.toolbar.addAction(self.import_action)
        self.toolbar.addAction(self.export_action)
        self.toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)

        self.fileMenu = QtGui.QMenu("&File", self)
        self.fileMenu.addAction(self.open_action)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.save_action)
        self.fileMenu.addAction(self.import_action)
        self.fileMenu.addAction(self.export_action)

        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exit_action)

        self.viewMenu = QtGui.QMenu("&View", self)
        self.viewMenu.addAction(self.select_all_action)
        self.viewMenu.addAction(self.zoom_in_action)
        self.viewMenu.addAction(self.zoom_out_action)

        self.helpMenu = QtGui.QMenu("&Help", self)
        self.helpMenu.addAction(self.about_action)

        self.menuBar().addMenu(self.fileMenu)
        self.menuBar().addMenu(self.viewMenu)
        self.menuBar().addMenu(self.helpMenu)

    def keyPressEvent(self, event):
        return
        if event.key() == 16777216:
        # if event.key() == Qtcore.Qt.Key_Escape:
            sys.exit(1)
