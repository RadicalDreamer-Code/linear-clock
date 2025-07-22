import sys
import datetime
from PySide6 import QtCore, QtGui, QtWidgets
import uuid

from screen_dialog import SettingsDialog
from task_dialog import TaskDialog

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
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Enable keyboard focus to receive key events
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        
        # Task management
        self.hover_task_id = None  # Track which task is being hovered over
        self.tooltip_timer = QtCore.QTimer()
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self.show_task_tooltip)
        
        # Click handling
        self.click_timer = QtCore.QTimer()
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self.handle_single_click)
        self.pending_click_pos = None

        # Animation setup
        self.animation = QtCore.QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(250)  # 250 ms animation
        self.animation.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)

        self.create_tray_icon()

        self.show()

    def update_clock(self):
        """Update the clock and check for task notifications"""
        now = datetime.datetime.now()
        current_time = now.time()
        
        # Check if focused task time has been reached
        if self.is_focused and self.focused_task_time:
            time_info = self.get_time_range_info()
            # Check if we've reached the end of the focused time range (task time)
            if time_info['progress'] >= 0.99:  # Close to end of range
                self.exit_focus_mode()
        
        # Check for task notifications
        self.check_task_notifications(current_time)
        
        # Update tray icon tooltip
        self.update_tray_tooltip()
        
        # Update the widget
        self.update()

    def update_tray_tooltip(self):
        """Update the tray icon tooltip with current status"""
        if hasattr(self, 'tray_icon') and self.tray_icon:
            tooltip_text = "Linear Clock"
            if self.is_focused and self.focused_task_id in self.tasks:
                task_name = self.tasks[self.focused_task_id]['name']
                task_time = self.focused_task_time.strftime("%H:%M:%S")
                tooltip_text += f" (Focused: {task_name} at {task_time})"
            
            self.tray_icon.setToolTip(tooltip_text)

    def check_task_notifications(self, current_time):
        """Check if any tasks should trigger notifications"""
        # Only check for notifications if current time is within the configured range
        if not self.is_time_in_range(current_time):
            return
            
        current_progress = self.get_time_range_info()['progress']
            
        for task_id, task_data in self.tasks.items():
            if task_id not in self.notified_tasks:
                task_time = task_data['time']
                
                # Only notify for tasks within the configured time range
                if not self.is_time_in_range(task_time):
                    continue
                
                task_progress = self.time_to_progress(task_time)
                
                # Check if current progress has reached or passed the task progress
                # Use a small tolerance to handle timer resolution (equivalent to ~1 second)
                time_info = self.get_time_range_info()
                tolerance = 1.0 / time_info['total_duration'] if time_info['total_duration'] > 0 else 0.001
                
                if abs(current_progress - task_progress) <= tolerance:
                    self.show_task_notification(task_data['name'], task_time)
                    self.notified_tasks.add(task_id)

    def show_task_notification(self, task_name, task_time):
        """Show a system tray notification for a task"""
        if hasattr(self, 'tray_icon') and self.tray_icon:
            time_str = task_time.strftime("%H:%M:%S")
            self.tray_icon.showMessage(
                "Task Reminder",
                f"{time_str} - {task_name}",
                QtWidgets.QSystemTrayIcon.Information,
                5000  # 5 seconds
            )

    def load_settings(self):
        """Load settings from QSettings or use defaults"""
        self.screen_index = self.settings.value("screen_index", 0, type=int)
        self.bar_position = self.settings.value("bar_position", "top", type=str)
        
        # Load time range settings
        start_time_str = self.settings.value("start_time", "00:00:00", type=str)
        end_time_str = self.settings.value("end_time", "23:59:59", type=str)
        
        try:
            self.start_time = datetime.time.fromisoformat(start_time_str)
            self.end_time = datetime.time.fromisoformat(end_time_str)
        except ValueError:
            # Fallback to default times if parsing fails
            self.start_time = datetime.time(0, 0, 0)
            self.end_time = datetime.time(23, 59, 59)
        
        # Focus feature variables
        self.is_focused = False
        self.original_start_time = None
        self.original_end_time = None
        self.focused_task_id = None
        self.focused_task_time = None
        
        # Initialize tasks for today
        self.tasks = {}  # Dictionary: task_id -> {'time': time_obj, 'name': str}
        self.notified_tasks = set()  # Track tasks that have already been notified
        self.load_tasks()

    def load_tasks(self):
        """Load tasks for today from QSettings"""
        today = datetime.date.today().isoformat()
        
        # Reset notified tasks when loading (e.g., new day or app restart)
        self.notified_tasks.clear()
        
        size = self.settings.beginReadArray(f"tasks_{today}")
        for i in range(size):
            self.settings.setArrayIndex(i)
            task_id = self.settings.value("id", type=str)
            time_str = self.settings.value("time", type=str)
            name = self.settings.value("name", type=str)
            
            if task_id and time_str and name:
                try:
                    time_obj = datetime.time.fromisoformat(time_str)
                    self.tasks[task_id] = {'time': time_obj, 'name': name}
                    
                    # Check if task time has already passed within the configured time range
                    if self.is_time_in_range(time_obj):
                        now = datetime.datetime.now().time()
                        if self.is_time_in_range(now):
                            # Both task and current time are in range, compare progress
                            current_progress = self.get_time_range_info()['progress']
                            task_progress = self.time_to_progress(time_obj)
                            
                            # If current progress has passed task progress, mark as notified
                            if current_progress > task_progress:
                                self.notified_tasks.add(task_id)
                        
                except ValueError:
                    pass  # Skip invalid time formats
        
        self.settings.endArray()

    def save_tasks(self):
        """Save current tasks to QSettings"""
        today = datetime.date.today().isoformat()
        self.settings.beginWriteArray(f"tasks_{today}")
        
        for i, (task_id, task_data) in enumerate(self.tasks.items()):
            self.settings.setArrayIndex(i)
            self.settings.setValue("id", task_id)
            self.settings.setValue("time", task_data['time'].isoformat())
            self.settings.setValue("name", task_data['name'])
        
        self.settings.endArray()
        self.settings.sync()

    def save_settings(self):
        """Save current settings to QSettings"""
        self.settings.setValue("screen_index", self.screen_index)
        self.settings.setValue("bar_position", self.bar_position)
        self.settings.setValue("start_time", self.start_time.isoformat())
        self.settings.setValue("end_time", self.end_time.isoformat())
        self.settings.sync()  # Ensure settings are written to disk

    def create_tray_icon(self):
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        icon = QtGui.QIcon.fromTheme("clock")
        if icon.isNull():
            icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)

        # Set the tooltip shown when you hover over the tray icon
        self.update_tray_tooltip()

        self.tray_icon.setVisible(True)

        menu = QtWidgets.QMenu()
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings)
        
        # Add import/export actions
        import_action = menu.addAction("Import Tasks from JSON...")
        import_action.triggered.connect(self.import_json_file_dialog)
        
        paste_action = menu.addAction("Paste JSON from Clipboard")
        paste_action.triggered.connect(self.paste_json_from_clipboard)
        
        export_action = menu.addAction("Export Tasks to JSON...")
        export_action.triggered.connect(self.export_json_file_dialog)
        
        menu.addSeparator()
        
        # Add focus mode actions to tray menu
        if self.is_focused:
            exit_focus_action = menu.addAction("Exit Focus Mode")
            exit_focus_action.triggered.connect(self.exit_focus_mode)

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

    def mouseDoubleClickEvent(self, event):
        """Handle double-click to create new task"""
        if event.button() == QtCore.Qt.LeftButton:
            # Cancel any pending single click
            self.click_timer.stop()
            self.pending_click_pos = None
            
            # Calculate time based on click position
            click_time = self.get_time_from_position(event.position())
            
            # Show task dialog
            dialog = TaskDialog(self, click_time)
            if dialog.exec() == QtWidgets.QDialog.Accepted:
                time_obj, task_name, _ = dialog.get_task_data()
                if task_name:  # Only add if name is not empty
                    task_id = str(uuid.uuid4())
                    self.tasks[task_id] = {'time': time_obj, 'name': task_name}
                    
                    # Check if task time has already passed within the configured time range
                    if self.is_time_in_range(time_obj):
                        now = datetime.datetime.now().time()
                        if self.is_time_in_range(now):
                            # Both task and current time are in range, compare progress
                            current_progress = self.get_time_range_info()['progress']
                            task_progress = self.time_to_progress(time_obj)
                            
                            # If current progress has passed task progress, mark as notified
                            if current_progress > task_progress:
                                self.notified_tasks.add(task_id)
                    
                    self.save_tasks()
                    self.update()
        
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        """Handle single click on task markers with delay to avoid conflict with double-click"""
        if event.button() == QtCore.Qt.LeftButton:
            # Store the click position and start timer
            self.pending_click_pos = event.position()
            self.click_timer.start(300)  # Wait 300ms to see if it's a double-click
            
            # Set focus to enable keyboard events (like Ctrl+V)
            self.setFocus()
        
        super().mousePressEvent(event)

    def handle_single_click(self):
        """Handle delayed single click"""
        if self.pending_click_pos is not None:
            task_id = self.get_task_at_position(self.pending_click_pos)
            if task_id:
                # Edit existing task
                task_data = self.tasks[task_id]
                dialog = TaskDialog(self, task_data['time'], task_data['name'], task_id)
                if dialog.exec() == QtWidgets.QDialog.Accepted:
                    time_obj, task_name, deleted = dialog.get_task_data()
                    if deleted:
                        del self.tasks[task_id]
                        self.notified_tasks.discard(task_id)  # Remove from notified set
                    elif task_name:  # Only update if name is not empty
                        self.tasks[task_id] = {'time': time_obj, 'name': task_name}
                        
                        # Reset notification state when task is modified
                        self.notified_tasks.discard(task_id)
                        
                        # Check if task time has already passed within the configured time range
                        if self.is_time_in_range(time_obj):
                            now = datetime.datetime.now().time()
                            if self.is_time_in_range(now):
                                # Both task and current time are in range, compare progress
                                current_progress = self.get_time_range_info()['progress']
                                task_progress = self.time_to_progress(time_obj)
                                
                                # If current progress has passed task progress, mark as notified
                                if current_progress > task_progress:
                                    self.notified_tasks.add(task_id)
                    else:
                        del self.tasks[task_id]  # Delete if name is empty
                        self.notified_tasks.discard(task_id)  # Remove from notified set
                    self.save_tasks()
                    self.update()
            
            self.pending_click_pos = None

    def mouseMoveEvent(self, event):
        """Handle mouse move for task tooltips"""
        task_id = self.get_task_at_position(event.position())
        
        if task_id != self.hover_task_id:
            self.hover_task_id = task_id
            QtWidgets.QToolTip.hideText()
            
            if task_id:
                self.tooltip_timer.start(500)  # Show tooltip after 500ms
            else:
                self.tooltip_timer.stop()
        
        super().mouseMoveEvent(event)

    def show_task_tooltip(self):
        """Show tooltip for hovered task"""
        if self.hover_task_id and self.hover_task_id in self.tasks:
            task_data = self.tasks[self.hover_task_id]
            tooltip_text = f"{task_data['time'].strftime('%H:%M:%S')} - {task_data['name']}"
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), tooltip_text, self)

    def get_time_from_position(self, pos):
        """Convert mouse position to time of day within the configured range"""
        rect = self.rect()
        
        if self.bar_position in ["top", "bottom"]:
            progress = pos.x() / rect.width()
        else:  # left or right
            progress = pos.y() / rect.height()
        
        # Clamp progress between 0 and 1
        progress = max(0, min(1, progress))
        
        # Convert progress to time within the configured range
        return self.progress_to_time(progress)

    def get_task_at_position(self, pos):
        """Get task ID at mouse position (if any)"""
        rect = self.rect()
        click_tolerance = 5  # pixels
        
        for task_id, task_data in self.tasks.items():
            task_time = task_data['time']
            task_progress = self.time_to_progress(task_time)
            
            if self.bar_position in ["top", "bottom"]:
                task_x = int(rect.width() * task_progress)
                if abs(pos.x() - task_x) <= click_tolerance:
                    return task_id
            else:  # left or right
                task_y = int(rect.height() * task_progress)
                if abs(pos.y() - task_y) <= click_tolerance:
                    return task_id
        
        return None

    def get_time_range_info(self):
        """Calculate time range duration and current progress"""
        now = datetime.datetime.now().time()
        
        # Convert times to seconds since midnight
        start_seconds = self.start_time.hour * 3600 + self.start_time.minute * 60 + self.start_time.second
        end_seconds = self.end_time.hour * 3600 + self.end_time.minute * 60 + self.end_time.second
        current_seconds = now.hour * 3600 + now.minute * 60 + now.second
        
        # Handle case where end time is next day (e.g., 18:00 to 06:00)
        if end_seconds <= start_seconds:
            # Range spans midnight
            total_duration = (24 * 3600 - start_seconds) + end_seconds
            
            if current_seconds >= start_seconds:
                # Current time is after start time (same day)
                elapsed = current_seconds - start_seconds
            else:
                # Current time is before end time (next day)
                elapsed = (24 * 3600 - start_seconds) + current_seconds
        else:
            # Normal range within same day
            total_duration = end_seconds - start_seconds
            elapsed = current_seconds - start_seconds
            
            # Clamp elapsed to valid range
            elapsed = max(0, min(elapsed, total_duration))
        
        # Calculate progress (0.0 to 1.0)
        if total_duration > 0:
            progress = elapsed / total_duration
        else:
            progress = 0.0
            
        return {
            'progress': max(0.0, min(1.0, progress)),
            'total_duration': total_duration,
            'elapsed': elapsed,
            'is_in_range': self.is_time_in_range(now)
        }

    def is_time_in_range(self, time_obj):
        """Check if a given time is within the configured time range"""
        time_seconds = time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
        start_seconds = self.start_time.hour * 3600 + self.start_time.minute * 60 + self.start_time.second
        end_seconds = self.end_time.hour * 3600 + self.end_time.minute * 60 + self.end_time.second
        
        if end_seconds <= start_seconds:
            # Range spans midnight
            return time_seconds >= start_seconds or time_seconds <= end_seconds
        else:
            # Normal range within same day
            return start_seconds <= time_seconds <= end_seconds

    def time_to_progress(self, time_obj):
        """Convert a time object to progress value (0.0 to 1.0) within the configured range"""
        time_seconds = time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
        start_seconds = self.start_time.hour * 3600 + self.start_time.minute * 60 + self.start_time.second
        end_seconds = self.end_time.hour * 3600 + self.end_time.minute * 60 + self.end_time.second
        
        if end_seconds <= start_seconds:
            # Range spans midnight
            total_duration = (24 * 3600 - start_seconds) + end_seconds
            
            if time_seconds >= start_seconds:
                elapsed = time_seconds - start_seconds
            else:
                elapsed = (24 * 3600 - start_seconds) + time_seconds
        else:
            # Normal range within same day
            total_duration = end_seconds - start_seconds
            elapsed = time_seconds - start_seconds
            elapsed = max(0, min(elapsed, total_duration))
        
        if total_duration > 0:
            return elapsed / total_duration
        return 0.0

    def progress_to_time(self, progress):
        """Convert progress value (0.0 to 1.0) to time object within the configured range"""
        progress = max(0.0, min(1.0, progress))
        
        start_seconds = self.start_time.hour * 3600 + self.start_time.minute * 60 + self.start_time.second
        end_seconds = self.end_time.hour * 3600 + self.end_time.minute * 60 + self.end_time.second
        
        if end_seconds <= start_seconds:
            # Range spans midnight
            total_duration = (24 * 3600 - start_seconds) + end_seconds
        else:
            # Normal range within same day
            total_duration = end_seconds - start_seconds
        
        elapsed_seconds = int(progress * total_duration)
        target_seconds = (start_seconds + elapsed_seconds) % (24 * 3600)
        
        hours = target_seconds // 3600
        minutes = (target_seconds % 3600) // 60
        seconds = target_seconds % 60
        
        return datetime.time(hours, minutes, seconds)

    def paintEvent(self, event):
        now = datetime.datetime.now()
        time_info = self.get_time_range_info()
        progress = time_info['progress']

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect()
        time_str = now.strftime("%H:%M:%S")

        # Fill entire widget area with transparent background to make it reactive to mouse events
        painter.setBrush(QtGui.QColor(0, 0, 0, 1))  # Almost transparent black
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(rect)

        # Choose bar color based on whether current time is in range
        if time_info['is_in_range']:
            bar_color = QtGui.QColor(0, 255, 0, 120)  # Transparent green (in range)
        else:
            bar_color = QtGui.QColor(128, 128, 128, 120)  # Transparent gray (out of range)

        # Draw the progress bar
        painter.setBrush(bar_color)
        painter.setPen(QtCore.Qt.NoPen)

        # Add visual indicator for focus mode
        if self.is_focused:
            # Draw a subtle border to indicate focus mode
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 0, 150), 2))  # Yellow border
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
            
            # Reset pen and brush for progress bar
            painter.setBrush(bar_color)
            painter.setPen(QtCore.Qt.NoPen)

        if self.bar_position in ["top", "bottom"]:
            fill_width = int(rect.width() * progress)
            painter.drawRect(0, 0, fill_width, rect.height())

            # Draw time centered only when fully expanded
            if rect.height() >= self.full_height:
                painter.setPen(QtGui.QColor("white"))
                font = QtGui.QFont("Arial", 12, QtGui.QFont.Bold)
                font.setPointSize(12)
                painter.setFont(font)
                painter.drawText(rect, QtCore.Qt.AlignCenter, time_str)

        elif self.bar_position == "left":
            fill_height = int(rect.height() * progress)
            painter.drawRect(0, 0, rect.width(), fill_height)

            # Rotate text vertically (bottom-up) only when fully expanded
            if rect.width() >= self.full_height:
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

            # Rotate text vertically (top-down) only when fully expanded
            if rect.width() >= self.full_height:
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

        # Draw task markers
        self.draw_task_markers(painter, rect)
        
        # Draw focus indicator for the focused task
        if self.is_focused and self.focused_task_id in self.tasks:
            self.draw_focus_indicator(painter, rect)

    def draw_task_markers(self, painter, rect):
        """Draw vertical lines for task markers"""
        if not self.tasks:
            return
        
        # Set up pen for task markers
        painter.setPen(QtGui.QPen(QtGui.QColor("red"), 2))
        
        for task_id, task_data in self.tasks.items():
            task_time = task_data['time']
            
            # Only show tasks that are within the configured time range
            if not self.is_time_in_range(task_time):
                continue
                
            task_progress = self.time_to_progress(task_time)
            
            if self.bar_position in ["top", "bottom"]:
                # Draw vertical line
                x = int(rect.width() * task_progress)
                painter.drawLine(x, 0, x, rect.height())
            else:  # left or right
                # Draw horizontal line
                y = int(rect.height() * task_progress)
                painter.drawLine(0, y, rect.width(), y)


    def open_settings(self):
        screens = QtGui.QGuiApplication.screens()
        dialog = SettingsDialog(self, screens=screens, current_index=self.screen_index, 
                               position=self.bar_position, start_time=self.start_time, end_time=self.end_time)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            selected_index, selected_position, start_time, end_time = dialog.get_settings()
            
            # Exit focus mode if settings are changed
            if self.is_focused:
                self.exit_focus_mode()
            
            self.bar_position = selected_position
            self.start_time = start_time
            self.end_time = end_time
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

    def focus_on_task(self, task_id):
        """Focus the time range from current time to the task time"""
        if task_id not in self.tasks:
            return
        
        task_time = self.tasks[task_id]['time']
        current_time = datetime.datetime.now().time()
        
        # Don't focus if task time has already passed
        current_seconds = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
        task_seconds = task_time.hour * 3600 + task_time.minute * 60 + task_time.second
        
        # Handle day boundary case
        if task_seconds < current_seconds:
            # Assume task is tomorrow if it's earlier in the day
            pass
        
        # Store original time range
        if not self.is_focused:
            self.original_start_time = self.start_time
            self.original_end_time = self.end_time
        
        # Set new focused time range
        self.start_time = current_time
        self.end_time = task_time
        self.is_focused = True
        self.focused_task_id = task_id
        self.focused_task_time = task_time
        
        # Reset notified tasks for the new range
        self.notified_tasks.clear()
        
        # Re-check notification states for tasks in the new range
        self.load_tasks()
        
        # Update display
        self.update()

    def exit_focus_mode(self):
        """Exit focus mode and restore original time range"""
        if not self.is_focused:
            return
        
        # Restore original time range
        self.start_time = self.original_start_time
        self.end_time = self.original_end_time
        
        # Clear focus state
        self.is_focused = False
        self.original_start_time = None
        self.original_end_time = None
        self.focused_task_id = None
        self.focused_task_time = None
        
        # Reset notified tasks for the restored range
        self.notified_tasks.clear()
        
        # Re-check notification states for tasks in the restored range
        self.load_tasks()
        
        # Update display
        self.update()

    def contextMenuEvent(self, event):
        """Handle right-click context menu for tasks"""
        task_id = self.get_task_at_position(event.pos())
        
        if task_id:
            menu = QtWidgets.QMenu(self)
            
            # Add focus action
            focus_action = menu.addAction("Focus on Task")
            focus_action.triggered.connect(lambda: self.focus_on_task(task_id))
            
            # Add exit focus action if currently focused
            if self.is_focused:
                exit_focus_action = menu.addAction("Exit Focus Mode")
                exit_focus_action.triggered.connect(self.exit_focus_mode)
            
            menu.addSeparator()
            
            # Add import/export actions to task context menu
            import_submenu = menu.addMenu("Import/Export")
            import_file_action = import_submenu.addAction("Import from JSON File...")
            import_file_action.triggered.connect(self.import_json_file_dialog)
            
            paste_clipboard_action = import_submenu.addAction("Paste JSON from Clipboard")
            paste_clipboard_action.triggered.connect(self.paste_json_from_clipboard)
            
            export_file_action = import_submenu.addAction("Export to JSON File...")
            export_file_action.triggered.connect(self.export_json_file_dialog)
            
            menu.addSeparator()
            
            # Add edit task action
            edit_action = menu.addAction("Edit Task")
            edit_action.triggered.connect(lambda: self.edit_task(task_id))
            
            # Add delete task action
            delete_action = menu.addAction("Delete Task")
            delete_action.triggered.connect(lambda: self.delete_task(task_id))
            
            menu.exec(event.globalPos())
        else:
            # If not clicking on a task and in focus mode, show exit focus option
            if self.is_focused:
                menu = QtWidgets.QMenu(self)
                exit_focus_action = menu.addAction("Exit Focus Mode")
                exit_focus_action.triggered.connect(self.exit_focus_mode)
                menu.addSeparator()
            else:
                menu = QtWidgets.QMenu(self)
            
            # Add import/export actions to general context menu
            import_submenu = menu.addMenu("Import/Export")
            import_file_action = import_submenu.addAction("Import from JSON File...")
            import_file_action.triggered.connect(self.import_json_file_dialog)
            
            paste_clipboard_action = import_submenu.addAction("Paste JSON from Clipboard (Ctrl+V)")
            paste_clipboard_action.triggered.connect(self.paste_json_from_clipboard)
            
            export_file_action = import_submenu.addAction("Export to JSON File...")
            export_file_action.triggered.connect(self.export_json_file_dialog)
            
            menu.exec(event.globalPos())

    def edit_task(self, task_id):
        """Edit an existing task"""
        if task_id not in self.tasks:
            return
        
        task_data = self.tasks[task_id]
        dialog = TaskDialog(self, task_data['time'], task_data['name'], task_id)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            time_obj, task_name, deleted = dialog.get_task_data()
            if deleted:
                del self.tasks[task_id]
                self.notified_tasks.discard(task_id)
                
                # If we're focused on this task, exit focus mode
                if self.is_focused and self.focused_task_id == task_id:
                    self.exit_focus_mode()
            elif task_name:
                self.tasks[task_id] = {'time': time_obj, 'name': task_name}
                
                # Reset notification state when task is modified
                self.notified_tasks.discard(task_id)
                
                # Update focused task time if this is the focused task
                if self.is_focused and self.focused_task_id == task_id:
                    self.focused_task_time = time_obj
                    self.end_time = time_obj
                
                # Check if task time has already passed within the configured time range
                if self.is_time_in_range(time_obj):
                    now = datetime.datetime.now().time()
                    if self.is_time_in_range(now):
                        current_progress = self.get_time_range_info()['progress']
                        task_progress = self.time_to_progress(time_obj)
                        
                        if current_progress > task_progress:
                            self.notified_tasks.add(task_id)
            else:
                del self.tasks[task_id]
                self.notified_tasks.discard(task_id)
                
                # If we're focused on this task, exit focus mode
                if self.is_focused and self.focused_task_id == task_id:
                    self.exit_focus_mode()
            
            self.save_tasks()
            self.update()

    def delete_task(self, task_id):
        """Delete a task after confirmation"""
        if task_id not in self.tasks:
            return
        
        task_data = self.tasks[task_id]
        reply = QtWidgets.QMessageBox.question(
            self, 
            "Delete Task", 
            f"Are you sure you want to delete the task '{task_data['name']}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            del self.tasks[task_id]
            self.notified_tasks.discard(task_id)
            
            # If we're focused on this task, exit focus mode
            if self.is_focused and self.focused_task_id == task_id:
                self.exit_focus_mode()
            
            self.save_tasks()
            self.update()

    def draw_focus_indicator(self, painter, rect):
        """Draw a special indicator for the focused task"""
        if not self.is_focused or self.focused_task_id not in self.tasks:
            return
        
        task_time = self.tasks[self.focused_task_id]['time']
        task_progress = self.time_to_progress(task_time)
        
        # Set up pen for focused task indicator (thicker, different color)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 0), 4))  # Yellow, thicker line
        
        if self.bar_position in ["top", "bottom"]:
            # Draw thick vertical line for focused task
            x = int(rect.width() * task_progress)
            painter.drawLine(x, 0, x, rect.height())
            
            # Draw small arrow pointing to the focused task
            arrow_size = 6
            if self.bar_position == "top":
                # Arrow pointing down
                points = [
                    QtCore.QPoint(x, rect.height()),
                    QtCore.QPoint(x - arrow_size, rect.height() - arrow_size),
                    QtCore.QPoint(x + arrow_size, rect.height() - arrow_size)
                ]
            else:  # bottom
                # Arrow pointing up
                points = [
                    QtCore.QPoint(x, 0),
                    QtCore.QPoint(x - arrow_size, arrow_size),
                    QtCore.QPoint(x + arrow_size, arrow_size)
                ]
            
            painter.setBrush(QtGui.QColor(255, 255, 0))
            painter.drawPolygon(points)
            
        else:  # left or right
            # Draw thick horizontal line for focused task
            y = int(rect.height() * task_progress)
            painter.drawLine(0, y, rect.width(), y)
            
            # Draw small arrow pointing to the focused task
            arrow_size = 6
            if self.bar_position == "left":
                # Arrow pointing right
                points = [
                    QtCore.QPoint(rect.width(), y),
                    QtCore.QPoint(rect.width() - arrow_size, y - arrow_size),
                    QtCore.QPoint(rect.width() - arrow_size, y + arrow_size)
                ]
            else:  # right
                # Arrow pointing left
                points = [
                    QtCore.QPoint(0, y),
                    QtCore.QPoint(arrow_size, y - arrow_size),
                    QtCore.QPoint(arrow_size, y + arrow_size)
                ]
            
            painter.setBrush(QtGui.QColor(255, 255, 0))
            painter.drawPolygon(points)

    def dragEnterEvent(self, event):
        """Handle drag enter event for JSON files"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith('.json'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move event"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith('.json'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        """Handle drop event for JSON files"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith('.json'):
                    self.import_tasks_from_json(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def import_tasks_from_json(self, file_path):
        """Import tasks from a JSON file"""
        try:
            import json
            
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Handle different JSON structures
            tasks_data = []
            
            if isinstance(data, list):
                # JSON is a list of tasks
                tasks_data = data
            elif isinstance(data, dict):
                # JSON is an object, look for common keys that might contain tasks
                if 'tasks' in data:
                    tasks_data = data['tasks']
                elif 'events' in data:
                    tasks_data = data['events']
                elif 'items' in data:
                    tasks_data = data['items']
                else:
                    # Treat the object itself as a single task
                    tasks_data = [data]
            
            imported_count = 0
            skipped_count = 0
            
            for task_data in tasks_data:
                if not isinstance(task_data, dict):
                    skipped_count += 1
                    continue
                
                # Extract name and time from the task data
                name = None
                time_str = None
                
                # Look for name field (try different common field names)
                for name_field in ['name', 'title', 'task', 'description', 'label']:
                    if name_field in task_data and task_data[name_field]:
                        name = str(task_data[name_field])
                        break
                
                # Look for time field (try different common field names)
                for time_field in ['time', 'start_time', 'start', 'datetime', 'timestamp']:
                    if time_field in task_data and task_data[time_field]:
                        time_str = str(task_data[time_field])
                        break
                
                if not name or not time_str:
                    skipped_count += 1
                    continue
                
                # Parse the time string
                time_obj = None
                try:
                    # Try different time formats
                    time_formats = [
                        "%H:%M:%S",      # HH:MM:SS
                        "%H:%M",         # HH:MM
                        "%I:%M:%S %p",   # 12-hour format with seconds
                        "%I:%M %p",      # 12-hour format without seconds
                        "%Y-%m-%d %H:%M:%S",  # Full datetime
                        "%Y-%m-%dT%H:%M:%S",  # ISO format
                    ]
                    
                    for fmt in time_formats:
                        try:
                            if 'T' in time_str or ' ' in time_str:
                                # Full datetime, extract time part
                                dt = datetime.datetime.strptime(time_str, fmt)
                                time_obj = dt.time()
                            else:
                                # Time only
                                dt = datetime.datetime.strptime(time_str, fmt)
                                time_obj = dt.time()
                            break
                        except ValueError:
                            continue
                    
                    if time_obj is None:
                        # Try parsing as ISO format time only
                        try:
                            time_obj = datetime.time.fromisoformat(time_str)
                        except ValueError:
                            pass
                
                except Exception:
                    pass
                
                if time_obj is None:
                    skipped_count += 1
                    continue
                
                # Add the task
                task_id = str(uuid.uuid4())
                self.tasks[task_id] = {'time': time_obj, 'name': name}
                
                # Check if task time has already passed within the configured time range
                if self.is_time_in_range(time_obj):
                    now = datetime.datetime.now().time()
                    if self.is_time_in_range(now):
                        # Both task and current time are in range, compare progress
                        current_progress = self.get_time_range_info()['progress']
                        task_progress = self.time_to_progress(time_obj)
                        
                        # If current progress has passed task progress, mark as notified
                        if current_progress > task_progress:
                            self.notified_tasks.add(task_id)
                
                imported_count += 1
            
            # Save tasks and update display
            if imported_count > 0:
                self.save_tasks()
                self.update()
            
            # Show result message
            if imported_count > 0 or skipped_count > 0:
                message = f"Import completed!\n\nImported: {imported_count} tasks"
                if skipped_count > 0:
                    message += f"\nSkipped: {skipped_count} entries (missing name or time)"
                
                QtWidgets.QMessageBox.information(
                    self,
                    "JSON Import",
                    message,
                    QtWidgets.QMessageBox.Ok
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "JSON Import",
                    "No valid tasks found in the JSON file.\n\nExpected format:\n- 'name' field for task name\n- 'time' field for task time",
                    QtWidgets.QMessageBox.Ok
                )
        
        except json.JSONDecodeError as e:
            QtWidgets.QMessageBox.critical(
                self,
                "JSON Import Error",
                f"Invalid JSON file format:\n{str(e)}",
                QtWidgets.QMessageBox.Ok
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Import Error",
                f"Error importing tasks from JSON file:\n{str(e)}",
                QtWidgets.QMessageBox.Ok
            )

    def import_json_file_dialog(self):
        """Open file dialog to import JSON file"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import Tasks from JSON",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.import_tasks_from_json(file_path)

    def export_json_file_dialog(self):
        """Open file dialog to export tasks to JSON file"""
        if not self.tasks:
            QtWidgets.QMessageBox.information(
                self,
                "Export Tasks",
                "No tasks to export.",
                QtWidgets.QMessageBox.Ok
            )
            return
        
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Tasks to JSON",
            f"tasks_{datetime.date.today().isoformat()}.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.export_tasks_to_json(file_path)

    def export_tasks_to_json(self, file_path):
        """Export current tasks to a JSON file"""
        try:
            import json
            
            # Prepare tasks data for export
            tasks_data = []
            for task_id, task_data in self.tasks.items():
                tasks_data.append({
                    "name": task_data['name'],
                    "time": task_data['time'].isoformat()
                })
            
            # Sort tasks by time
            tasks_data.sort(key=lambda x: x['time'])
            
            # Create export data
            export_data = {
                "tasks": tasks_data,
                "exported_date": datetime.date.today().isoformat(),
                "exported_time": datetime.datetime.now().time().isoformat(),
                "time_range": {
                    "start_time": self.start_time.isoformat() if not self.is_focused else self.original_start_time.isoformat(),
                    "end_time": self.end_time.isoformat() if not self.is_focused else self.original_end_time.isoformat()
                }
            }
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(export_data, file, indent=2, ensure_ascii=False)
            
            QtWidgets.QMessageBox.information(
                self,
                "Export Successful",
                f"Successfully exported {len(tasks_data)} tasks to:\n{file_path}",
                QtWidgets.QMessageBox.Ok
            )
        
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Export Error",
                f"Error exporting tasks to JSON file:\n{str(e)}",
                QtWidgets.QMessageBox.Ok
            )

    def keyPressEvent(self, event):
        """Handle key press events for clipboard paste"""
        if event.key() == QtCore.Qt.Key_V and event.modifiers() == QtCore.Qt.ControlModifier:
            # Ctrl+V pressed - paste JSON from clipboard
            self.paste_json_from_clipboard()
        else:
            super().keyPressEvent(event)

    def paste_json_from_clipboard(self):
        """Paste and import JSON content from clipboard"""
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard_text = clipboard.text()
        
        if not clipboard_text.strip():
            QtWidgets.QMessageBox.information(
                self,
                "Clipboard Paste",
                "Clipboard is empty or contains no text.",
                QtWidgets.QMessageBox.Ok
            )
            return
        
        try:
            import json
            
            # Try to parse the clipboard content as JSON
            data = json.loads(clipboard_text)
            
            # Handle different JSON structures (same as file import)
            tasks_data = []
            
            if isinstance(data, list):
                # JSON is a list of tasks
                tasks_data = data
            elif isinstance(data, dict):
                # JSON is an object, look for common keys that might contain tasks
                if 'tasks' in data:
                    tasks_data = data['tasks']
                elif 'events' in data:
                    tasks_data = data['events']
                elif 'items' in data:
                    tasks_data = data['items']
                else:
                    # Treat the object itself as a single task
                    tasks_data = [data]
            
            imported_count = 0
            skipped_count = 0
            
            for task_data in tasks_data:
                if not isinstance(task_data, dict):
                    skipped_count += 1
                    continue
                
                # Extract name and time from the task data
                name = None
                time_str = None
                
                # Look for name field (try different common field names)
                for name_field in ['name', 'title', 'task', 'description', 'label']:
                    if name_field in task_data and task_data[name_field]:
                        name = str(task_data[name_field])
                        break
                
                # Look for time field (try different common field names)
                for time_field in ['time', 'start_time', 'start', 'datetime', 'timestamp']:
                    if time_field in task_data and task_data[time_field]:
                        time_str = str(task_data[time_field])
                        break
                
                if not name or not time_str:
                    skipped_count += 1
                    continue
                
                # Parse the time string (same logic as file import)
                time_obj = None
                try:
                    # Try different time formats
                    time_formats = [
                        "%H:%M:%S",      # HH:MM:SS
                        "%H:%M",         # HH:MM
                        "%I:%M:%S %p",   # 12-hour format with seconds
                        "%I:%M %p",      # 12-hour format without seconds
                        "%Y-%m-%d %H:%M:%S",  # Full datetime
                        "%Y-%m-%dT%H:%M:%S",  # ISO format
                    ]
                    
                    for fmt in time_formats:
                        try:
                            if 'T' in time_str or ' ' in time_str:
                                # Full datetime, extract time part
                                dt = datetime.datetime.strptime(time_str, fmt)
                                time_obj = dt.time()
                            else:
                                # Time only
                                dt = datetime.datetime.strptime(time_str, fmt)
                                time_obj = dt.time()
                            break
                        except ValueError:
                            continue
                    
                    if time_obj is None:
                        # Try parsing as ISO format time only
                        try:
                            time_obj = datetime.time.fromisoformat(time_str)
                        except ValueError:
                            pass
                
                except Exception:
                    pass
                
                if time_obj is None:
                    skipped_count += 1
                    continue
                
                # Add the task
                task_id = str(uuid.uuid4())
                self.tasks[task_id] = {'time': time_obj, 'name': name}
                
                # Check if task time has already passed within the configured time range
                if self.is_time_in_range(time_obj):
                    now = datetime.datetime.now().time()
                    if self.is_time_in_range(now):
                        # Both task and current time are in range, compare progress
                        current_progress = self.get_time_range_info()['progress']
                        task_progress = self.time_to_progress(time_obj)
                        
                        # If current progress has passed task progress, mark as notified
                        if current_progress > task_progress:
                            self.notified_tasks.add(task_id)
                
                imported_count += 1
            
            # Save tasks and update display
            if imported_count > 0:
                self.save_tasks()
                self.update()
            
            # Show result message
            if imported_count > 0 or skipped_count > 0:
                message = f"Clipboard import completed!\n\nImported: {imported_count} tasks"
                if skipped_count > 0:
                    message += f"\nSkipped: {skipped_count} entries (missing name or time)"
                
                QtWidgets.QMessageBox.information(
                    self,
                    "Clipboard Import",
                    message,
                    QtWidgets.QMessageBox.Ok
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Clipboard Import",
                    "No valid tasks found in the clipboard JSON.\n\nExpected format:\n- 'name' field for task name\n- 'time' field for task time",
                    QtWidgets.QMessageBox.Ok
                )
        
        except json.JSONDecodeError as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Clipboard Import Error",
                f"Invalid JSON format in clipboard:\n{str(e)}\n\nMake sure you've copied valid JSON content.",
                QtWidgets.QMessageBox.Ok
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Import Error",
                f"Error importing tasks from clipboard:\n{str(e)}",
                QtWidgets.QMessageBox.Ok
            )


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    clock_bar = AnimatedToggleClockBar()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
