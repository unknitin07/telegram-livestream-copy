#!/usr/bin/env python3
"""
Telegram Audio Relay Bot - Main Entry Point
Streams audio from one Telegram voice chat to another in real-time
"""

import asyncio
import json
import logging
import sys
import signal
from pathlib import Path
import coloredlogs

from buffer import AudioBuffer
from streaming import AudioStreamer

# Configure logging
def setup_logging():
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # File handler
    file_handler = logging.FileHandler('audio_relay.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Console handler with colors
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    # Use coloredlogs for prettier console output
    coloredlogs.install(
        level='INFO',
        fmt=log_format,
        logger=logger
    )
    
    return logger

logger = setup_logging()

class AudioRelayBot:
    """Main bot class managing the audio relay"""
    
    def __init__(self, config_file='config.json'):
        """
        Initialize the audio relay bot
        
        Args:
            config_file: Path to configuration file
        """
        self.config = self._load_config(config_file)
        self.buffer = AudioBuffer(max_size=self.config.get('buffer_size', 50))
        self.streamer = AudioStreamer(self.config, self.buffer)
        self.running = False
        
    def _load_config(self, config_file):
        """Load configuration from JSON file"""
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                logger.error(f"❌ Configuration file not found: {config_file}")
                logger.info("Please create config.json with your settings")
                sys.exit(1)
                
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            # Validate configuration
            self._validate_config(config)
            
            logger.info("✅ Configuration loaded successfully")
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in config file: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"❌ Error loading configuration: {e}")
            sys.exit(1)
            
    def _validate_config(self, config):
        """Validate configuration structure"""
        required_keys = ['account_a', 'account_b', 'source_chat_id', 'target_chat_id']
        
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")
                
        # Check for placeholder values
        if config['account_a']['api_id'] == "YOUR_API_ID":
            raise ValueError("Please update config.json with your actual API credentials")
            
        # Validate account structure
        account_keys = ['api_id', 'api_hash', 'phone', 'session_name']
        for account in ['account_a', 'account_b']:
            for key in account_keys:
                if key not in config[account]:
                    raise ValueError(f"Missing {key} in {account} configuration")
                    
    def _check_session_files(self):
        """Check if session files exist"""
        session_a = Path(f"{self.config['account_a']['session_name']}.session")
        session_b = Path(f"{self.config['account_b']['session_name']}.session")
        
        if not session_a.exists() or not session_b.exists():
            logger.error("❌ Session files not found!")
            logger.info("Please run 'python login.py' first to create session files")
            return False
            
        return True
        
    async def start(self):
        """Start the audio relay bot"""
        try:
            logger.info("="*60)
            logger.info("🎵 Telegram Audio Relay Bot Starting...")
            logger.info("="*60)
            
            # Check session files
            if not self._check_session_files():
                return False
                
            # Start buffer
            await self.buffer.start()
            logger.info("✅ Audio buffer initialized")
            
            # Start streamer
            if not await self.streamer.start():
                logger.error("❌ Failed to start audio streamer")
                return False
                
            self.running = True
            
            # Log configuration
            logger.info(f"📡 Source Chat ID: {self.config['source_chat_id']}")
            logger.info(f"📢 Target Chat ID: {self.config['target_chat_id']}")
            logger.info(f"📦 Buffer Size: {self.config.get('buffer_size', 50)}")
            logger.info("="*60)
            logger.info("✅ Bot is running! Press Ctrl+C to stop")
            logger.info("="*60)
            
            # Start streaming tasks
            tasks = [
                asyncio.create_task(self.streamer.capture_source_audio()),
                asyncio.create_task(self.streamer.stream_audio()),
                asyncio.create_task(self._monitor_health())
            ]
            
            # Wait for tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}", exc_info=True)
            return False
            
    async def stop(self):
        """Stop the audio relay bot"""
        if not self.running:
            return
            
        logger.info("\n" + "="*60)
        logger.info("⏹️  Stopping Telegram Audio Relay Bot...")
        logger.info("="*60)
        
        self.running = False
        
        # Stop streamer
        await self.streamer.stop()
        
        # Stop buffer
        await self.buffer.stop()
        
        # Log final statistics
        stats = self.buffer.get_stats()
        logger.info("\n📊 Final Statistics:")
        logger.info(f"   Total Frames Received: {stats['received']}")
        logger.info(f"   Total Frames Sent: {stats['sent']}")
        logger.info(f"   Total Frames Dropped: {stats['dropped']}")
        
        logger.info("="*60)
        logger.info("✅ Bot stopped successfully")
        logger.info("="*60 + "\n")
        
    async def _monitor_health(self):
        """Monitor overall system health"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if not self.streamer.running:
                    logger.warning("⚠️ Streamer is not running!")
                    
                if not self.buffer.is_healthy():
                    logger.warning("⚠️ Buffer health check failed!")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")

# Global bot instance for signal handling
bot_instance = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    if bot_instance:
        logger.info("\n🛑 Received shutdown signal...")
        asyncio.create_task(bot_instance.stop())

async def main():
    """Main entry point"""
    global bot_instance
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start bot
    bot_instance = AudioRelayBot()
    
    try:
        await bot_instance.start()
    except KeyboardInterrupt:
        logger.info("\n🛑 Keyboard interrupt received...")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
    finally:
        await bot_instance.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
