#!/usr/bin/env python3

import RPi.GPIO as GPIO
import time
import os
from music_player import MPDController

# Keypad configuration
PINS_ROWS = [6, 13, 19, 26]    # Physical pins: 31, 33, 35, 37
PINS_COLS = [12, 16, 20, 21]   # Physical pins: 32, 36, 38, 40

KEY_ARRAY = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']
]

def read_keypad(row_pins, col_pins, key_map):
    """Scan keypad matrix and return pressed key"""
    # Set all rows LOW initially
    for row_pin in row_pins:
        GPIO.setup(row_pin, GPIO.OUT)
        GPIO.output(row_pin, GPIO.LOW)
    
    # Set all columns as inputs with pull-down
    for col_pin in col_pins:
        GPIO.setup(col_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    # Scan each row
    for i, row_pin in enumerate(row_pins):
        # Set current row HIGH
        GPIO.output(row_pin, GPIO.HIGH)
        
        # Check each column
        for j, col_pin in enumerate(col_pins):
            if GPIO.input(col_pin) == GPIO.HIGH:
                time.sleep(0.02)  # Debounce
                if GPIO.input(col_pin) == GPIO.HIGH:
                    key = key_map[i][j]
                    GPIO.output(row_pin, GPIO.LOW)  # Reset row before returning
                    print(f"Key Pressed: {key}")
                    return key
        
        # Reset current row LOW
        GPIO.output(row_pin, GPIO.LOW)
    
    return None

def load_radio_playlist():
    """Load radio.m3u playlist and return station info"""
    station_names = []
    station_urls = []
    
    filename = "/var/lib/mpd/playlists/radio.m3u"
    try:
        with open(filename) as playlist:
            lines = [line.rstrip() for line in playlist]
            for line in lines:
                if line.startswith("#EXTINF"):
                    station = line.split(",", 1)  # Split only on first comma
                    station_names.append(station[1] if len(station) > 1 else "Unknown Station")
                elif line.startswith("http"):
                    station_urls.append(line)  # URLs
    except FileNotFoundError:
        print(f"Error: Could not find playlist file {filename}")
        return [], []
    
    return station_names, station_urls

def main():
    # Initialize GPIO
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    
    # Initialize GPIO pins once to prevent conflicts
    for pin in PINS_ROWS + PINS_COLS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    # Load radio stations
    station_names, station_urls = load_radio_playlist()
    
    print("*" * 20)
    print("🎧 Radio Controller - Starting...")
    print(f"Loaded {len(station_names)} radio stations")
    print("*" * 20)
    
    try:
        print("Radio controller ready. Press Ctrl+C to exit.\n")
        print("Keys: 1-9=Select Station, A=Next, B=Prev, C=Play/Pause, D=Info, */#=Volume")
        
        while True:
            key = read_keypad(PINS_ROWS, PINS_COLS, KEY_ARRAY)
            
            if key:
                try:
                    # Number keys 1-9: Select station
                    if key.isdigit() and key != '0':
                        idx = int(key) - 1  # Convert to 0-based index
                        if 0 <= idx < len(station_urls):
                            url = station_urls[idx]
                            station = station_names[idx] if idx < len(station_names) else f"Station {idx+1}"
                            print(f"🎵 Playing: {station}")
                            
                            with MPDController() as controller:
                                controller.client.clear()
                                controller.client.add(url)
                                controller.client.play(0)
                                controller.get_current_track_info()
                        else:
                            print(f"Invalid station {idx+1}. Available: 1-{len(station_names)}")
                    
                    # Control keys
                    elif key == 'A':  # Next track
                        with MPDController() as controller:
                            controller.skip_track('next')
                    elif key == 'B':  # Previous track
                        with MPDController() as controller:
                            controller.skip_track('prev')
                    elif key == 'C':  # Play/Pause
                        with MPDController() as controller:
                            controller.toggle_pause()
                    elif key == 'D':  # Info
                        with MPDController() as controller:
                            controller.get_current_track_info()
                    elif key == '*':  # Volume down
                        with MPDController() as controller:
                            status = controller.client.status()
                            current_vol = int(status.get('volume', 50))
                            new_vol = max(0, current_vol - 5)
                            controller.set_volume(new_vol)
                            print(f"🔊 Volume: {new_vol}%")
                    elif key == '#':  # Volume up
                        with MPDController() as controller:
                            status = controller.client.status()
                            current_vol = int(status.get('volume', 50))
                            new_vol = min(100, current_vol + 5)
                            controller.set_volume(new_vol)
                            print(f"🔊 Volume: {new_vol}%")
                    elif key == '0':  # Exit
                        print("Exiting...")
                        break
                        
                except Exception as e:
                    print(f"Error handling key {key}: {e}")
                    
            time.sleep(0.02)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        GPIO.cleanup()
        print("Cleanup complete. Goodbye!")

if __name__ == "__main__":
    main()
