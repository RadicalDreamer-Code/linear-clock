from PySide6 import QtWidgets

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, screens=None, current_index=0):
        super().__init__(parent)
        self.setWindowTitle("Linear Clock Settings")
        self.setFixedSize(300, 100)

        self.selected_index = current_index

        layout = QtWidgets.QVBoxLayout(self)

        self.combo = QtWidgets.QComboBox()
        for i, screen in enumerate(screens):
            geom = screen.geometry()
            self.combo.addItem(f"Screen {i}: {screen.name()} ({geom.width()}x{geom.height()})")
        self.combo.setCurrentIndex(current_index)
        layout.addWidget(QtWidgets.QLabel("Select screen:"))
        layout.addWidget(self.combo)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_selected_screen_index(self):
        return self.combo.currentIndex()
