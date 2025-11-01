#!/usr/bin/env python3
"""
Setup Test Script for Telegram Audio Relay
Verifies all requirements and dependencies are properly installed
"""

import sys
import subprocess
import platform
import os
from pathlib import Path

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print section header"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{Colors.RESET}\n")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

def check_python_version():
    """Check if Python version is adequate"""
    print_header("Checking Python Version")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    print(f"Python version: {version_str}")
    
    if version.major >= 3 and version.minor >= 9:
        print_success("Python version is compatible")
        return True
    else:
        print_error("Python 3.9 or higher is required")
        print_info("Current version: {version_str}")
        return False

def check_command_exists(command):
    """Check if a command exists in PATH"""
    try:
        result = subprocess.run(
            [command, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def check_ffmpeg():
    """Check if FFmpeg is installed"""
    print_header("Checking FFmpeg Installation")
    
    if check_command_exists('ffmpeg'):
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True
        )
        version_line = result.stdout.split('\n')[0]
        print(f"FFmpeg: {version_line}")
        print_success("FFmpeg is installed")
        return True
    else:
        print_error("FFmpeg is not installed")
        
        system = platform.system()
        if system == "Linux":
            print_info("Install with: sudo apt install ffmpeg")
        elif system == "Darwin":
            print_info("Install with: brew install ffmpeg")
        elif system == "Windows":
            print_info("Download from: https://ffmpeg.org/download.html")
            
        return False

def check_python_packages():
    """Check if required Python packages are installed"""
    print_header("Checking Python Packages")
    
    required_packages = [
        'pyrogram',
        'pytgcalls',
        'tgcrypto',
        'aiofiles',
        'coloredlogs'
    ]
    
    all_installed = True
    
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"{package} is installed")
        except ImportError:
            print_error(f"{package} is NOT installed")
            all_installed = False
    
    if not all_installed:
        print_info("Install all packages with: pip install -r requirements.txt")
    
    return all_installed

def check_config_file():
    """Check if config.json exists and is valid"""
    print_header("Checking Configuration File")
    
    config_path = Path('config.json')
    
    if not config_path.exists():
        print_error("config.json not found")
        print_info("Please create config.json with your API credentials")
        return False
    
    try:
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        required_keys = ['account_a', 'account_b', 'source_chat_id', 'target_chat_id']
        
        for key in required_keys:
            if key not in config:
                print_error(f"Missing required key: {key}")
                return False
        
        # Check for placeholder values
        if config['account_a']['api_id'] == "YOUR_API_ID":
            print_warning("config.json contains placeholder values")
            print_info("Please update with your actual API credentials")
            return False
        
        print_success("config.json is valid")
        return True
        
    except json.JSONDecodeError:
        print_error("config.json is not valid JSON")
        return False
    except Exception as e:
        print_error(f"Error reading config.json: {e}")
        return False

def check_session_files():
    """Check if session files exist"""
    print_header("Checking Session Files")
    
    session_a = Path('account_a.session')
    session_b = Path('account_b.session')
    
    has_sessions = True
    
    if session_a.exists():
        print_success("account_a.session exists")
    else:
        print_warning("account_a.session not found")
        has_sessions = False
    
    if session_b.exists():
        print_success("account_b.session exists")
    else:
        print_warning("account_b.session not found")
        has_sessions = False
    
    if not has_sessions:
        print_info("Run 'python login.py' to create session files")
    
    return has_sessions

def check_audio_system():
    """Check audio system availability"""
    print_header("Checking Audio System")
    
    system = platform.system()
    
    if system == "Linux":
        if check_command_exists('pactl'):
            print_success("PulseAudio is available")
            
            # List audio sources
            try:
                result = subprocess.run(
                    ['pactl', 'list', 'sources', 'short'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                sources = result.stdout.strip().split('\n')
                print_info(f"Found {len(sources)} audio source(s)")
                
                # Check for monitor sources
                monitors = [s for s in sources if 'monitor' in s.lower()]
                if monitors:
                    print_success(f"Found {len(monitors)} monitor source(s) for audio capture")
                else:
                    print_warning("No monitor sources found for audio capture")
                    print_info("You may need to configure audio loopback")
                    
            except Exception as e:
                print_warning(f"Could not list audio sources: {e}")
                
            return True
        else:
            print_warning("PulseAudio not detected")
            return False
            
    elif system == "Darwin":
        print_info("macOS detected")
        print_info("Consider installing BlackHole for audio routing: brew install blackhole-2ch")
        return True
        
    elif system == "Windows":
        print_info("Windows detected")
        print_info("Ensure 'Stereo Mix' is enabled or install Virtual Audio Cable")
        return True
    
    return False

def check_project_files():
    """Check if all required project files exist"""
    print_header("Checking Project Files")
    
    required_files = [
        'main.py',
        'streaming.py',
        'buffer.py',
        'audio_capture.py',
        'login.py',
        'requirements.txt',
        'README.md'
    ]
    
    all_exist = True
    
    for file in required_files:
        if Path(file).exists():
            print_success(f"{file} exists")
        else:
            print_error(f"{file} NOT found")
            all_exist = False
    
    return all_exist

def main():
    """Run all checks"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print("🎵 Telegram Audio Relay - Setup Test")
    print(f"{'='*60}{Colors.RESET}\n")
    
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    
    results = {
        "Python Version": check_python_version(),
        "FFmpeg": check_ffmpeg(),
        "Python Packages": check_python_packages(),
        "Configuration": check_config_file(),
        "Session Files": check_session_files(),
        "Audio System": check_audio_system(),
        "Project Files": check_project_files()
    }
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"{check:.<40} {status}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} checks passed{Colors.RESET}\n")
    
    if passed == total:
        print_success("All checks passed! You're ready to run the bot.")
        print_info("Start with: python main.py")
    else:
        print_warning(f"{total - passed} check(s) failed. Please fix the issues above.")
        
        # Provide next steps
        if not results["Python Packages"]:
            print_info("\nNext step: pip install -r requirements.txt")
        elif not results["Configuration"]:
            print_info("\nNext step: Configure config.json with your API credentials")
        elif not results["Session Files"]:
            print_info("\nNext step: python login.py")
    
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted{Colors.RESET}\n")
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {e}{Colors.RESET}\n")
        sys.exit(1)
