# Linear Clock

A sleek clock bar that displays the progress of your day as a linear timeline across your screen edge. Perfect for time awareness and task management (for my time blind folks).

## Requirements

- Python 3.7+
- PySide6

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/RadicalDreamer-Code/linear-clock.git
   cd linear-clock
   ```

2. **Install dependencies:**

   ```bash
   pip install PySide6
   ```

   Or if you have a requirements.txt file:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Starting the Application

```bash
python main.py
```

The application will start and display a thin bar at the top of your primary monitor.

### Using the Clock

1. **View progress**: The green bar shows how much of the day has passed
2. **Create tasks**: Double-click anywhere on the bar to create a task at that time position
3. **Edit tasks**: Click on red task markers to edit or delete existing tasks
4. **View task details**: Hover over red markers to see task time and name
5. **Change settings**: Right-click the system tray icon and select "Settings"

### Task Management

- **Creating**: Double-click on the bar → time is pre-filled based on click position → enter task name
- **Editing**: Click on a red task marker → modify time/name or delete the task
- **Notifications**: When the progress bar reaches a task marker, you'll get a system notification

### Settings

Access settings via the system tray icon:

- **Monitor selection**: Choose which screen to display the clock on
- **Position**: Place the bar on top, bottom, left, or right edge
- **Close**: Exit the application

## System Tray

The application runs in the system tray with these options:

- **Settings**: Configure monitor and position
- **Close**: Exit the application
