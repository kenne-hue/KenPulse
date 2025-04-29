import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Base Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///website/database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'kenpulse254@gmail.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = 'kenpulse254@gmail.com'
    
    # Admin Configuration
    ADMIN_ACCESS_CODE = os.environ.get('ADMIN_ACCESS_CODE', 'admin123')
    
    # ESP32 Configuration
    ESP32_BAUD_RATE = 115200
    ESP32_TIMEOUT = 1
    ESP32_WRITE_TIMEOUT = 1
    ESP32_READ_TIMEOUT = 1
    
    # Serial Port Configuration
    SERIAL_PORT_PATTERN = 'COM*'  # For Windows
    # SERIAL_PORT_PATTERN = '/dev/ttyUSB*'  # For Linux
    # SERIAL_PORT_PATTERN = '/dev/tty.usbserial*'  # For macOS
    
    # Command Configuration
    ESP32_COMMAND_TERMINATOR = '\r\n'
    ESP32_RESPONSE_TERMINATOR = '\r\n'
    
    # Default Commands
    ESP32_DEFAULT_COMMANDS = {
        'status': 'AT+STATUS',
        'reset': 'AT+RST',
        'version': 'AT+VERSION',
        'help': 'AT+HELP'
    }
    
    # Response Timeouts
    ESP32_RESPONSE_TIMEOUT = 5  # seconds
    
    # Reconnection Settings
    ESP32_RECONNECT_ATTEMPTS = 3
    ESP32_RECONNECT_DELAY = 1  # seconds
    
    # Upload Configuration
    UPLOAD_FOLDER = 'website/static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} 