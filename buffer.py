#!/usr/bin/env python3
"""
Audio Buffer Management for Telegram Audio Relay
Handles audio frame queuing with health monitoring
"""

import asyncio
import time
import logging
from collections import deque

logger = logging.getLogger(__name__)

class AudioBuffer:
    """Async audio buffer with health monitoring"""
    
    def __init__(self, max_size=50):
        """
        Initialize audio buffer
        
        Args:
            max_size: Maximum number of frames to buffer
        """
        self.max_size = max_size
        self.queue = asyncio.Queue(maxsize=max_size)
        self.stats = {
            'received': 0,
            'sent': 0,
            'dropped': 0,
            'last_activity': time.time()
        }
        self.running = False
        self._monitor_task = None
        
    async def start(self):
        """Start the buffer monitoring"""
        self.running = True
        self._monitor_task = asyncio.create_task(self._monitor_health())
        logger.info(f"Buffer started with max size: {self.max_size}")
        
    async def stop(self):
        """Stop the buffer and cleanup"""
        self.running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Clear remaining frames
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
                
        logger.info("Buffer stopped")
        
    async def put(self, frame):
        """
        Add audio frame to buffer
        
        Args:
            frame: Audio frame data to buffer
        """
        try:
            self.queue.put_nowait(frame)
            self.stats['received'] += 1
            self.stats['last_activity'] = time.time()
        except asyncio.QueueFull:
            # Drop oldest frame if buffer is full
            try:
                self.queue.get_nowait()
                self.stats['dropped'] += 1
            except asyncio.QueueEmpty:
                pass
            
            # Try adding the new frame again
            try:
                self.queue.put_nowait(frame)
                self.stats['received'] += 1
            except asyncio.QueueFull:
                self.stats['dropped'] += 1
                logger.warning("Buffer overflow - frame dropped")
                
    async def get(self, timeout=1.0):
        """
        Get audio frame from buffer
        
        Args:
            timeout: Maximum time to wait for frame
            
        Returns:
            Audio frame or None if timeout
        """
        try:
            frame = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            self.stats['sent'] += 1
            self.stats['last_activity'] = time.time()
            return frame
        except asyncio.TimeoutError:
            return None
            
    def get_stats(self):
        """Get current buffer statistics"""
        return {
            'size': self.queue.qsize(),
            'max_size': self.max_size,
            'received': self.stats['received'],
            'sent': self.stats['sent'],
            'dropped': self.stats['dropped'],
            'idle_time': time.time() - self.stats['last_activity']
        }
        
    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            'received': 0,
            'sent': 0,
            'dropped': 0,
            'last_activity': time.time()
        }
        logger.info("Buffer statistics reset")
        
    async def _monitor_health(self):
        """Monitor buffer health and log statistics"""
        while self.running:
            try:
                await asyncio.sleep(10)  # Log every 10 seconds
                stats = self.get_stats()
                logger.info(
                    f"📊 Buffer Stats - "
                    f"Size: {stats['size']}/{stats['max_size']} | "
                    f"Received: {stats['received']} | "
                    f"Sent: {stats['sent']} | "
                    f"Dropped: {stats['dropped']} | "
                    f"Idle: {stats['idle_time']:.1f}s"
                )
                
                # Health check warnings
                if stats['idle_time'] > 30:
                    logger.warning(f"⚠️ Buffer idle for {stats['idle_time']:.0f}s")
                    
                if stats['dropped'] > stats['received'] * 0.1:  # More than 10% dropped
                    logger.warning(f"⚠️ High drop rate: {stats['dropped']}/{stats['received']}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in buffer health monitor: {e}")
                
    def is_healthy(self):
        """
        Check if buffer is healthy
        
        Returns:
            bool: True if buffer is operating normally
        """
        stats = self.get_stats()
        
        # Buffer is unhealthy if:
        # 1. Idle for more than 60 seconds
        # 2. Drop rate above 20%
        if stats['idle_time'] > 60:
            logger.error("Buffer health check failed: idle timeout")
            return False
            
        if stats['received'] > 0:
            drop_rate = stats['dropped'] / stats['received']
            if drop_rate > 0.2:
                logger.error(f"Buffer health check failed: high drop rate ({drop_rate:.1%})")
                return False
                
        return True
