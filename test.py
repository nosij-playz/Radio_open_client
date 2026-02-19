import yt_dlp
import vlc
import time
import sys

class YouTubeAudioStreamerVLC:
    def __init__(self):
        self.instance = vlc.Instance('--no-video')
        self.player = self.instance.media_player_new()
        self.is_playing = False
        
    def get_audio_stream_url(self, url):
        """Extract audio stream URL from YouTube video"""
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_audio': True,
            'noplaylist': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info
                info = ydl.extract_info(url, download=False)
                
                # Get the best audio format
                formats = info.get('formats', [])
                audio_url = info.get('url', None)
                
                # Try to find the best audio format
                for f in formats:
                    if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                        audio_url = f.get('url')
                        break
                
                print(f"🎵 Now streaming: {info.get('title', 'Unknown')}")
                print(f"⏱️  Duration: {info.get('duration', 'Unknown')} seconds")
                print(f"👤 Channel: {info.get('uploader', 'Unknown')}")
                print("-" * 50)
                
                return audio_url
                
        except Exception as e:
            print(f"❌ Error extracting audio: {e}")
            return None
    
    def play_stream(self, url):
        """Play the audio stream using VLC"""
        audio_url = self.get_audio_stream_url(url)
        
        if not audio_url:
            print("❌ Could not get audio stream")
            return
        
        # Create VLC media
        media = self.instance.media_new(audio_url)
        media.add_option('no-video')  # Ensure no video
        self.player.set_media(media)
        
        # Start playback
        self.player.play()
        self.is_playing = True
        
        print("▶️  Playing... (Press Ctrl+C to stop)")
        print("🎮 Controls: [P]ause, [R]esume, [S]top, [Q]uit")
        
        try:
            while self.is_playing:
                time.sleep(0.1)
                
                # Simple control interface
                if msvcrt.kbhit() if sys.platform == "win32" else True:
                    if sys.platform != "win32":
                        import select
                        if select.select([sys.stdin], [], [], 0)[0]:
                            cmd = sys.stdin.read(1).lower()
                        else:
                            cmd = None
                    else:
                        import msvcrt
                        cmd = msvcrt.getch().decode().lower()
                    
                    if cmd:
                        if cmd == 'p':
                            self.player.pause()
                            print("⏸️  Paused")
                        elif cmd == 'r':
                            self.player.play()
                            print("▶️  Resumed")
                        elif cmd == 's':
                            self.stop()
                        elif cmd == 'q':
                            break
                
                # Check if playback ended
                if self.player.get_state() == vlc.State.Ended:
                    print("\n✅ Playback finished")
                    break
                    
        except KeyboardInterrupt:
            print("\n⏹️  Stopping...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop playback and cleanup"""
        self.is_playing = False
        self.player.stop()
        print("👋 Goodbye!")

def main():
    print("🎧 YouTube Audio Streamer (VLC Version)")
    print("=" * 50)
    print("⚠️  Note: Requires VLC media player installed")
    print("=" * 50)
    
    url = input("📹 Enter YouTube URL: ").strip()
    
    if not url:
        print("❌ No URL provided")
        return
    
    streamer = YouTubeAudioStreamerVLC()
    streamer.play_stream(url)

if __name__ == "__main__":
    main()