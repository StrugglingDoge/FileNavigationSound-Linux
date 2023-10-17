
## Navigation Sound Monitor for File Managers

### Overview

This script is designed to play a navigation sound effect when navigating folders in file managers such as Dolphin. The script makes use of `dbus-monitor` to listen for folder navigation events and uses `pygame` to play the sound effect.

[![ File Navigation Sound Monitor for Linux Example](https://markdown-videos-api.jorgenkh.no/url?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D2LNA1qM3C0M)](https://www.youtube.com/watch?v=2LNA1qM3C0M)

### Prerequisites

1. Python 3.x
2. `pygame` module: Can be installed using `pip install pygame`
3. `psutil` module: Can be installed using `pip install psutil`
4. `dbus-monitor`: Typically available on KDE-based systems.

### Setup

1. Clone or download the script.
2. (Optional) Modify the `DEFAULT_SOUND_EFFECT` and `DEFAULT_APP_NAME` constants at the top of the script if you wish to set a different default sound effect or application name. This can be useful for auto-starting the script.

### Usage

Run the script using the following command:

```
python3 script_name.py [OPTIONS]
```

#### Options:

- `--debug`: Enable debug messages.
- `--sound-path`: Path to the sound effect file. If not specified, the default path is used.
- `--app-name`: Name of the application to monitor. If not specified, "dolphin" is used by default.

#### Examples:

1. To monitor Dolphin with a custom sound:
```
python3 script_name.py --sound-path /path/to/custom_sound.wav
```

2. To monitor a different file manager (e.g., Nautilus):
```
python3 script_name.py --app-name nautilus
```

### Contribution

Feel free to contribute to this project by opening issues or submitting pull requests.

