from PySide6 import QtWidgets

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, screens=None, current_index=0, position='top'):
        super().__init__(parent)
        self.setWindowTitle("Linear Clock Settings")
        self.setFixedSize(300, 160)

        self.selected_index = current_index
        self.selected_position = position

        layout = QtWidgets.QVBoxLayout(self)

        # Screen selector
        self.screen_combo = QtWidgets.QComboBox()
        for i, screen in enumerate(screens):
            geom = screen.geometry()
            self.screen_combo.addItem(f"Screen {i}: {screen.name()} ({geom.width()}x{geom.height()})")
        self.screen_combo.setCurrentIndex(current_index)

        layout.addWidget(QtWidgets.QLabel("Select screen:"))
        layout.addWidget(self.screen_combo)

        # Position selector
        self.position_combo = QtWidgets.QComboBox()
        self.position_combo.addItems(["top", "bottom", "left", "right"])
        self.position_combo.setCurrentText(position)

        layout.addWidget(QtWidgets.QLabel("Bar position:"))
        layout.addWidget(self.position_combo)

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_settings(self):
        return self.screen_combo.currentIndex(), self.position_combo.currentText()
