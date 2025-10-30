#!/usr/bin/env python3
"""
Login script to authenticate both Telegram accounts and save sessions
Run this once before starting the main bot
"""

import json
import asyncio
from pyrogram import Client

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

async def login_account(account_name, account_config):
    print(f"\n{'='*50}")
    print(f"Logging in {account_name.upper()}")
    print(f"{'='*50}")
    
    client = Client(
        name=account_config['session_name'],
        api_id=account_config['api_id'],
        api_hash=account_config['api_hash'],
        phone_number=account_config['phone']
    )
    
    async with client:
        me = await client.get_me()
        print(f"✅ Successfully logged in as: {me.first_name} (@{me.username})")
        print(f"   Phone: {me.phone_number}")
        print(f"   Session saved: {account_config['session_name']}.session")
    
    return True

async def main():
    print("🔐 Telegram Audio Relay - Account Login")
    print("This will create session files for both accounts\n")
    
    config = load_config()
    
    # Login Account A (Source - Listener)
    try:
        await login_account("account_a", config['account_a'])
    except Exception as e:
        print(f"❌ Failed to login Account A: {e}")
        return
    
    # Login Account B (Target - Broadcaster)
    try:
        await login_account("account_b", config['account_b'])
    except Exception as e:
        print(f"❌ Failed to login Account B: {e}")
        return
    
    print(f"\n{'='*50}")
    print("✅ Both accounts logged in successfully!")
    print("You can now run: python main.py")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    asyncio.run(main())
