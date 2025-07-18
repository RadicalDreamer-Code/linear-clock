import sys
import datetime
from PySide6 import QtCore, QtGui, QtWidgets

class AnimatedToggleClockBar(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # screen = QtGui.QGuiApplication.primaryScreen().geometry()
        # self.screen_width = screen.width()
        # self.screen_x = screen.x()
        # self.screen_y = screen.y()

        screen_index = 1  # 0 - primary, 1 - secondary, etc.
        screens = QtGui.QGuiApplication.screens()

        if screen_index >= len(screens):
            screen_index = 0

        screen_geom = screens[screen_index].geometry()
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

    def open_settings(self):
        # Placeholder for future settings window
        QtWidgets.QMessageBox.information(self, "Settings", "Settings window not implemented yet.")

    def enterEvent(self, event):
        # Animate to full height
        target_rect = QtCore.QRect(self.screen_x, self.screen_y, self.screen_width, self.full_height)
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
            target_rect = QtCore.QRect(self.screen_x, self.screen_y, self.screen_width, self.slim_height)
            self.animation.stop()
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(target_rect)
            self.animation.start()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        now = datetime.datetime.now()
        seconds = now.hour * 3600 + now.minute * 60 + now.second
        ratio = seconds / (24 * 3600)
        width = self.width() * ratio

        # Draw semi-transparent green bar
        color = QtGui.QColor(0, 255, 0, 120)
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(0, 0, int(width), self.height())

        if self.height() > 20:
            time_str = now.strftime("%H:%M:%S")
            painter.setPen(QtGui.QColor(255, 255, 255))
            font = QtGui.QFont("Arial", 12, QtGui.QFont.Bold)
            painter.setFont(font)
            painter.drawText(self.rect(), QtCore.Qt.AlignCenter, time_str)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    clock_bar = AnimatedToggleClockBar()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
