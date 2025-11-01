#!/usr/bin/env python3
"""
Login script for Telegram Audio Relay Bot
Generates session files for both accounts
"""

import json
import asyncio
import sys
from pyrogram import Client

def load_config():
    """Load configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Error: config.json not found!")
        print("Please create config.json with your account details.")
        sys.exit(1)
    except json.JSONDecodeError:
        print("❌ Error: Invalid JSON in config.json")
        sys.exit(1)

async def login_account(name, account_info):
    """Login to a single account and create session file"""
    print(f"\n{'='*50}")
    print(f"Logging in to Account {name.upper()}")
    print(f"{'='*50}")
    
    api_id = account_info['api_id']
    api_hash = account_info['api_hash']
    session_name = account_info['session_name']
    
    if api_id == "YOUR_API_ID" or api_hash == "YOUR_API_HASH":
        print(f"❌ Error: Please update config.json with real API credentials")
        return False
    
    try:
        app = Client(
            session_name,
            api_id=int(api_id),
            api_hash=api_hash,
            phone_number=account_info['phone']
        )
        
        await app.start()
        me = await app.get_me()
        
        print(f"✅ Successfully logged in as: {me.first_name}")
        print(f"   Phone: {me.phone_number}")
        print(f"   Session saved: {session_name}.session")
        
        await app.stop()
        return True
        
    except Exception as e:
        print(f"❌ Error logging in to {name}: {str(e)}")
        return False

async def main():
    """Main function to login both accounts"""
    print("\n🔐 Telegram Audio Relay - Account Login")
    print("=" * 50)
    
    config = load_config()
    
    # Login to Account A
    success_a = await login_account('a', config['account_a'])
    
    # Login to Account B
    success_b = await login_account('b', config['account_b'])
    
    print(f"\n{'='*50}")
    if success_a and success_b:
        print("✅ Both accounts logged in successfully!")
        print("\nYou can now run: python main.py")
    else:
        print("❌ Some accounts failed to login. Please check the errors above.")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    asyncio.run(main())
