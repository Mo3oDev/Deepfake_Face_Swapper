from PyQt5.QtWidgets import (QMainWindow, QPushButton, QLabel, QFileDialog, QVBoxLayout, 
                         QHBoxLayout, QWidget, QMessageBox, QFrame, QProgressBar, QGroupBox, QGridLayout, QSizePolicy)
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon, QWheelEvent, QPainter
from PyQt5.QtCore import Qt, QSize, QTimer
import os
import cv2
from core.face_swapper import FaceSwapper

class ZoomableLabel(QLabel):
    """QLabel que permite hacer zoom con la rueda del ratón (Ctrl + rueda) y mover la imagen con drag (pan)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #ffffff;")
        self.setMinimumSize(250, 250)
        self._zoom = 1.0
        self._max_zoom = 4.0
        self._min_zoom = 0.2
        self._base_pixmap = None
        self._offset = [0, 0]  # Desplazamiento x, y
        self._drag_active = False
        self._last_pos = None

    def setPixmap(self, pixmap):
        self._base_pixmap = pixmap
        self._zoom = 1.0
        self._offset = [0, 0]
        self.updatePixmap()

    def updatePixmap(self):
        if self._base_pixmap:
            size = self._base_pixmap.size()
            w = int(size.width() * self._zoom)
            h = int(size.height() * self._zoom)
            scaled = self._base_pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # Crear un QPixmap del tamaño del label para centrar y desplazar
            label_size = self.size()
            canvas = QPixmap(label_size)
            canvas.fill(Qt.white)
            painter = QPainter(canvas)
            # Calcular posición centrada + offset
            x = (label_size.width() - scaled.width()) // 2 + self._offset[0]
            y = (label_size.height() - scaled.height()) // 2 + self._offset[1]
            painter.drawPixmap(x, y, scaled)
            painter.end()
            super().setPixmap(canvas)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.ControlModifier:
            angle = event.angleDelta().y()
            factor = 1.25 if angle > 0 else 0.8
            new_zoom = self._zoom * factor
            if self._min_zoom <= new_zoom <= self._max_zoom:
                # Mantener el punto bajo el cursor al hacer zoom
                if self._base_pixmap:
                    cursor_pos = event.pos()
                    label_size = self.size()
                    pixmap_size = self._base_pixmap.size() * self._zoom
                    rel_x = cursor_pos.x() - label_size.width() // 2 - self._offset[0]
                    rel_y = cursor_pos.y() - label_size.height() // 2 - self._offset[1]
                    scale_factor = new_zoom / self._zoom
                    self._offset[0] = int(self._offset[0] - rel_x * (scale_factor - 1))
                    self._offset[1] = int(self._offset[1] - rel_y * (scale_factor - 1))
                self._zoom = new_zoom
                self.updatePixmap()
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._zoom > 1.0:
            self._drag_active = True
            self._last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_active and self._last_pos:
            dx = event.pos().x() - self._last_pos.x()
            dy = event.pos().y() - self._last_pos.y()
            self._offset[0] += dx
            self._offset[1] += dy
            self._last_pos = event.pos()
            self.updatePixmap()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_active = False
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        self.updatePixmap()
        super().resizeEvent(event)

    def resetZoom(self):
        self._zoom = 1.0
        self._offset = [0, 0]
        self.updatePixmap()

class ImageFrame(QFrame):
    """Frame personalizado para mostrar imágenes con un título y un borde estilizado"""
    def __init__(self, title, parent=None, zoomable=False):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #3498db;
                border-radius: 8px;
                background-color: #f0f0f0;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        
        # Título con estilo
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            color: #2c3e50;
            padding: 5px;
            background-color: #ecf0f1;
            border-bottom: 1px solid #bdc3c7;
            border-top-left-radius: 7px;
            border-top-right-radius: 7px;
        """)
        
        # Contenedor para la imagen
        if zoomable:
            self.image_label = ZoomableLabel()
        else:
            self.image_label = QLabel()
            self.image_label.setAlignment(Qt.AlignCenter)
            self.image_label.setMinimumSize(250, 250)
            self.image_label.setStyleSheet("background-color: #ffffff;")
        
        # Texto de información
        self.info_label = QLabel("Sin imagen")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        
        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.image_label)
        self.layout.addWidget(self.info_label)
    
    def setImage(self, pixmap):
        if hasattr(self.image_label, 'setPixmap'):
            self.image_label.setPixmap(pixmap)
        self.info_label.setText("")
    
    def setInfo(self, text):
        self.info_label.setText(text)
    
    def clear(self):
        self.image_label.clear()
        self.info_label.setText("Sin imagen")

class StyledButton(QPushButton):
    """Botón personalizado con estilo moderno"""
    def __init__(self, text, icon_path=None, parent=None):
        super().__init__(text, parent)
        
        if (icon_path and os.path.exists(icon_path)):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(24, 24))
        
        self.setMinimumHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Deepfake - Face Swapper - UDEC")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 13px;
                color: #2c3e50;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: #2c3e50;
            }
        """)
        
        self.swapper = FaceSwapper()
        self.target_img_path = None
        self.source_img_path = None
        self.result_img = None
        
        # Inicializar la interfaz después de un corto retraso
        self.init_ui()
    
   
    def init_ui(self):
        # Widget central y layout principal
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Título de la aplicación
        title_label = QLabel("Deepfake - Face Swapper - UDEC")
        title_font = QFont("Arial", 20, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            color: #2c3e50;
            margin: 10px;
            padding: 5px;
            background-color: #ecf0f1;
            border-radius: 5px;
        """)
        
        # Layout para las imágenes (2x2 grid)
        images_layout = QGridLayout()
        
        # Frames para las imágenes
        self.target_frame = ImageFrame("Imagen Objetivo (Cara a reemplazar)")
        self.source_frame = ImageFrame("Imagen Fuente (Cara a utilizar)")
        self.result_frame = ImageFrame("Resultado", zoomable=True)
        
        # Agregar frames al grid
        images_layout.addWidget(self.target_frame, 0, 0)
        images_layout.addWidget(self.source_frame, 0, 1)
        images_layout.addWidget(self.result_frame, 1, 0, 1, 2)
        
        # Panel de controles
        controls_group = QGroupBox("Controles")
        controls_layout = QVBoxLayout(controls_group)
        
        # Botones con íconos
        buttons_layout = QHBoxLayout()
        
        # Icono paths 
        target_icon = "icons/target.png"  
        source_icon = "icons/source.png"
        swap_icon = "icons/swap.png"
        clear_icon = "icons/clear.png"
        save_icon = "icons/save.png"
        reset_icon = "icons/reset.png"

        # Crear botones estilizados
        self.target_btn = StyledButton("Seleccionar imagen objetivo", target_icon)
        self.source_btn = StyledButton("Seleccionar imagen fuente", source_icon)
        self.swap_btn = StyledButton("Realizar Face Swap", swap_icon)
        self.clear_btn = StyledButton("Limpiar", clear_icon)
        self.save_btn = StyledButton("Guardar resultado", save_icon)
        self.reset_zoom_btn = StyledButton("Resetear zoom", reset_icon)
        self.reset_zoom_btn.setEnabled(False)
        self.reset_zoom_btn.clicked.connect(self.reset_result_zoom)
        
        # Conectar señales
        self.target_btn.clicked.connect(self.select_target_img)
        self.source_btn.clicked.connect(self.select_source_img)
        self.swap_btn.clicked.connect(self.do_swap)
        self.clear_btn.clicked.connect(self.clear_all)
        self.save_btn.clicked.connect(self.save_result)
        
        # Desactivar botones hasta que tengamos imágenes
        self.swap_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        
        # Agregar botones al layout
        buttons_layout.addWidget(self.target_btn)
        buttons_layout.addWidget(self.source_btn)
        buttons_layout.addWidget(self.swap_btn)
        buttons_layout.addWidget(self.clear_btn)
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.reset_zoom_btn)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                width: 10px;
                margin: 0.5px;
            }
        """)
        
        # Agregar todo al layout de controles
        controls_layout.addLayout(buttons_layout)
        controls_layout.addWidget(self.progress_bar)
        
        # Pie de página / barra de estado
        footer_label = QLabel("© 2025 Deepfake - Face Swapper - UDEC | Desarrollado con ❤ & ☕")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("""
            font-style: italic;
            color: #7f8c8d;
            padding: 5px;
            border-top: 1px solid #bdc3c7;
        """)
        
        main_layout.addWidget(title_label)
        main_layout.addLayout(images_layout, 3)  
        main_layout.addWidget(controls_group, 1)
        main_layout.addWidget(footer_label)
        
        self.setCentralWidget(central_widget)
        
    
    def select_target_img(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen objetivo", "images/gallery", 
            "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.target_img_path = path
            pixmap = QPixmap(path)
            scaled_pixmap = pixmap.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.target_frame.setImage(scaled_pixmap)
            self.target_frame.setInfo(f"Archivo: {os.path.basename(path)}")
            self.update_swap_button_state()

    def select_source_img(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen fuente", "images/gallery", 
            "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.source_img_path = path
            pixmap = QPixmap(path)
            scaled_pixmap = pixmap.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.source_frame.setImage(scaled_pixmap)
            self.source_frame.setInfo(f"Archivo: {os.path.basename(path)}")
            self.update_swap_button_state()

    def update_swap_button_state(self):
        """Actualiza el estado del botón de swap basado en si ambas imágenes están cargadas"""
        if self.target_img_path and self.source_img_path:
            self.swap_btn.setEnabled(True)
        else:
            self.swap_btn.setEnabled(False)
            
    def do_swap(self):
        if not self.target_img_path or not self.source_img_path:
            QMessageBox.warning(self, "Error", "Selecciona ambas imágenes primero.")
            return
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.target_btn.setEnabled(False)
            self.source_btn.setEnabled(False)
            self.swap_btn.setEnabled(False)
            QTimer.singleShot(300, lambda: self.progress_bar.setValue(30))
            QTimer.singleShot(600, lambda: self.progress_bar.setValue(60))
            QTimer.singleShot(900, lambda: self.progress_bar.setValue(90))
            # Nombre descriptivo para la imagen generada
            nombre_objetivo = os.path.splitext(os.path.basename(self.target_img_path))[0]
            nombre_fuente = os.path.splitext(os.path.basename(self.source_img_path))[0]
            output_name = f"swap_{nombre_objetivo}_con_{nombre_fuente}.png"
            output_path = os.path.join("images", "generated", output_name)
            _, self.result_img = self.swapper.swap_faces(
                self.target_img_path, 
                self.source_img_path, 
                output_path
            )
            QTimer.singleShot(1200, lambda: self.show_result(self.result_img))
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.target_btn.setEnabled(True)
            self.source_btn.setEnabled(True)
            self.swap_btn.setEnabled(True)
            QMessageBox.critical(self, "Error", str(e))
    
    def show_result(self, img):
        """Muestra la imagen resultado en el frame correspondiente, ocupando todo el ancho disponible sin distorsión y habilita zoom interactivo."""
        # Convertimos a RGB y creamos el QPixmap
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_img.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        # Hacemos que el label expanda con el layout
        self.result_frame.image_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        # Obtenemos el ancho y alto actualmente disponibles en el label
        available_w = self.result_frame.image_label.width()
        available_h = self.result_frame.image_label.height()

        # Escalamos el pixmap al ancho disponible, manteniendo proporción
        scaled_pixmap = pixmap.scaled(
            available_w,
            available_h,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        # Pintamos y actualizamos
        self.result_frame.setImage(scaled_pixmap)
        self.result_frame.setInfo("¡Face swap completado! (Ctrl + rueda para zoom)")

        # Restauramos controles y barra de progreso
        self.progress_bar.setValue(100)
        QTimer.singleShot(500, lambda: self.progress_bar.setVisible(False))
        for btn in (self.target_btn, self.source_btn, self.swap_btn, self.save_btn, self.reset_zoom_btn):
            btn.setEnabled(True)
        QMessageBox.information(self, "Éxito", "¡Face swap completado correctamente!")

    def reset_result_zoom(self):
        """Resetea el zoom de la imagen de resultado."""
        if hasattr(self.result_frame.image_label, 'resetZoom'):
            self.result_frame.image_label.resetZoom()
    
    def clear_all(self):
        """Limpia todas las imágenes y restablece el estado"""
        self.target_img_path = None
        self.source_img_path = None
        self.result_img = None
        
        # Limpiar frames
        self.target_frame.clear()
        self.source_frame.clear()
        self.result_frame.clear()
        
        # Actualizar estado de botones
        self.swap_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.reset_zoom_btn.setEnabled(False)
    
    def save_result(self):
        """Guarda la imagen resultado en un archivo seleccionado por el usuario"""
        if self.result_img is None:
            QMessageBox.warning(self, "Advertencia", "No hay resultado para guardar.")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar imagen resultado", "images/generated", 
            "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if path:
            try:
                cv2.imwrite(path, self.result_img)
                QMessageBox.information(self, "Éxito", f"Imagen guardada en {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al guardar la imagen: {str(e)}")

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())