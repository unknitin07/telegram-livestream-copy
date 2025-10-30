#!/usr/bin/env python3
"""
Audio buffer management for smooth streaming between source and target
"""

import asyncio
import logging
from collections import deque
import time

logger = logging.getLogger(__name__)

class AudioBuffer:
    def __init__(self, max_size=50):
        self.queue = asyncio.Queue(maxsize=max_size)
        self.max_size = max_size
        self.frames_received = 0
        self.frames_sent = 0
        self.frames_dropped = 0
        self.last_receive_time = None
        self.last_send_time = None
        
    async def put(self, frame):
        """Add audio frame to buffer"""
        try:
            self.queue.put_nowait(frame)
            self.frames_received += 1
            self.last_receive_time = time.time()
        except asyncio.QueueFull:
            # Buffer full, drop oldest frame
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(frame)
                self.frames_dropped += 1
                logger.warning(f"Buffer full! Dropped frame. Total dropped: {self.frames_dropped}")
            except:
                pass
    
    async def get(self):
        """Get audio frame from buffer"""
        try:
            frame = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            self.frames_sent += 1
            self.last_send_time = time.time()
            return frame
        except asyncio.TimeoutError:
            logger.warning("Buffer timeout - no frames available")
            return None
    
    def get_stats(self):
        """Get buffer statistics"""
        return {
            'size': self.queue.qsize(),
            'max_size': self.max_size,
            'received': self.frames_received,
            'sent': self.frames_sent,
            'dropped': self.frames_dropped,
            'last_receive': self.last_receive_time,
            'last_send': self.last_send_time
        }
    
    def clear(self):
        """Clear all frames from buffer"""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except:
                break
        logger.info("Buffer cleared")
    
    def is_healthy(self):
        """Check if buffer is receiving and sending data"""
        now = time.time()
        
        if self.last_receive_time is None or self.last_send_time is None:
            return False
        
        # If no data received in last 5 seconds, something is wrong
        receive_lag = now - self.last_receive_time
        send_lag = now - self.last_send_time
        
        if receive_lag > 5 or send_lag > 5:
            logger.warning(f"Buffer health issue - receive_lag: {receive_lag:.2f}s, send_lag: {send_lag:.2f}s")
            return False
        
        return True
