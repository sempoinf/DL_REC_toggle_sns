import os
import re
import serial
import serial.tools.list_ports
import time
from dynamixel_sdk import *
from enum import Enum

# Constants
DXL_ID = 171
BAUDRATE = 115200
PROTOCOL_VERSION = 2.0
DEF_TMO = 100

DX_RESET_CMD = 23
DX_MEAS_START_STOP = 24
DX_TEMP_PORT_ID = 25

DX_SENSORS_STATUS = 83
DX_SENSORS_DATA_FIRST = 85
DX_SENSOR_DATA_LAST = 124
DX_UPD_COMMAND = 125

SNS_ETHANOL_ID = 46

# Port related constants
PORT_REGISTERS = {
	51: "Port1",
	55: "Port2",
	59: "Port3",
	63: "Port4"
}

# Link between PortX, SNS_ID & SEL_RANGE
PORT_REGISTERS_RANGES = {
	"Port1": {"SNS_ID": 51, "SEL_RANGE": 53},
	"Port2": {"SNS_ID": 55, "SEL_RANGE": 57},
	"Port3": {"SNS_ID": 59, "SEL_RANGE": 61},
	"Port4": {"SNS_ID": 63, "SEL_RANGE": 65},
	"Port1S": {"SNS_ID": 67, "SEL_RANGE": 69},
	"Port2S": {"SNS_ID": 71, "SEL_RANGE": 73},
	"Port3S": {"SNS_ID": 75, "SEL_RANGE": 77},
	"Port4S": {"SNS_ID": 79, "SEL_RANGE": 81}
}

# Define communication statuses as an enum
class CommunicationStatus(Enum):
	SUCCESS = 0
	RX_TIMEOUT = -3001
	CRC_ERROR = -3002
	BUSY = -3003

# Define device errors as an enum
class DeviceError(Enum):
	VOLTAGE_ERROR = 1
	OVERHEATING = 2
	MOTOR_OVERLOAD = 3

# enum ranges of sns
# 0....01 in register DX_PORTX_SEL_RANGE for activate RANGE1
# 0....10 in register DX_PORTX_SEL_RANGE for activate RANGE2
# 0...100 in register DX_PORTX_SEL_RANGE for activate RANGE3
class SNS_ranges(Enum):
	RANGE_1 = 1
	RANGE_2 = 2
	RANGE_3 = 4
	RANGE_4 = 6
	RANGE_5 = 8
	RANGE_6 = 10
	RANGE_7 = 12
	RANGE_8 = 14


def pause_script(message="Pausing script. Press Enter to continue..."):
	#print(message)
	input("Pausing script. Press Enter to continue...")

def connect_dev(dxl_id, baudrate):
	"""
	Connect to the device using available COM ports.
	
	Parameters:
		dxl_id (int): The ID of the device to connect to.
		baudrate (int): The baud rate for the connection.
	
	Returns:
		tuple: (PortHandler, PacketHandler) if the device is found, (None, None) otherwise.
	"""
	# Define the pattern to match specific serial ports
	pattern = re.compile(r'^/dev/cu\.usbserial.*')
	
	for port in sorted(serial.tools.list_ports.comports(), key=lambda p: p.device):
		if pattern.match(port.device):
			print(f"Trying port: {port.device}")
			try:
				# Create serial connection
				ser = serial.Serial(port=port.device, baudrate=baudrate, timeout=100)
				
				# Initialize PortHandler and PacketHandler
				portHandler = PortHandler(ser.name)
				packetHandler = PacketHandler(PROTOCOL_VERSION)
				
				# Configure port handler and open port
				portHandler.setBaudRate(baudrate)
				portHandler.openPort()
				
				# Ping device
				outping_data, dxl_comm_result, dxl_error = packetHandler.ping(portHandler, dxl_id)
				if dxl_comm_result == COMM_SUCCESS:
					print("Device found!")
					return portHandler, packetHandler
					
				# If device not found, close port and continue
				print(f"No device on port {port.device}")
				portHandler.closePort()
				ser.close()
				
			except serial.SerialException as e:
				print(f"Serial error: {e}")
			except Exception as e:
				print(f"Unexpected error: {e}")
			
	print("Device not found")
	return None, None

def find_port_sns(dxl_id, portHandler, packetHandler, sns_id_desired):
	"""Find the port where the sensor with the desired ID is connected."""
	print(f"Checking where sensor {sns_id_desired} is connected.")
	
	time.sleep(1)
	# Iterate through each port register to find the sensor
	for port_name, registers in PORT_REGISTERS_RANGES.items():
		
		port_id_curr = registers["SNS_ID"]
		# Attempt to read the sensor ID from the current register
		sns_id_curr, dxl_comm_result, dxl_error = packetHandler.read2ByteTxRx(portHandler, dxl_id, port_id_curr)
		
		# Check for communication errors
		if CommunicationStatus(dxl_comm_result) != CommunicationStatus.SUCCESS:
			comm_error_msg = packetHandler.getTxRxResult(dxl_comm_result)
			print(f"Communication error on register {port_id_curr} ({port_name}): {comm_error_msg} (Error Code: {dxl_comm_result})")
			continue  # Skip to the next register if there's a communication error
		
		# Check for device errors
		if dxl_error != 0:
			device_error = DeviceError(dxl_error)
			print(f"Device error on register {port_id_curr} ({port_name}): {device_error.name} (Error Code: {device_error.value})")
		else:
			print(f"Successfully read from {port_name}: Sensor ID {sns_id_curr}")
		
		# Check if the current sensor ID matches the desired sensor ID
		if sns_id_curr == sns_id_desired:
			print(f"Sensor {sns_id_desired} found on {port_name}.")
			return port_name  # Return the register address if the sensor is found
	
	# If no matching sensor is found after checking all ports
	print(f"Sensor {sns_id_desired} not found on any port.")
	return None
	
def get_valid_delta_range(prompt="What delta of ranges do you want to activate? ", min_value = 1, max_value = 16):
	"""
	Prompts the user to input a valid delta range. Ensures the input is a positive integer greater than or equal to min_value.
	
	Parameters:
		prompt (str): The prompt message to display to the user.
		min_value (int): The minimum acceptable value for the delta range.
		max_value (int): The maximum acceptable value for the delta range.
	
	Returns:
		int: A valid integer delta range provided by the user.
	"""
	while True:
		user_input = input(prompt)
	
		# Try converting input to an integer
		try:
			delta_range = int(user_input)
			# Check if the integer is within the acceptable range
			if delta_range >= min_value and delta_range <= max_value :
				return delta_range
			else:
				print(f"Invalid input! Please enter a number greater than or equal to {min_value} and less than or equal to {max_value}.")
		except ValueError:
			print("Invalid input! Please enter a valid number.")
			

	
def toggle_sns(dxl_id, portHandler, packetHandler, port_n):
	"""Initialize and toggle the sensor, then read its data."""
	print(f"Initializing and toggling sensor.")
	
		
	sns_sel_range_id = PORT_REGISTERS_RANGES[port_n]["SEL_RANGE"]
	print(f"Reg of port for select range - {sns_sel_range_id}")
	
	# Sample values for demonstration
	# default_rang = SNS_ranges.RANGE_1.value + SNS_ranges.RANGE_2.value
	
	default_rang = SNS_ranges.RANGE_1.value
	
	# Flag to determine if a valid delta range was provided
	flag_input = False
	
	if flag_input:	
		"""For concole choose ranges"""
		delta_range = get_valid_delta_range()
		dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, dxl_id, sns_sel_range_id, delta_range)
	else:
		print(f"Default range - {bin(default_rang)}")
		dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, dxl_id, sns_sel_range_id, default_rang)
		
	if dxl_comm_result != COMM_SUCCESS:
		print(f"Error initializing sensor: {dxl_error}")
		return None
		
	print("Get Hot sensor...")
	
	# Sensor initialization code here
	for i in range(1, 7):
		time.sleep(9)
		outping_data, dxl_comm_result, dxl_error = packetHandler.ping(portHandler, dxl_id)
		print(f"Spend {i*10} secs")
		
		# # check complete ping command
		# if dxl_comm_result != COMM_SUCCESS:
		# 	print(f"Communication error: {packetHandler.getTxRxResult(dxl_comm_result)}")
		# elif dxl_error != 0:
		# 	print(f"Device error: {packetHandler.getRxPacketError(dxl_error)}")
		# else:
		# 	print(f"Ping successful: {outping_data}")
				
	pause_script("Sensor hot. Please touch the sensor and press Enter to continue...")
	
	print("Resuming data collection from the sensor...\n")
	
	# Continue with sensor data collection or other tasks
	dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, dxl_id, DX_MEAS_START_STOP, 1)
	if dxl_comm_result != COMM_SUCCESS:
		print(f"Error starting measurement: {dxl_error}")
		return None
	else:
		print(f"Start measuaring data from sensor")
	
def read_sensor_data(dxl_id, portHandler, packetHandler):
	time.sleep(9)
	for i in range(3):
		
		# calculate address shift
		addr = DX_SENSORS_DATA_FIRST + (i * 4)
		print(f"SNS_DATA_REG - {addr}")
		vals_sns, dxl_comm_result, dxl_error = packetHandler.read4ByteTxRx(portHandler, dxl_id, addr)
		if dxl_comm_result != COMM_SUCCESS:
			print(f"Communication error: {packetHandler.getTxRxResult(dxl_comm_result)}")
			return None
		elif dxl_error != 0:
			print(f"Error: {packetHandler.getRxPacketError(dxl_error)}")
			return None
		else:
			print(f"Data: {hex(vals_sns)}")
			# print(f"Data from reg: {vals_sns}")
			# f_num = vals_sns & 0xFFFF
			# s_num = (vals_sns >> 16) & 0xFFFF
			# list_of_data = [f_num, s_num]
			#list_of_data = [(vals_sns[i], vals_sns[i + 1]) for i in range(0, len(vals_sns), 2)]
			#print(f"Two 2-byte numbers: {list_of_data}")
			input("After read data from regs")
			# return list_of_data
		time.sleep(9)

def write_data_to_file(filename, data):
	"""Write sensor data to a file with pairs and a control string."""
	file_exists = os.path.isfile(filename)
	with open(filename, 'a') as file:
		if not file_exists:
			file.write("Sensor Data Pairs\n")
			file.write("=================\n\n")
		
		file.writelines(f"Pair {index+1}: {pair[0]:>6}, {pair[1]:>6}\n" for index, pair in enumerate(data))
		file.write("\nEND OF DATA\n")

def verify_data_written(filename):
	"""Verify if the data was written correctly by checking the control string."""
	if not os.path.isfile(filename):
		return False
	
	with open(filename, 'r') as file:
		return file.readlines()[-1].strip() == "END OF DATA"
		
def deinit_mes_sns(dxl_id, portHandler, packetHandler):
	"""Deinitialize the sensor."""
	print(f"Deinitializing measurement sensor.")
	dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, dxl_id, DX_MEAS_START_STOP, 0)
	if dxl_comm_result != COMM_SUCCESS:
		print(f"Error stopping measurement: {dxl_error}")

def recorder_reset(dxl_id, portHandler, packetHandler):
	"""Reset the recorder."""
	dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, dxl_id, DX_RESET_CMD, 1)
	return dxl_comm_result == COMM_SUCCESS

def main():
	portHandler, packetHandler = connect_dev(DXL_ID, BAUDRATE)
	if portHandler and packetHandler:
		port_name = find_port_sns(DXL_ID, portHandler, packetHandler, SNS_ETHANOL_ID)
		if port_name:
			toggle_sns(DXL_ID, portHandler, packetHandler, port_name)
			sensor_data_pairs = read_sensor_data(DXL_ID, portHandler, packetHandler)
			if sensor_data_pairs:
				print("Sensor Data Pairs:", sensor_data_pairs)
				
				filename = "results_term_compens.txt"
				write_data_to_file(filename, sensor_data_pairs)
				print(f"Data written to {filename}")
				
				if verify_data_written(filename):
					print("Data successfully written to file. Measurements can continue.")
					deinit_mes_sns(DXL_ID, portHandler, packetHandler)
					recorder_reset(DXL_ID, portHandler, packetHandler)
				else:
					print("Data write verification failed. Measurements should be stopped.")
		else:
			print("Port not found. Cannot toggle sensor.")
	else:
		print("Failed to connect to the device.")

if __name__ == '__main__':
	try:
		for i in range(3):
			main()
			alpha = input("If a mistake occurred, enter 'e' to exit, or press Enter to continue: ").strip().lower()
			if alpha == "e":
				print("Exiting due to user input.")
				sys.exit(0)
	except KeyboardInterrupt:
		print("\nScript interrupted by user.")
		sys.exit(0)