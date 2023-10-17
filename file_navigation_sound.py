"""
MIT License

Copyright (c) 2023 Carson Kelley

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import subprocess
import re
import pygame
import os
import psutil
import argparse
import logging
import asyncio
import signal
from threading import Thread

# The default sound effect to play when navigating to a new directory
DEFAULT_SOUND_EFFECT = "./navigation.wav"

# The default application name to monitor
DEFAULT_APP_NAME = "dolphin"


class DolphinMonitor:
    def __init__(self, sound_effect=DEFAULT_SOUND_EFFECT, app_name=DEFAULT_APP_NAME, debug=False):
        """
        Initialize the monitor.

        Args:
        - sound_effect (str): Path to the sound effect to play.
        - app_name (str): Name of the application to monitor.
        - debug (bool): Whether to show debug messages.
        """
        self.debug = debug
        self.app_name = app_name
        self.cmd = [
            'dbus-monitor',
            "--session",
            f"type='method_call',interface='org.kde.ActivityManager.Resources',member='RegisterResourceEvent'"
        ]
        self.process = None
        pygame.mixer.init()
        self.sound = pygame.mixer.Sound(sound_effect)

        # States
        self.state = "InitialState"
        self.last_directory = None

    def stop(self):
        """Gracefully stop the monitor."""
        if self.process:
            self.process.terminate()
            self.process = None
        pygame.mixer.quit()

    def is_directory(self, path):
        """Check if the given path is a directory."""
        return os.path.isdir(path)

    def get_app_pids(self):
        """Retrieve process IDs of the target application."""
        return {proc.info['pid'] for proc in psutil.process_iter(attrs=['pid', 'name']) if
                self.app_name in proc.info['name']}

    def extract_app_event(self, lines):
        """Extract the application event details from the given lines."""
        app_call = {
            'application': None,
            'app_uint': None,
            'file_path': None,
            'file_uint': None
        }

        for data_line in lines:
            if f"string \"{self.app_name}\"" in data_line:
                app_call['application'] = self.app_name
                next_line_match = re.search('uint32 (\d+)', lines[lines.index(data_line) + 1])
                if next_line_match:
                    app_call['app_uint'] = int(next_line_match.group(1))
            elif "string" in data_line:
                file_path_match = re.search('file://(.*)"', data_line)
                if file_path_match is None:
                    file_path_match = re.search('trash:/(.*)"', data_line)
                    if file_path_match is None or file_path_match.group(1).strip() == "":
                        continue
                    app_call['file_path'] = "trash://" + file_path_match.group(1).strip()
                    app_call['file_uint'] = int(re.search('uint32 (\d+)', lines[lines.index(data_line) + 1]).group(1))
                elif file_path_match:
                    app_call['file_path'] = file_path_match.group(1).strip()
                    next_line_match = re.search('uint32 (\d+)', lines[lines.index(data_line) + 1])
                    if next_line_match:
                        app_call['file_uint'] = int(next_line_match.group(1))

        if app_call['file_path'] is not None and not self.is_directory(app_call['file_path']):
            app_call['file_path'] = os.path.dirname(app_call['file_path'])

        return app_call

    def handle_app_event(self, event):
        """Handle the application event."""
        if not event['application'] or event['application'] != self.app_name:
            return

        if self.state == "InitialState" and event['file_uint'] == 3 and event['file_path'] != self.last_directory:
            self.last_directory = event['file_path']
            self.play_sound()
            self.state = "SoundPlayedState"
            if self.debug:
                logging.info(f"Transitioned to {self.state} due to event: {event}")

        elif (self.state == "WaitingForNewDirState" and event['file_uint'] in [1, 3] and self.last_directory
              != event['file_path']):
            self.last_directory = event['file_path']
            if self.debug:
                logging.info(f"Playing sound due to event: {event}")
            self.play_sound()
            self.state = "SoundPlayedState"
            if self.debug:
                logging.info(f"Transitioned to {self.state} due to event: {event}")

        elif self.state == "SoundPlayedState":
            self.state = "InitialState"
            if self.debug:
                logging.info(f"Transitioned back to {self.state}")

    def play_sound(self):
        """Play the sound effect in a new thread."""
        if self.debug:
            logging.info("Playing sound effect")
        Thread(target=self._play_sound_thread).start()

    def _play_sound_thread(self):
        """Thread function to play the sound effect."""
        if pygame.mixer.get_busy():
            pygame.mixer.stop()
        self.sound.play()

    async def monitor(self):
        """Monitor the application for navigation events and play sound effects accordingly."""
        self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1,
                                        universal_newlines=True)
        known_app_pids = self.get_app_pids()

        cached_method_call = ""

        call_data = []
        while True:
            if cached_method_call != "":
                line = cached_method_call
                cached_method_call = ""
            else:
                line = self.process.stdout.readline()

            current_app_pids = self.get_app_pids()
            new_pids = current_app_pids - known_app_pids
            closed_pids = known_app_pids - current_app_pids

            if closed_pids or new_pids:
                if self.debug:
                    logging.info("Application instance change detected, reinitializing...")
                await asyncio.sleep(0.5)
                # Terminate and restart the monitoring process
                if self.process:
                    self.process.terminate()
                    self.process = None
                    await asyncio.sleep(0.1)
                return await self.monitor()  # Recursively restart monitoring

            if "method call" in line:
                call_data = [line]
                while True:
                    sub_line = self.process.stdout.readline()
                    if "method call" in sub_line:
                        cached_method_call = sub_line
                        break
                    call_data.append(sub_line)

                # Debounce events
                await asyncio.sleep(0.03)

                event = self.extract_app_event(call_data)
                if self.debug:
                    logging.info(f"Processed event: {event}")
                self.handle_app_event(event)


def main():
    """Main function to execute the monitor."""
    monitor = DolphinMonitor(sound_effect=args.sound_path, app_name=args.app_name, debug=args.debug)
    try:
        asyncio.run(monitor.monitor())
    except Exception as e:
        # Log the exception and restart the monitor after a delay
        logging.error(f"An error occurred: {e}. Restarting in 5 seconds...")
        asyncio.sleep(5)
        main()
    except KeyboardInterrupt:
        # Handle manual interruption (Ctrl+C)
        logging.info("Received KeyboardInterrupt. Shutting down gracefully...")
    finally:
        # Ensure everything is cleaned up properly
        monitor.stop()


def handle_signal(signum, frame):
    """Signal handler to gracefully shut down."""
    logging.info(f"Received signal {signum}. Shutting down gracefully...")
    raise SystemExit


if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    parser = argparse.ArgumentParser(description='Monitor and play sound effects for application navigation events.')
    parser.add_argument('--debug', action='store_true', help='Enable debug messages')
    parser.add_argument('--sound-path', default=DEFAULT_SOUND_EFFECT, help='Path to the sound effect file.')
    parser.add_argument('--app-name', default=DEFAULT_APP_NAME, help='Name of the application to monitor.')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.INFO)

    # Start the main execution
    main()
