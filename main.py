import sys
import datetime
from PySide6 import QtCore, QtGui, QtWidgets

from screen_dialog import SettingsDialog

class AnimatedToggleClockBar(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # Initialize QSettings
        self.settings = QtCore.QSettings("LinearClock", "LinearClock")
        
        # Load settings or use defaults
        self.load_settings()
        
        screens = QtGui.QGuiApplication.screens()

        if self.screen_index >= len(screens):
            self.screen_index = 0

        screen_geom = screens[self.screen_index].geometry()
        self.screen_width = screen_geom.width()
        self.screen_x = screen_geom.x()
        self.screen_y = screen_geom.y()


        self.full_height = 30
        self.slim_height = 5

        self.setGeometry(self.screen_x, self.screen_y, self.screen_width, self.slim_height)

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)

        self.setMouseTracking(True)

        # Animation setup
        self.animation = QtCore.QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(250)  # 250 ms animation
        self.animation.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

        self.create_tray_icon()

        self.show()

    def load_settings(self):
        """Load settings from QSettings or use defaults"""
        self.screen_index = self.settings.value("screen_index", 0, type=int)
        self.bar_position = self.settings.value("bar_position", "top", type=str)

    def save_settings(self):
        """Save current settings to QSettings"""
        self.settings.setValue("screen_index", self.screen_index)
        self.settings.setValue("bar_position", self.bar_position)
        self.settings.sync()  # Ensure settings are written to disk

    def create_tray_icon(self):
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        icon = QtGui.QIcon.fromTheme("clock")
        if icon.isNull():
            icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)

        # Set the tooltip shown when you hover over the tray icon
        self.tray_icon.setToolTip("Linear Clock")

        self.tray_icon.setVisible(True)

        menu = QtWidgets.QMenu()
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings)

        close_action = menu.addAction("Close")
        close_action.triggered.connect(QtWidgets.QApplication.quit)

        self.tray_icon.setContextMenu(menu)

        # Show a balloon message when app starts (duration in ms)
        self.tray_icon.showMessage(
            "Linear Clock",
            "Application has started.",
            QtWidgets.QSystemTrayIcon.Information,
            3000  # 3 seconds
        )

    def enterEvent(self, event):
        # Animate to full height based on current position
        target_rect = self.get_full_geometry()
        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(target_rect)
        self.animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Animate back to slim height after short delay
        QtCore.QTimer.singleShot(300, self.animate_to_slim)
        super().leaveEvent(event)

    def animate_to_slim(self):
        if not self.underMouse():
            target_rect = self.get_slim_geometry()
            self.animation.stop()
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(target_rect)
            self.animation.start()

    def paintEvent(self, event):
        now = datetime.datetime.now()
        seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second
        total_seconds = 24 * 60 * 60
        progress = seconds_since_midnight / total_seconds

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect()
        bar_color = QtGui.QColor(0, 255, 0, 120)  # Transparent green
        time_str = now.strftime("%H:%M:%S")

        painter.setBrush(bar_color)
        painter.setPen(QtCore.Qt.NoPen)

        if self.bar_position in ["top", "bottom"]:
            fill_width = int(rect.width() * progress)
            painter.drawRect(0, 0, fill_width, rect.height())

            # Draw time centered
            painter.setPen(QtGui.QColor("white"))
            font = QtGui.QFont("Arial", 12, QtGui.QFont.Bold)
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(rect, QtCore.Qt.AlignCenter, time_str)

        elif self.bar_position == "left":
            fill_height = int(rect.height() * progress)
            painter.drawRect(0, 0, rect.width(), fill_height)

            # Rotate text vertically (bottom-up)
            painter.save()
            painter.translate(rect.center().x(), rect.center().y())
            painter.rotate(-90)
            painter.setPen(QtGui.QColor("white"))
            font = QtGui.QFont("Arial", 12, QtGui.QFont.Bold)
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(QtCore.QRect(-rect.height() // 2, -rect.width() // 2,
                                        rect.height(), rect.width()),
                            QtCore.Qt.AlignCenter, time_str)
            painter.restore()

        elif self.bar_position == "right":
            fill_height = int(rect.height() * progress)
            painter.drawRect(0, rect.height() - fill_height, rect.width(), fill_height)

            # Rotate text vertically (top-down)
            painter.save()
            painter.translate(rect.center().x(), rect.center().y())
            painter.rotate(90)
            painter.setPen(QtGui.QColor("white"))
            font = QtGui.QFont("Arial", 12, QtGui.QFont.Bold)
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(QtCore.QRect(-rect.height() // 2, -rect.width() // 2,
                                        rect.height(), rect.width()),
                            QtCore.Qt.AlignCenter, time_str)
            painter.restore()


    def open_settings(self):
        screens = QtGui.QGuiApplication.screens()
        dialog = SettingsDialog(self, screens=screens, current_index=self.screen_index, position=self.bar_position)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            selected_index, selected_position = dialog.get_settings()
            self.bar_position = selected_position
            self.move_to_screen(selected_index, self.bar_position)
            # Save settings after change
            self.save_settings()


    def move_to_screen(self, screen_index, position='top'):
        screens = QtGui.QGuiApplication.screens()
        if screen_index >= len(screens):
            return

        self.screen_index = screen_index
        self.bar_position = position
        
        # Update screen dimensions for current screen
        screen_geom = screens[self.screen_index].geometry()
        self.screen_width = screen_geom.width()
        self.screen_x = screen_geom.x()
        self.screen_y = screen_geom.y()
        
        # Set to slim geometry initially
        slim_rect = self.get_slim_geometry()
        self.setGeometry(slim_rect)
        
        self.update()

    def get_slim_geometry(self):
        """Get the geometry for slim (collapsed) state based on current position"""
        screens = QtGui.QGuiApplication.screens()
        if self.screen_index >= len(screens):
            return QtCore.QRect(0, 0, 100, 5)  # fallback
        
        geom = screens[self.screen_index].geometry()
        width = geom.width()
        height = geom.height()
        x = geom.x()
        y = geom.y()
        
        if self.bar_position == 'top':
            return QtCore.QRect(x, y, width, self.slim_height)
        elif self.bar_position == 'bottom':
            return QtCore.QRect(x, y + height - self.slim_height, width, self.slim_height)
        elif self.bar_position == 'left':
            return QtCore.QRect(x, y, self.slim_height, height)
        elif self.bar_position == 'right':
            return QtCore.QRect(x + width - self.slim_height, y, self.slim_height, height)
        
        return QtCore.QRect(x, y, width, self.slim_height)  # default to top

    def get_full_geometry(self):
        """Get the geometry for full (expanded) state based on current position"""
        screens = QtGui.QGuiApplication.screens()
        if self.screen_index >= len(screens):
            return QtCore.QRect(0, 0, 100, 30)  # fallback
        
        geom = screens[self.screen_index].geometry()
        width = geom.width()
        height = geom.height()
        x = geom.x()
        y = geom.y()
        
        if self.bar_position == 'top':
            return QtCore.QRect(x, y, width, self.full_height)
        elif self.bar_position == 'bottom':
            return QtCore.QRect(x, y + height - self.full_height, width, self.full_height)
        elif self.bar_position == 'left':
            return QtCore.QRect(x, y, self.full_height, height)
        elif self.bar_position == 'right':
            return QtCore.QRect(x + width - self.full_height, y, self.full_height, height)
        
        return QtCore.QRect(x, y, width, self.full_height)  # default to top





def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    clock_bar = AnimatedToggleClockBar()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
