from PySide6 import QtCore, QtGui, QtWidgets
import datetime

class TaskDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, initial_time=None, task_name="", task_id=None):
        super().__init__(parent)
        self.task_id = task_id
        self.setWindowTitle("Add Task" if task_id is None else "Edit Task")
        self.setModal(True)
        self.setFixedSize(300, 150)
        
        # Set initial time to current time if not provided
        if initial_time is None:
            initial_time = datetime.datetime.now().time()
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Time input
        time_layout = QtWidgets.QHBoxLayout()
        time_layout.addWidget(QtWidgets.QLabel("Time:"))
        
        self.time_edit = QtWidgets.QTimeEdit()
        self.time_edit.setTime(QtCore.QTime(initial_time.hour, initial_time.minute, initial_time.second))
        self.time_edit.setDisplayFormat("HH:mm:ss")
        time_layout.addWidget(self.time_edit)
        
        layout.addLayout(time_layout)
        
        # Task name input
        name_layout = QtWidgets.QHBoxLayout()
        name_layout.addWidget(QtWidgets.QLabel("Task:"))
        
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setText(task_name)
        self.name_edit.setPlaceholderText("Enter task name...")
        name_layout.addWidget(self.name_edit)
        
        layout.addLayout(name_layout)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        if task_id is not None:
            delete_button = QtWidgets.QPushButton("Delete")
            delete_button.clicked.connect(self.delete_task)
            button_layout.addWidget(delete_button)
        
        button_layout.addStretch()
        
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        ok_button = QtWidgets.QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
        
        # Focus on name edit
        self.name_edit.setFocus()
        self.name_edit.selectAll()
        
        self.deleted = False
    
    def delete_task(self):
        reply = QtWidgets.QMessageBox.question(
            self, 
            "Delete Task", 
            "Are you sure you want to delete this task?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            self.deleted = True
            self.accept()
    
    def get_task_data(self):
        """Returns (time_object, task_name, deleted)"""
        qt_time = self.time_edit.time()
        time_obj = datetime.time(qt_time.hour(), qt_time.minute(), qt_time.second())
        return time_obj, self.name_edit.text().strip(), self.deleted
