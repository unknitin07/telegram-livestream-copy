#!/usr/bin/env python3
"""
Main entry point for Telegram Audio Relay Bot
Streams audio from source voice chat to target voice chat
"""

import asyncio
import json
import logging
import signal
import sys
from pyrogram import Client
from streaming import AudioStreamer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audio_relay.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class AudioRelayBot:
    def __init__(self, config_path='config.json'):
        self.config = self.load_config(config_path)
        self.source_client = None
        self.target_client = None
        self.streamer = None
        self.running = False
        
    def load_config(self, path):
        """Load configuration from JSON file"""
        try:
            with open(path, 'r') as f:
                config = json.load(f)
            logger.info("✅ Configuration loaded successfully")
            return config
        except FileNotFoundError:
            logger.error(f"❌ Config file not found: {path}")
            sys.exit(1)
        except json.JSONDecodeError:
            logger.error(f"❌ Invalid JSON in config file: {path}")
            sys.exit(1)
    
    async def init_clients(self):
        """Initialize Telegram clients"""
        logger.info("Initializing Telegram clients...")
        
        # Account A - Source (Listener)
        self.source_client = Client(
            name=self.config['account_a']['session_name'],
            api_id=self.config['account_a']['api_id'],
            api_hash=self.config['account_a']['api_hash']
        )
        
        # Account B - Target (Broadcaster)
        self.target_client = Client(
            name=self.config['account_b']['session_name'],
            api_id=self.config['account_b']['api_id'],
            api_hash=self.config['account_b']['api_hash']
        )
        
        await self.source_client.start()
        await self.target_client.start()
        
        # Get account info
        source_me = await self.source_client.get_me()
        target_me = await self.target_client.get_me()
        
        logger.info(f"✅ Source Account: {source_me.first_name} (@{source_me.username})")
        logger.info(f"✅ Target Account: {target_me.first_name} (@{target_me.username})")
    
    async def start_streaming(self):
        """Start audio streaming"""
        logger.info("="*60)
        logger.info("🎵 TELEGRAM AUDIO RELAY BOT")
        logger.info("="*60)
        logger.info(f"Source Chat ID: {self.config['source_chat_id']}")
        logger.info(f"Target Chat ID: {self.config['target_chat_id']}")
        logger.info(f"Buffer Size: {self.config['buffer_size']}")
        logger.info("="*60)
        
        # Initialize streamer
        self.streamer = AudioStreamer(
            source_client=self.source_client,
            target_client=self.target_client,
            source_chat_id=self.config['source_chat_id'],
            target_chat_id=self.config['target_chat_id'],
            buffer_size=self.config['buffer_size']
        )
        
        self.running = True
        
        try:
            # Start streaming
            await self.streamer.run()
        except KeyboardInterrupt:
            logger.info("\n⚠️ Received interrupt signal")
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}", exc_info=True)
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up...")
        
        if self.streamer:
            await self.streamer.stop()
        
        if self.source_client:
            await self.source_client.stop()
        
        if self.target_client:
            await self.target_client.stop()
        
        logger.info("✅ Cleanup completed")
    
    async def run(self):
        """Main run method"""
        try:
            await self.init_clients()
            await self.start_streaming()
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
            await self.cleanup()
            sys.exit(1)

async def main():
    """Entry point"""
    bot = AudioRelayBot()
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info("\n⚠️ Shutting down gracefully...")
        asyncio.create_task(bot.cleanup())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user")
