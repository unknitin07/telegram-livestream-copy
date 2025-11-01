#!/usr/bin/env python3
"""
Audio Capture Helper for Telegram Audio Relay
System-specific audio capture implementations
"""

import asyncio
import logging
import platform
import subprocess
import os

logger = logging.getLogger(__name__)

class AudioCaptureManager:
    """
    Manages system audio capture for relaying voice chat audio
    Supports Linux (PulseAudio), macOS (AVFoundation), and Windows (DirectShow)
    """
    
    def __init__(self, output_fifo):
        """
        Initialize audio capture manager
        
        Args:
            output_fifo: Path to FIFO pipe for output
        """
        self.output_fifo = output_fifo
        self.process = None
        self.system = platform.system()
        
    async def start_capture(self, device_name=None):
        """
        Start capturing system audio
        
        Args:
            device_name: Optional specific audio device to capture from
        """
        try:
            cmd = self._get_ffmpeg_command(device_name)
            
            logger.info(f"Starting audio capture with command: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info("✅ Audio capture started")
            
            # Monitor process
            while self.process.poll() is None:
                await asyncio.sleep(1)
                
            # Process ended
            stderr = self.process.stderr.read().decode()
            logger.error(f"Audio capture process ended: {stderr}")
            
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}", exc_info=True)
            
    def stop_capture(self):
        """Stop audio capture"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            logger.info("Audio capture stopped")
            
    def _get_ffmpeg_command(self, device_name=None):
        """
        Get FFmpeg command for the current system
        
        Args:
            device_name: Optional device name
            
        Returns:
            List of command arguments
        """
        if self.system == "Linux":
            return self._get_linux_command(device_name)
        elif self.system == "Darwin":  # macOS
            return self._get_macos_command(device_name)
        elif self.system == "Windows":
            return self._get_windows_command(device_name)
        else:
            raise OSError(f"Unsupported operating system: {self.system}")
            
    def _get_linux_command(self, device_name=None):
        """
        Get FFmpeg command for Linux (PulseAudio)
        
        To list audio sources: pactl list sources short
        """
        if device_name is None:
            # Try to detect default monitor source
            device_name = self._detect_linux_monitor_source()
            
        return [
            'ffmpeg',
            '-f', 'pulse',
            '-i', device_name or 'default',
            '-f', 's16le',      # 16-bit PCM
            '-ar', '48000',     # 48kHz (Telegram voice chat standard)
            '-ac', '2',         # Stereo
            '-y',
            self.output_fifo
        ]
        
    def _get_macos_command(self, device_name=None):
        """
        Get FFmpeg command for macOS (AVFoundation)
        
        To list audio devices: ffmpeg -f avfoundation -list_devices true -i ""
        """
        # Default to system audio (usually :0 or :1)
        device = device_name or ':0'
        
        return [
            'ffmpeg',
            '-f', 'avfoundation',
            '-i', device,
            '-f', 's16le',
            '-ar', '48000',
            '-ac', '2',
            '-y',
            self.output_fifo
        ]
        
    def _get_windows_command(self, device_name=None):
        """
        Get FFmpeg command for Windows (DirectShow)
        
        To list audio devices: ffmpeg -list_devices true -f dshow -i dummy
        """
        # You need to find the exact device name on Windows
        device = device_name or 'audio=Stereo Mix'
        
        return [
            'ffmpeg',
            '-f', 'dshow',
            '-i', device,
            '-f', 's16le',
            '-ar', '48000',
            '-ac', '2',
            '-y',
            self.output_fifo
        ]
        
    def _detect_linux_monitor_source(self):
        """
        Detect PulseAudio monitor source (for capturing system audio)
        
        Returns:
            Source name or None
        """
        try:
            result = subprocess.run(
                ['pactl', 'list', 'sources', 'short'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Look for monitor sources
            for line in result.stdout.split('\n'):
                if 'monitor' in line.lower():
                    # Extract source name (first field)
                    source_name = line.split()[1] if len(line.split()) > 1 else None
                    if source_name:
                        logger.info(f"Detected monitor source: {source_name}")
                        return source_name
                        
        except Exception as e:
            logger.warning(f"Could not detect monitor source: {e}")
            
        return 'default'
        
    @staticmethod
    def list_audio_devices():
        """
        List available audio devices for the current system
        """
        system = platform.system()
        
        try:
            if system == "Linux":
                logger.info("Listing PulseAudio sources:")
                subprocess.run(['pactl', 'list', 'sources', 'short'])
                
            elif system == "Darwin":
                logger.info("Listing macOS audio devices:")
                subprocess.run([
                    'ffmpeg', '-f', 'avfoundation',
                    '-list_devices', 'true', '-i', ''
                ], stderr=subprocess.STDOUT)
                
            elif system == "Windows":
                logger.info("Listing Windows audio devices:")
                subprocess.run([
                    'ffmpeg', '-list_devices', 'true',
                    '-f', 'dshow', '-i', 'dummy'
                ], stderr=subprocess.STDOUT)
                
        except Exception as e:
            logger.error(f"Failed to list audio devices: {e}")


# Example usage and testing
async def test_audio_capture():
    """Test audio capture functionality"""
    
    # Create test FIFO
    test_fifo = 'test_audio.raw'
    
    try:
        if os.path.exists(test_fifo):
            os.remove(test_fifo)
        os.mkfifo(test_fifo)
        
        # List available devices
        print("\n=== Available Audio Devices ===")
        AudioCaptureManager.list_audio_devices()
        
        # Start capture
        print(f"\n=== Starting Audio Capture to {test_fifo} ===")
        manager = AudioCaptureManager(test_fifo)
        
        # Start capture task
        capture_task = asyncio.create_task(manager.start_capture())
        
        # Let it run for 10 seconds
        print("Capturing for 10 seconds...")
        await asyncio.sleep(10)
        
        # Stop capture
        manager.stop_capture()
        capture_task.cancel()
        
        try:
            await capture_task
        except asyncio.CancelledError:
            pass
            
        print("✅ Test completed")
        
    finally:
        # Cleanup
        if os.path.exists(test_fifo):
            os.remove(test_fifo)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_audio_capture())
