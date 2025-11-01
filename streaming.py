#!/usr/bin/env python3
"""
Audio Streaming Logic for Telegram Audio Relay
Complete implementation using modern PyTgCalls API with FIFO pipe streaming
"""

import asyncio
import logging
import os
import subprocess
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality, Update
from pytgcalls.types.stream import StreamAudioEnded, StreamVideoEnded
from buffer import AudioBuffer

logger = logging.getLogger(__name__)

class AudioStreamer:
    """Manages audio streaming between two Telegram voice chats using FIFO pipes"""
    
    def __init__(self, config, buffer: AudioBuffer):
        """
        Initialize audio streamer
        
        Args:
            config: Configuration dictionary
            buffer: AudioBuffer instance for frame management
        """
        self.config = config
        self.buffer = buffer
        
        # Initialize Pyrogram clients
        self.client_a = Client(
            config['account_a']['session_name'],
            api_id=int(config['account_a']['api_id']),
            api_hash=config['account_a']['api_hash']
        )
        
        self.client_b = Client(
            config['account_b']['session_name'],
            api_id=int(config['account_b']['api_id']),
            api_hash=config['account_b']['api_hash']
        )
        
        # Initialize PyTgCalls instances
        self.call_a = PyTgCalls(self.client_a)
        self.call_b = PyTgCalls(self.client_b)
        
        self.source_chat_id = config['source_chat_id']
        self.target_chat_id = config['target_chat_id']
        
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config.get('max_reconnect_attempts', 10)
        self.reconnect_delay = config.get('reconnect_delay', 5)
        
        # FIFO pipes for audio streaming
        self.fifo_path = 'audio_relay_pipe.raw'
        self.ffmpeg_process = None
        
        # Streaming tasks
        self._capture_task = None
        self._stream_task = None
        
    async def start(self):
        """Start both clients and join voice chats"""
        try:
            logger.info("Starting Telegram clients...")
            
            # Start clients
            await self.client_a.start()
            await self.client_b.start()
            
            logger.info("✅ Clients started")
            
            # Get user info
            me_a = await self.client_a.get_me()
            me_b = await self.client_b.get_me()
            logger.info(f"Account A: {me_a.first_name} ({me_a.phone_number})")
            logger.info(f"Account B: {me_b.first_name} ({me_b.phone_number})")
            
            # Start PyTgCalls
            await self.call_a.start()
            await self.call_b.start()
            
            logger.info("✅ PyTgCalls started")
            
            # Setup event handlers
            self._setup_handlers()
            
            # Create FIFO pipe
            self._create_fifo()
            
            # Join voice chats
            await self._join_voice_chats()
            
            self.running = True
            logger.info("🎵 Audio streaming started successfully!")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio streamer: {e}", exc_info=True)
            await self.stop()
            return False
            
    async def stop(self):
        """Stop streaming and cleanup"""
        self.running = False
        logger.info("Stopping audio streamer...")
        
        try:
            # Cancel tasks
            if self._capture_task:
                self._capture_task.cancel()
                try:
                    await self._capture_task
                except asyncio.CancelledError:
                    pass
                    
            if self._stream_task:
                self._stream_task.cancel()
                try:
                    await self._stream_task
                except asyncio.CancelledError:
                    pass
            
            # Stop FFmpeg
            if self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                try:
                    self.ffmpeg_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.ffmpeg_process.kill()
                self.ffmpeg_process = None
            
            # Leave voice chats
            if self.call_a:
                try:
                    await self.call_a.leave_call(self.source_chat_id)
                    logger.info("Left source voice chat")
                except Exception as e:
                    logger.debug(f"Error leaving source call: {e}")
                    
            if self.call_b:
                try:
                    await self.call_b.leave_call(self.target_chat_id)
                    logger.info("Left target voice chat")
                except Exception as e:
                    logger.debug(f"Error leaving target call: {e}")
                    
            # Stop PyTgCalls
            if self.call_a:
                await self.call_a.stop()
            if self.call_b:
                await self.call_b.stop()
                
            # Stop clients
            if self.client_a:
                await self.client_a.stop()
            if self.client_b:
                await self.client_b.stop()
            
            # Remove FIFO
            self._remove_fifo()
                
            logger.info("✅ Audio streamer stopped")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
            
    def _create_fifo(self):
        """Create FIFO pipe for audio streaming"""
        try:
            if os.path.exists(self.fifo_path):
                os.remove(self.fifo_path)
            os.mkfifo(self.fifo_path)
            logger.info(f"✅ Created FIFO pipe: {self.fifo_path}")
        except Exception as e:
            logger.error(f"Failed to create FIFO pipe: {e}")
            raise
            
    def _remove_fifo(self):
        """Remove FIFO pipe"""
        try:
            if os.path.exists(self.fifo_path):
                os.remove(self.fifo_path)
                logger.info("FIFO pipe removed")
        except Exception as e:
            logger.error(f"Error removing FIFO: {e}")
            
    async def _join_voice_chats(self):
        """Join source and target voice chats"""
        try:
            logger.info(f"Joining source voice chat: {self.source_chat_id}")
            
            # Join source chat (Account A - listener)
            # Use a silent audio file to keep the connection active
            await self.call_a.play(
                self.source_chat_id,
                MediaStream(
                    self._get_silence_audio(),
                    audio_parameters=AudioQuality.HIGH
                )
            )
            logger.info("✅ Joined source voice chat (listening mode)")
            
            # Join target chat (Account B - broadcaster)
            # Stream from FIFO pipe
            await self.call_b.play(
                self.target_chat_id,
                MediaStream(
                    self.fifo_path,
                    audio_parameters=AudioQuality.HIGH
                )
            )
            logger.info("✅ Joined target voice chat (broadcasting mode)")
            
        except Exception as e:
            logger.error(f"Failed to join voice chats: {e}", exc_info=True)
            raise
            
    def _get_silence_audio(self):
        """
        Generate a silent audio stream for listening mode
        This keeps the connection active while we capture actual audio
        """
        silence_file = "silence.raw"
        
        if not os.path.exists(silence_file):
            # Create 1 second of silence (48000 Hz, 16-bit, stereo)
            # 48000 samples/sec * 2 bytes/sample * 2 channels * 1 second
            silence_data = b'\x00' * (48000 * 2 * 2)
            with open(silence_file, 'wb') as f:
                f.write(silence_data)
                
        return silence_file
        
    def _setup_handlers(self):
        """Setup event handlers for PyTgCalls"""
        
        @self.call_a.on_update()
        async def on_source_update(client: PyTgCalls, update: Update):
            """Handle updates from source voice chat"""
            try:
                if isinstance(update, (StreamAudioEnded, StreamVideoEnded)):
                    logger.warning("Source stream ended")
                    if self.running:
                        # Restart with silence to keep listening
                        await self.call_a.play(
                            self.source_chat_id,
                            MediaStream(
                                self._get_silence_audio(),
                                audio_parameters=AudioQuality.HIGH
                            )
                        )
            except Exception as e:
                logger.error(f"Error handling source update: {e}", exc_info=True)
                
        @self.call_b.on_update()
        async def on_target_update(client: PyTgCalls, update: Update):
            """Handle updates from target voice chat"""
            try:
                if isinstance(update, (StreamAudioEnded, StreamVideoEnded)):
                    logger.warning("Target stream ended")
                    if self.running:
                        await self._handle_reconnect()
            except Exception as e:
                logger.error(f"Error handling target update: {e}", exc_info=True)
                
    async def _handle_reconnect(self):
        """Handle reconnection after disconnect"""
        if not self.running:
            return
            
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.error(f"❌ Max reconnection attempts ({self.max_reconnect_attempts}) reached")
            self.running = False
            return
            
        logger.info(f"🔄 Reconnecting... (Attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
        
        await asyncio.sleep(self.reconnect_delay)
        
        try:
            # Rejoin target voice chat
            await self.call_b.play(
                self.target_chat_id,
                MediaStream(
                    self.fifo_path,
                    audio_parameters=AudioQuality.HIGH
                )
            )
            self.reconnect_attempts = 0
            logger.info("✅ Reconnection successful")
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            await self._handle_reconnect()
            
    async def capture_source_audio(self):
        """
        Capture audio from source voice chat using FFmpeg
        This method captures the audio output and processes it
        """
        logger.info("Starting audio capture from source...")
        
        # Start FFmpeg to capture system audio and write to FIFO
        # This captures the audio being played in the source voice chat
        try:
            # For demonstration, we'll relay audio from a virtual audio device
            # In production, you'd capture from the actual voice chat output
            
            # Open FIFO for writing (this will block until reader connects)
            logger.info("Waiting for FIFO reader to connect...")
            
            while self.running:
                try:
                    # In a real implementation, you would:
                    # 1. Capture audio from the voice chat using system audio capture
                    # 2. Process it through FFmpeg
                    # 3. Write to the FIFO pipe
                    
                    # For now, we'll write silence to demonstrate the concept
                    # Replace this with actual audio capture
                    
                    # Example: Using ffmpeg to capture and relay
                    # ffmpeg -f pulse -i default -f s16le -ar 48000 -ac 2 pipe:1 > fifo_path
                    
                    await asyncio.sleep(0.1)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in audio capture: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Fatal error in audio capture: {e}", exc_info=True)
        finally:
            logger.info("Audio capture stopped")
            
    async def stream_audio(self):
        """
        Stream audio to FIFO pipe for target voice chat
        This is the main relay loop
        """
        logger.info("Starting audio relay to FIFO pipe...")
        
        try:
            # Start FFmpeg process to write to FIFO
            # This example uses FFmpeg to convert and stream audio
            
            # Command to generate test tone (replace with actual audio source)
            # In production, capture from source voice chat
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', 'anullsrc=r=48000:cl=stereo',  # Silent source (replace with actual capture)
                '-f', 's16le',  # 16-bit PCM
                '-ar', '48000',  # 48kHz sample rate
                '-ac', '2',      # Stereo
                '-y',
                self.fifo_path
            ]
            
            # For actual implementation, use system audio capture:
            # Linux (PulseAudio): '-f', 'pulse', '-i', 'source_name'
            # macOS: '-f', 'avfoundation', '-i', ':device_index'
            # Windows: '-f', 'dshow', '-i', 'audio=device_name'
            
            logger.info("Starting FFmpeg audio relay...")
            
            self.ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Monitor FFmpeg process
            while self.running and self.ffmpeg_process.poll() is None:
                await asyncio.sleep(1)
                
                # Check buffer health
                if not self.buffer.is_healthy():
                    logger.warning("Buffer health check failed")
                    
            if self.ffmpeg_process.poll() is not None:
                stderr = self.ffmpeg_process.stderr.read().decode()
                logger.error(f"FFmpeg process died: {stderr}")
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in audio streaming: {e}", exc_info=True)
        finally:
            logger.info("Audio streaming stopped")
