import serial
import serial.tools.list_ports
import time
import platform
from website.config import Config

class ESP32Communicator:
    def __init__(self):
        self.serial_connection = None
        self.connected = False
        self.config = Config()
        self._set_platform_specific_config()

    def _set_platform_specific_config(self):
        """Set platform-specific serial port pattern"""
        system = platform.system()
        if system == 'Windows':
            setattr(self.config, 'SERIAL_PORT_PATTERN', 'COM*')
        elif system == 'Linux':
            setattr(self.config, 'SERIAL_PORT_PATTERN', '/dev/ttyUSB*')
        elif system == 'Darwin':  # macOS
            setattr(self.config, 'SERIAL_PORT_PATTERN', '/dev/tty.usbserial*')

    def get_available_ports(self):
        """Get list of available serial ports"""
        try:
            ports = []
            for port in serial.tools.list_ports.comports():
                if port.device.startswith(self.config.SERIAL_PORT_PATTERN):
                    ports.append(port.device)
            return ports
        except Exception as e:
            print(f"Error getting available ports: {str(e)}")
            return []

    def connect(self, port):
        """Connect to ESP32 on specified port"""
        try:
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=self.config.ESP32_BAUD_RATE,
                timeout=self.config.ESP32_TIMEOUT,
                write_timeout=self.config.ESP32_WRITE_TIMEOUT
            )
            time.sleep(2)  # Wait for ESP32 to initialize
            self.connected = True
            return True, "Successfully connected to ESP32"
        except Exception as e:
            self.connected = False
            return False, f"Connection error: {str(e)}"

    def disconnect(self):
        """Disconnect from ESP32"""
        try:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            self.connected = False
            return True, "Successfully disconnected from ESP32"
        except Exception as e:
            return False, f"Disconnection error: {str(e)}"

    def send_command(self, command):
        """Send command to ESP32 and get response"""
        if not self.connected or not self.serial_connection:
            return False, "Not connected to ESP32"

        try:
            # Add command terminator
            full_command = command + self.config.ESP32_COMMAND_TERMINATOR
            self.serial_connection.write(full_command.encode())
            
            # Wait for response
            response = self.serial_connection.readline().decode().strip()
            
            if response:
                return True, response
            else:
                return False, "No response received"
        except Exception as e:
            return False, f"Command error: {str(e)}"

    def is_connected(self):
        """Check if ESP32 is connected"""
        return self.connected and self.serial_connection and self.serial_connection.is_open

    def get_status(self):
        """Get ESP32 status"""
        if not self.connected:
            return "Disconnected"
        
        try:
            success, response = self.send_command(self.config.ESP32_DEFAULT_COMMANDS['status'])
            if success:
                return f"Connected - {response}"
            else:
                return "Connected but status check failed"
        except:
            return "Connected but status check failed"

    def is_esp32_available(self):
        """Check if ESP32 is available on the system"""
        try:
            ports = self.get_available_ports()
            return len(ports) > 0
        except:
            return False 