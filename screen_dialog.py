from PySide6 import QtWidgets, QtCore
import datetime

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, screens=None, current_index=0, position='top', start_time=None, end_time=None, 
                 task_dragging_enabled=True, drag_snap_seconds=10):
        super().__init__(parent)
        self.setWindowTitle("Linear Clock Settings")
        self.setFixedSize(400, 350)

        self.selected_index = current_index
        self.selected_position = position

        # Default times if not provided
        if start_time is None:
            start_time = datetime.time(0, 0, 0)  # 00:00:00
        if end_time is None:
            end_time = datetime.time(23, 59, 59)  # 23:59:59

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

        # Time range settings
        time_group = QtWidgets.QGroupBox("Time Range")
        time_layout = QtWidgets.QFormLayout(time_group)

        # Start time
        self.start_time_edit = QtWidgets.QTimeEdit()
        self.start_time_edit.setTime(QtCore.QTime(start_time.hour, start_time.minute, start_time.second))
        self.start_time_edit.setDisplayFormat("HH:mm:ss")
        time_layout.addRow("Start time:", self.start_time_edit)

        # End time
        self.end_time_edit = QtWidgets.QTimeEdit()
        self.end_time_edit.setTime(QtCore.QTime(end_time.hour, end_time.minute, end_time.second))
        self.end_time_edit.setDisplayFormat("HH:mm:ss")
        time_layout.addRow("End time:", self.end_time_edit)

        # Info label
        info_label = QtWidgets.QLabel("Note: End time can be next day (e.g., 6:00 to 6:00 = 24h cycle)")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        time_layout.addRow(info_label)

        layout.addWidget(time_group)

        # Task dragging settings
        drag_group = QtWidgets.QGroupBox("Task Dragging")
        drag_layout = QtWidgets.QFormLayout(drag_group)

        # Enable task dragging checkbox
        self.drag_enabled_checkbox = QtWidgets.QCheckBox()
        self.drag_enabled_checkbox.setChecked(task_dragging_enabled)
        drag_layout.addRow("Enable task dragging:", self.drag_enabled_checkbox)

        # Snap interval spinbox
        self.snap_interval_spinbox = QtWidgets.QSpinBox()
        self.snap_interval_spinbox.setRange(1, 300)  # 1 second to 5 minutes
        self.snap_interval_spinbox.setValue(drag_snap_seconds)
        self.snap_interval_spinbox.setSuffix(" seconds")
        drag_layout.addRow("Snap interval:", self.snap_interval_spinbox)

        # Info label for dragging
        drag_info_label = QtWidgets.QLabel("Drag tasks to different times. Tasks snap to the configured interval.")
        drag_info_label.setWordWrap(True)
        drag_info_label.setStyleSheet("color: gray; font-size: 10px;")
        drag_layout.addRow(drag_info_label)

        layout.addWidget(drag_group)

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_settings(self):
        # Convert QTime back to datetime.time
        qt_start = self.start_time_edit.time()
        qt_end = self.end_time_edit.time()
        
        start_time = datetime.time(qt_start.hour(), qt_start.minute(), qt_start.second())
        end_time = datetime.time(qt_end.hour(), qt_end.minute(), qt_end.second())
        
        return (self.screen_combo.currentIndex(), self.position_combo.currentText(), start_time, end_time,
                self.drag_enabled_checkbox.isChecked(), self.snap_interval_spinbox.value())
