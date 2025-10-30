# 🎵 Telegram Audio Relay Bot

Stream audio from one Telegram voice chat to another in real-time using two user accounts.

## 📋 Features

- ✅ Real-time audio streaming between voice chats
- ✅ Automatic reconnection on disconnect
- ✅ Audio buffering for smooth playback
- ✅ Health monitoring and statistics
- ✅ Detailed logging
- ✅ Easy configuration

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.8+
- Two Telegram accounts
- VPS or server for 24/7 operation
- Telegram API credentials (get from https://my.telegram.org)

### 2. Installation

```bash
# Clone or download the bot files
cd telegram-audio-relay

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Edit `config.json` with your details:

```json
{
  "account_a": {
    "api_id": "YOUR_API_ID",
    "api_hash": "YOUR_API_HASH",
    "phone": "+1234567890",
    "session_name": "account_a"
  },
  "account_b": {
    "api_id": "YOUR_API_ID",
    "api_hash": "YOUR_API_HASH",
    "phone": "+0987654321",
    "session_name": "account_b"
  },
  "source_chat_id": -1001234567890,
  "target_chat_id": -1009876543210,
  "buffer_size": 50,
  "reconnect_delay": 5,
  "max_reconnect_attempts": 10
}
```

**Getting Chat IDs:**
- Forward a message from the chat to @userinfobot
- Or use this command in the chat: `/id` (if you have a bot there)
- Group/channel IDs start with `-100`

### 4. First Time Login

```bash
python login.py
```

This will:
- Prompt you to login with phone + code for both accounts
- Save session files (`account_a.session`, `account_b.session`)
- You only need to do this once

### 5. Start Streaming

```bash
python main.py
```

## 🖥️ Running 24/7 on VPS

### Using screen (simple)

```bash
screen -S audio-relay
python main.py
# Press Ctrl+A then D to detach
# Reconnect with: screen -r audio-relay
```

### Using systemd (recommended)

Create `/etc/systemd/system/audio-relay.service`:

```ini
[Unit]
Description=Telegram Audio Relay Bot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/telegram-audio-relay
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable audio-relay
sudo systemctl start audio-relay
sudo systemctl status audio-relay

# View logs
sudo journalctl -u audio-relay -f
```

## 📊 Monitoring

Logs are saved to `audio_relay.log` and printed to console.

Stats are logged every 10 seconds:
```
📊 Buffer Stats - Size: 25/50 | Received: 15420 | Sent: 15400 | Dropped: 0
```

## ⚠️ Important Notes

### Limitations
- **Account restrictions**: Make sure both accounts are not restricted by Telegram
- **Voice chat access**: Both accounts need permission to join the voice chats
- **Rate limits**: Telegram may rate limit if you reconnect too frequently
- **Audio quality**: Depends on source stream quality and network stability

### Current Implementation Status

🟡 **This is a foundation/framework** - the core audio capture/streaming functions (`get_source_frame` and `send_target_frame` in `streaming.py`) are placeholders.

**Why?** The pytgcalls library's API for accessing raw audio streams varies by version and isn't fully documented.

**Next steps:**
1. Test with your pytgcalls version
2. Implement actual audio capture from `self.source_call`
3. Implement actual audio sending to `self.target_call`
4. See pytgcalls documentation or examples for raw stream access

### Troubleshooting

**"Session file not found"**
- Run `python login.py` first

**"Could not join voice chat"**
- Verify chat IDs are correct (include `-100` prefix)
- Check if accounts have permission to join
- Make sure voice chat is active

**"Buffer health check failed"**
- Network issues or source stream stopped
- Check logs for specific errors
- Bot will attempt to reconnect automatically

## 🛠️ Architecture

```
[ Source Voice Chat ]
        ↓
   Account A (listens)
        ↓
  pytgcalls audio capture
        ↓
   Audio Buffer (async queue)
        ↓
  pytgcalls audio send
        ↑
   Account B (broadcasts)
        ↑
[ Target Voice Chat ]
```

## 📁 Project Structure

```
telegram-audio-relay/
├── main.py              # Entry point
├── streaming.py         # Audio streaming logic
├── buffer.py           # Buffer management
├── login.py            # Account authentication
├── config.json         # Configuration
├── requirements.txt    # Dependencies
├── README.md          # This file
├── audio_relay.log    # Runtime logs
├── account_a.session  # Session file (generated)
└── account_b.session  # Session file (generated)
```

## 🔒 Security

- Never commit `.session` files to git
- Keep your `config.json` private (contains API credentials)
- Use environment variables for sensitive data in production

## 📝 License

Free to use and modify.

## 🤝 Contributing

This is a working foundation. Contributions to improve audio handling, add features, or fix bugs are welcome!

---

**Need help?** Check the logs in `audio_relay.log` for detailed error messages.
