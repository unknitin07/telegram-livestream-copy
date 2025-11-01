# 🎵 Complete Setup Guide for Telegram Audio Relay

This guide will help you set up the Telegram Audio Relay bot for real-time audio streaming between voice chats.

## 📋 Prerequisites

### 1. System Requirements

- **Operating System**: Linux (recommended), macOS, or Windows
- **Python**: 3.9 or higher (3.11 recommended)
- **FFmpeg**: Required for audio processing
- **RAM**: Minimum 512MB
- **Network**: Stable internet connection

### 2. Install FFmpeg

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg pulseaudio-utils
```

#### Linux (Fedora/RHEL)
```bash
sudo dnf install ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

#### Windows
1. Download from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract and add to PATH
3. Or use: `choco install ffmpeg` (with Chocolatey)

### 3. Verify FFmpeg Installation
```bash
ffmpeg -version
```

## 🚀 Installation Steps

### Step 1: Clone Repository
```bash
git clone <your-repo-url>
cd telegram-audio-relay
```

### Step 2: Create Virtual Environment (Recommended)
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

### Step 3: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Get Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org)
2. Login with your phone number
3. Click on "API Development Tools"
4. Create a new application:
   - **App title**: Any name (e.g., "Audio Relay Bot")
   - **Short name**: Any short name
   - **Platform**: Other
5. Copy your `api_id` and `api_hash`

### Step 5: Find Chat IDs

You need the chat IDs for both source and target voice chats.

#### Method 1: Using @userinfobot
1. Forward a message from the chat to [@userinfobot](https://t.me/userinfobot)
2. It will reply with the chat ID

#### Method 2: Using @raw_data_bot
1. Add [@raw_data_bot](https://t.me/raw_data_bot) to your group
2. The bot will show the chat ID

#### Method 3: Using Python
```python
from pyrogram import Client

app = Client("my_account", api_id=YOUR_API_ID, api_hash="YOUR_API_HASH")

async def main():
    async with app:
        async for dialog in app.get_dialogs():
            print(f"{dialog.chat.title or dialog.chat.first_name}: {dialog.chat.id}")

app.run(main())
```

**Note**: Group/channel IDs start with `-100` (e.g., `-1001234567890`)

### Step 6: Configure the Bot

Edit `config.json`:

```json
{
  "account_a": {
    "api_id": "12345678",
    "api_hash": "abcdef1234567890abcdef1234567890",
    "phone": "+1234567890",
    "session_name": "account_a"
  },
  "account_b": {
    "api_id": "12345678",
    "api_hash": "abcdef1234567890abcdef1234567890",
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

**Important**: 
- You can use the same `api_id` and `api_hash` for both accounts
- Both accounts should be different phone numbers
- Both accounts need permission to join the voice chats

### Step 7: Login to Accounts

```bash
python login.py
```

This will:
1. Ask for phone number verification code for Account A
2. Ask for phone number verification code for Account B
3. Save session files (only need to do this once)

## 🎮 Usage

### Basic Usage

```bash
python main.py
```

### Advanced Usage

#### Run in Background (Linux/macOS)

**Option 1: Using screen**
```bash
screen -S audio-relay
python main.py
# Press Ctrl+A then D to detach
# Reconnect: screen -r audio-relay
# Stop: screen -r audio-relay, then Ctrl+C
```

**Option 2: Using tmux**
```bash
tmux new -s audio-relay
python main.py
# Press Ctrl+B then D to detach
# Reconnect: tmux attach -t audio-relay
```

**Option 3: Using nohup**
```bash
nohup python main.py > output.log 2>&1 &
# Check logs: tail -f output.log
# Stop: kill $(ps aux | grep 'python main.py' | awk '{print $2}')
```

#### Run as Systemd Service (Linux)

1. Create service file:
```bash
sudo nano /etc/systemd/system/audio-relay.service
```

2. Add configuration:
```ini
[Unit]
Description=Telegram Audio Relay Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/telegram-audio-relay
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10
Environment="PATH=/path/to/venv/bin:/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
```

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable audio-relay
sudo systemctl start audio-relay
sudo systemctl status audio-relay
```

4. View logs:
```bash
sudo journalctl -u audio-relay -f
```

## 🔧 Audio Capture Setup

### Linux (PulseAudio)

#### 1. List Audio Sources
```bash
pactl list sources short
```

#### 2. Find Monitor Source
Look for sources with "monitor" in the name. Example output:
```
1    alsa_output.pci-0000_00_1f.3.analog-stereo.monitor    ...
```

#### 3. Configure in Code
Edit `streaming.py` or use the device name in `audio_capture.py`.

#### 4. Enable Loopback (if needed)
To capture Telegram's audio output:
```bash
pactl load-module module-loopback source=alsa_output.pci-0000_00_1f.3.analog-stereo.monitor
```

### macOS

#### 1. Install BlackHole (Virtual Audio Device)
```bash
brew install blackhole-2ch
```

#### 2. Configure Multi-Output Device
1. Open Audio MIDI Setup
2. Create Multi-Output Device
3. Add BlackHole and your speakers
4. Set as default output in Telegram

#### 3. List Devices
```bash
ffmpeg -f avfoundation -list_devices true -i ""
```

### Windows

#### 1. Enable Stereo Mix
1. Right-click speaker icon → Sounds
2. Recording tab
3. Right-click → Show Disabled Devices
4. Enable "Stereo Mix"

#### 2. Or Use Virtual Audio Cable
Download from: https://vb-audio.com/Cable/

#### 3. List Devices
```bash
ffmpeg -list_devices true -f dshow -i dummy
```

## 📊 Monitoring

### View Logs
```bash
tail -f audio_relay.log
```

### Statistics
The bot logs statistics every 10 seconds:
```
📊 Buffer Stats - Size: 25/50 | Received: 15420 | Sent: 15400 | Dropped: 0 | Idle: 2.3s
```

### Health Checks
- **Buffer health**: Checks every 30 seconds
- **Reconnection**: Automatic with configurable attempts
- **Connection status**: Real-time monitoring

## ⚠️ Troubleshooting

### "Session file not found"
**Solution**: Run `python login.py` first

### "Could not join voice chat"
**Solutions**:
- Verify chat IDs are correct (include `-100` prefix)
- Ensure both accounts have permission to join
- Make sure voice chat is active

### "FFmpeg not found"
**Solution**: Install FFmpeg and add to PATH

### No Audio Being Relayed
**Checks**:
1. Verify FFmpeg is capturing audio: Check logs
2. Ensure FIFO pipe is created: Should see `audio_relay_pipe.raw`
3. Check audio source device configuration
4. Verify both voice chats are active

### High CPU/Memory Usage
**Solutions**:
- Reduce buffer size in config
- Use lower audio quality
- Check for FFmpeg issues

### Rate Limiting
**Solutions**:
- Increase `reconnect_delay` in config
- Ensure stable network connection
- Avoid frequent reconnections

### Audio Quality Issues
**Solutions**:
- Check network bandwidth
- Verify audio source quality
- Adjust FFmpeg parameters
- Reduce buffer size for lower latency

## 🔒 Security Best Practices

1. **Never commit these files to Git**:
   - `*.session` files
   - `config.json` with credentials
   - Log files with sensitive data

2. **Use environment variables** (production):
```bash
export API_ID="12345678"
export API_HASH="abcdef..."
python main.py
```

3. **Secure your VPS**:
   - Use SSH keys, not passwords
   - Enable firewall
   - Keep system updated
   - Use non-root user

4. **Rotate credentials** periodically

## 🎯 Performance Tuning

### Low Latency Setup
```json
{
  "buffer_size": 25,
  "reconnect_delay": 3
}
```

### Stable Connection Setup
```json
{
  "buffer_size": 100,
  "reconnect_delay": 10
}
```

### High Quality Audio
Modify FFmpeg parameters in `audio_capture.py`:
```python
'-ar', '48000',  # Sample rate
'-ab', '128k',   # Bitrate
'-ac', '2',      # Channels
```

## 📚 Additional Resources

- [Pyrogram Documentation](https://docs.pyrogram.org/)
- [PyTgCalls Documentation](https://pytgcalls.github.io/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [Telegram Bot API](https://core.telegram.org/bots/api)

## 🆘 Getting Help

If you encounter issues:

1. Check `audio_relay.log` for detailed errors
2. Verify all prerequisites are installed
3. Ensure accounts aren't restricted by Telegram
4. Check if voice chats are active
5. Review this guide thoroughly

## 📝 Common Commands Cheatsheet

```bash
# Install dependencies
pip install -r requirements.txt

# Login accounts
python login.py

# Start bot
python main.py

# Run in background
screen -S audio-relay
python main.py

# View logs
tail -f audio_relay.log

# Stop bot
# Press Ctrl+C or:
pkill -f "python main.py"

# Test audio devices
python audio_capture.py

# Check FFmpeg
ffmpeg -version

# List PulseAudio sources (Linux)
pactl list sources short
```

---

Good luck with your audio relay setup! 🎵
