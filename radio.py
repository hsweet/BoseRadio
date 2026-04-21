from music_player import MPDController
import RPi.GPIO as GPIO
import time
import os

os.system('clear')

# Keypad configuration
PINS_ROWS = [6, 13, 19, 26]    # Physical pins: 31, 33, 35, 37
PINS_COLS = [12, 16, 20, 21]   # Physical pins: 32, 36, 38, 40

# Initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Initialize GPIO pins once to prevent conflicts
for pin in PINS_ROWS + PINS_COLS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Initialize MPD controller
mpd = MPDController()
# Set initial volume
volume = 70
with mpd as m:
    m.set_volume(volume)  
   

# Get station names and urls
stationlist = []
commandlist = []
filename = "/var/lib/mpd/playlists/radio.m3u"
with open(filename) as playlist:
    lines = [line.rstrip() for line in playlist]
    for line in lines:
        if line.startswith("#EXTINF"):
            station = line.split(",", 1)  # Split only on first comma
            stationlist.append(station[1] if len(station) > 1 else "Unknown Station")
        elif line.startswith("http"):
            commandlist.append(line)  # URLs
print("*" * 20)
print(f"Loaded {len(stationlist)} radio stations")
print("*" * 20)

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

def new_volume(change):
    global volume
    volume = max(0, min(100, volume + change))  # Keep volume between 0-100
    with mpd as m:
        m.set_volume(volume)
    return volume

def main():
    print("*" * 20)
    print("🎧 Radio Controller - Starting...")
    print("*" * 20)
    
    try:
        print("Radio controller ready. Press Ctrl+C to exit.\n")
        print("Keys: 1-9,0=Stations, A=Next, B=Prev, C=Play/Pause, D=Load Radio, */#=Volume")
        
        while True:
            key = read_keypad(PINS_ROWS, PINS_COLS, KEY_ARRAY)
            
            if key:
                print(f"Key Pressed: {key}")
                try:
                    if key.isdigit():
                        idx = int(key) - 1  # Convert to 0-based index
                        if 0 <= idx < len(commandlist):
                            url = commandlist[idx]
                            station = stationlist[idx] if idx < len(stationlist) else f"Station {idx+1}"
                            print(f"🎵 Playing: {station}")
                            # Play the URL
                            with mpd as m:
                                m.client.clear()
                                m.client.add(url)
                                m.client.play(0)
                                m.get_current_track_info()
                    else:
                        # Map special keys to MPD commands
                        key_map = {
                            'A': ('skip_track', 'next'),
                            'B': ('skip_track', 'prev'),
                            'C': ('toggle_pause', None),
                            'D': ('load_saved_playlist', 'radio'),
                            '*': ('_volume', -5),
                            '#': ('_volume', 5)
                        }
                        if key in key_map:
                            cmd, arg = key_map[key]
                            if cmd == '_volume':  # Special case for volume adjustment
                                new_volume(arg)
                            else:
                                with mpd as m:
                                    method = getattr(m, cmd)
                                    if arg is not None:
                                        method(arg)
                                    else:
                                        method()
                                           
                    # Wait for key release
                    while read_keypad(PINS_ROWS, PINS_COLS, KEY_ARRAY) is not None:
                        time.sleep(0.02)
                        
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