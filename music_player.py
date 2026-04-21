import sys
import time
from mpd import MPDClient, MPDError
import readchar # Ensure you have installed: pip install readchar

class MPDController:
    """A reusable class to manage the connection and commands to the MPD server."""

    def __init__(self, host='localhost', port=6600, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client = MPDClient()
        self.client.timeout = self.timeout
        
    def __enter__(self):
        """Context manager entry: Connect to MPD."""
        try:
            self.client.connect(self.host, self.port)
            return self
        except ConnectionRefusedError:
            print(f"Error: Connection refused. Is MPD running on {self.host}:{self.port}?", file=sys.stderr)
            sys.exit(1)
        except MPDError as e:
            print(f"MPD Connection Error: {e}", file=sys.stderr)
            sys.exit(1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: Disconnect from MPD."""
        try:
            self.client.close()
            self.client.disconnect()
        except:
            pass 

    def _execute_command_list(self, commands):
        """Executes a list of MPD commands efficiently, handling arguments."""
        try:
            self.client.command_list_ok_begin()
            for command, arg in commands:
                if arg is None:
                    getattr(self.client, command)() 
                else:
                    getattr(self.client, command)(arg)
            self.client.command_list_end()
            return True
        except MPDError as e:
            print(f"MPD Command Error: {e}", file=sys.stderr)
            return False

    def _get_playlist_length(self):
        """Returns the current number of songs in the MPD queue."""
        try:
            status = self.client.status()
            return int(status.get('playlistlength', 0))
        except:
            return 0 

    # --- Core MPD Functionality ---

    def load_folder_and_play(self, folder_name):
        initial_length = self._get_playlist_length()
        commands = [('clear', None), ('add', folder_name)]
        
        if self._execute_command_list(commands):
            final_length = self._get_playlist_length()
            
            if final_length > initial_length:
                self.client.play(0) 
                print(f"✅ Folder '{folder_name}' loaded with {final_length} tracks and playback started.")
            else:
                print(f"❌ Error: Folder '{folder_name}' added 0 tracks. Check path or permissions.")
        else:
            print(f"❌ Failed to execute commands for folder: {folder_name}.")
            
    def load_saved_playlist(self, playlist_name):
        initial_length = self._get_playlist_length()
        commands = [('clear', None), ('load', playlist_name)]
        
        if self._execute_command_list(commands):
            final_length = self._get_playlist_length()
            
            if final_length > initial_length:
                self.client.play(0)
                print(f"📻 Playlist '{playlist_name}' loaded with {final_length} tracks and playback started.")
            else:
                print(f"❌ Error: Playlist '{playlist_name}' loaded, but contains no tracks.")
        else:
            print(f"❌ Failed to execute commands for playlist: {playlist_name}.")

    # --- Playback Control Methods ---

    def skip_track(self, direction='next'):
        try:
            if direction == 'prev':
                self.client.previous()
                print("⏪ Skipped to the previous track.")
            else:
                self.client.next()
                print("⏩ Skipped to the next track.")
        except MPDError as e:
            print(f"Control Error: Could not skip track: {e}")

    def toggle_pause(self):
        try:
            status = self.client.status()
            current_state = status.get('state')
            self.client.pause()
            
            if current_state == 'play':
                print("⏸️ Playback paused.")
            elif current_state == 'pause':
                print("▶️ Playback resumed.")
            else:
                print("⏯️ Pause/Play toggled.")
        except MPDError as e:
            print(f"Control Error: Could not toggle pause: {e}")
            
    def set_volume(self, level):
        """Sets the MPD volume (0-100) and confirms the new level."""
        print(f"Setting volume to {level}%")
        try:
            level = int(level)
            if 0 <= level <= 100:
                self.client.setvol(level)
                status = self.client.status()
                current_volume = status.get('volume', 'N/A')
                print(f"🔊 Volume set to {level}%. Current reported volume: {current_volume}%.")
                return (current_volume)
            else:
                print("⚠️ Volume level must be between 0 and 100.")
        except (ValueError, MPDError) as e:
            print(f"Control Error: Could not set volume: {e}")

    def get_current_track_info(self):
        """Retrieves and prints the artist and title of the currently playing song."""
        try:
            status = self.client.status()
            
            if status.get('state') in ('play', 'pause'):
                song_info = self.client.currentsong()
                
                title = song_info.get('title', 'Unknown Title')
                artist = song_info.get('artist', 'Unknown Artist')
                album = song_info.get('album', 'Unknown Album')
                
                print("\n🎵 Currently Playing:")
                print(f"  Title:  {title}")
                print(f"  Artist: {artist}")
                print(f"  Album:  {album}")
            else:
                print("🛑 MPD is not currently playing or paused.")
            
        except MPDError as e:
            print(f"Information Error: Could not retrieve song details: {e}")


# ----------------------------------------------------------------------
## 🔁 Command Mapping and Main Event Loop
# ----------------------------------------------------------------------

COMMAND_MAP = {
    # Playback Controls (e.g., Spacebar, n/p keys)
    ' ': ('toggle_pause', None),
    'n': ('skip_track', 'next'),
    'p': ('skip_track', 'prev'),
    
    # Volume Adjustment Keys (handled separately below)
    '+': ('volume_change', 5),       
    '-': ('volume_change', -5),      
    
    # Load Content Keys (e.g., 1 and 2 on the number pad)
    # NOTE: "/" should be the path *relative* to MPD's music_directory, 
    # which in your case appears to be the root.
    '1': ('load_folder_and_play', "/"),
    '2': ('load_saved_playlist', "radio"),
    
    # Information/Exit
    'i': ('get_current_track_info', None),
    'q': ('exit', None)           
}


if __name__ == "__main__":
    
    MUSIC_PATH = "/"  # Assuming your MPD's music_directory is configured to see this path
    RADIO_PLAYLIST = "radio"

    print("\n🎧 MPD Standalone Controller Started.")
    print("Keys: [Space] Play/Pause, [n/p] Next/Prev, [+/-] Volume, [1/2] Load, [q] Quit.")

        # 2. Test Volume and Folder Load
    with MPDController() as controller:
        
        # Set volume and check current status
        controller.set_volume(45)
        controller.set_volume(80)
        
        print("\n" + "="*40)
        
        # THIS IS THE MISSING CALL: Load your music folder and start playback
        controller.load_folder_and_play(MUSIC_PATH)
        controller.get_current_track_info() # Check info after first load

        print("\n" + "="*40)
   
    # Initialize connection outside the loop to read initial volume/status
    try:
        with MPDController() as controller:
            status = controller.client.status()
            # Use the actual volume level as a starting point
            current_volume = int(status.get('volume', 50))
            print(f"Initial Volume set to: {current_volume}%")
    except SystemExit:
        # Exit if initial connection failed
        sys.exit(1)
   

    # --- The Infinite Loop for Hardware Input ---
    while True:
        try:
            # Block until a key is pressed (simulates reading hardware input)
            char = readchar.readchar()
            
        except KeyboardInterrupt:
            char = 'q'
        except Exception as e:
            print(f"Input Error: {e}")
            time.sleep(1)
            continue

        if char not in COMMAND_MAP:
            continue

        command, arg = COMMAND_MAP[char]
        
        # --- Handle Exit Command ---
        if command == 'exit':
            print("Exiting controller...")
            break
            
        # --- Execute Command within a New Context ---
        with MPDController() as controller:
            
            # 1. Handle Relative Volume Adjustment
            if command == 'volume_change':
                change = arg
                
                # Use current_volume to calculate the new level
                new_volume = max(0, min(100, current_volume + change))
                
                controller.set_volume(new_volume)
                # Update the global state after the command succeeds
                current_volume = new_volume 
            
            # 2. Handle All Other Commands
            else:
                method = getattr(controller, command)
                if arg is None:
                    method()
                else:
                    method(arg)

        # Small delay to debounce inputs from fast devices (like a number keypad)
        time.sleep(0.05)

'''
if __name__ == "__main__":
    
    # 1. Define Content Paths
    # IMPORTANT: The MUSIC_PATH must be relative to the 'music_directory' 
    # set in your MPD configuration file (/etc/mpd.conf).
    # If MPD's music_directory is set to "/", then MUSIC_PATH = "Sample_Tunes" 
    # refers to the folder /Sample_Tunes. If your music is at the root, use "/" 
    # but be aware of MPD permissions and performance.
    
    MUSIC_PATH = "/"  # Assuming your MPD's music_directory is configured to see this path
    RADIO_PLAYLIST = "radio"
    
    # 2. Test Volume and Folder Load
    with MPDController() as controller:
        
        # Set volume and check current status
        controller.set_volume(45)
        controller.set_volume(80)
        
        print("\n" + "="*40)
        
        # THIS IS THE MISSING CALL: Load your music folder and start playback
        controller.load_folder_and_play(MUSIC_PATH)
        controller.get_current_track_info() # Check info after first load

        print("\n" + "="*40)
        
    # 3. Demonstrate Controls and Playlist Load
    
    # Needs a new context to issue commands sequentially (for this simple setup)
    with MPDController() as controller:
        controller.skip_track('next')
        controller.toggle_pause()
        
        print("\n" + "="*40)
        
        # Load and play your radio playlist
        controller.load_saved_playlist(RADIO_PLAYLIST)
        controller.get_current_track_info() # Check info after second load
'''
