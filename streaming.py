#!/usr/bin/env python3
"""
Audio Streaming Logic for Telegram Audio Relay
Manages voice chat connections and audio streaming
"""

import asyncio
import logging
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, Update
from pytgcalls.types.input_stream import AudioParameters, AudioQuality
from pytgcalls.types.stream import Stream, StreamAudioEnded
from buffer import AudioBuffer

logger = logging.getLogger(__name__)

class AudioStreamer:
    """Manages audio streaming between two Telegram voice chats"""
    
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
        
        # Audio streaming pipe
        self.audio_pipe = None
        
    async def start(self):
        """Start both clients and join voice chats"""
        try:
            logger.info("Starting Telegram clients...")
            
            # Start clients
            await self.client_a.start()
            await self.client_b.start()
            
            logger.info("✅ Clients started")
            
            # Start PyTgCalls
            await self.call_a.start()
            await self.call_b.start()
            
            logger.info("✅ PyTgCalls started")
            
            # Setup handlers
            self._setup_handlers()
            
            # Join voice chats
            await self._join_voice_chats()
            
            self.running = True
            logger.info("🎵 Audio streaming started successfully!")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio streamer: {e}")
            await self.stop()
            return False
            
    async def stop(self):
        """Stop streaming and cleanup"""
        self.running = False
        logger.info("Stopping audio streamer...")
        
        try:
            # Leave voice chats
            if self.call_a:
                try:
                    await self.call_a.leave_call(self.source_chat_id)
                except Exception as e:
                    logger.debug(f"Error leaving source call: {e}")
                    
            if self.call_b:
                try:
                    await self.call_b.leave_call(self.target_chat_id)
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
                
            logger.info("✅ Audio streamer stopped")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            
    async def _join_voice_chats(self):
        """Join source and target voice chats"""
        logger.info(f"Joining source voice chat: {self.source_chat_id}")
        
        # Create audio pipe for streaming
        self.audio_pipe = AudioPiped('audio_pipe.raw')
        
        try:
            # Join source chat (Account A - listener)
            await self.call_a.join_call(
                self.source_chat_id,
                Stream(
                    AudioParameters(
                        bitrate=48000,
                    )
                )
            )
            logger.info("✅ Joined source voice chat")
            
            # Join target chat (Account B - broadcaster)
            await self.call_b.join_call(
                self.target_chat_id,
                self.audio_pipe
            )
            logger.info("✅ Joined target voice chat")
            
        except Exception as e:
            logger.error(f"Failed to join voice chats: {e}")
            raise
            
    def _setup_handlers(self):
        """Setup event handlers for PyTgCalls"""
        
        @self.call_a.on_update()
        async def on_source_update(client, update: Update):
            """Handle updates from source voice chat"""
            try:
                if isinstance(update, StreamAudioEnded):
                    logger.warning("Source audio stream ended")
                    await self._handle_reconnect()
            except Exception as e:
                logger.error(f"Error handling source update: {e}")
                
        @self.call_b.on_update()
        async def on_target_update(client, update: Update):
            """Handle updates from target voice chat"""
            try:
                if isinstance(update, StreamAudioEnded):
                    logger.warning("Target audio stream ended")
                    await self._handle_reconnect()
            except Exception as e:
                logger.error(f"Error handling target update: {e}")
                
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
            await self._join_voice_chats()
            self.reconnect_attempts = 0
            logger.info("✅ Reconnection successful")
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            await self._handle_reconnect()
            
    async def stream_audio(self):
        """
        Main audio streaming loop
        Captures audio from source and streams to target
        """
        logger.info("Starting audio streaming loop...")
        
        while self.running:
            try:
                # Check buffer health
                if not self.buffer.is_healthy():
                    logger.error("Buffer health check failed")
                    await self._handle_reconnect()
                    continue
                
                # Get audio frame from buffer (with timeout)
                frame = await self.buffer.get(timeout=1.0)
                
                if frame is not None:
                    # Stream frame to target
                    await self._send_frame_to_target(frame)
                else:
                    # No frame available, continue
                    await asyncio.sleep(0.01)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in streaming loop: {e}")
                await asyncio.sleep(1)
                
        logger.info("Audio streaming loop stopped")
        
    async def _send_frame_to_target(self, frame):
        """
        Send audio frame to target voice chat
        
        Args:
            frame: Audio frame data to send
        """
        try:
            # Write frame to audio pipe
            if self.audio_pipe:
                # This is a placeholder - actual implementation depends on
                # pytgcalls version and API for raw audio streaming
                pass
        except Exception as e:
            logger.error(f"Error sending frame to target: {e}")
            
    async def capture_source_audio(self):
        """
        Capture audio from source voice chat
        This is a placeholder for actual audio capture implementation
        """
        logger.info("Starting audio capture from source...")
        
        while self.running:
            try:
                # Placeholder for audio capture
                # Actual implementation depends on pytgcalls API
                # for accessing raw audio stream
                
                # Example structure (to be implemented):
                # frame = await self.call_a.get_audio_frame()
                # if frame:
                #     await self.buffer.put(frame)
                
                await asyncio.sleep(0.02)  # ~50fps for audio
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error capturing source audio: {e}")
                await asyncio.sleep(1)
                
        logger.info("Audio capture stopped")
