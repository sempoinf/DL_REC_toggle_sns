import os
import serial
import serial.tools.list_ports
import time
from dynamixel_sdk import *

# Constants
DXL_ID = 171
BAUDRATE = 115200
PROTOCOL_VERSION = 2.0
DEF_TMO = 100

DX_RESET_CMD = 23
DX_MEAS_START_STOP = 24
DX_TEMP_PORT_ID = 25

# Port related constants
PORT_REGISTERS = {
	51: "Port1",
	55: "Port2",
	59: "Port3",
	63: "Port4"
}

DX_SENSORS_STATUS = 83
DX_SENSORS_DATA_FIRST = 85
DX_SENSOR_DATA_LAST = 124
DX_UPD_COMMAND = 125

SNS_ETHANOL_ID = 46

def pause_script(message="Pausing script. Press Enter to continue..."):
	#print(message)
	input("Pausing script. Press Enter to continue...")

def connect_dev(dxl_id, baudrate):
	"""Connect to the device using available COM ports."""
	for port in sorted(serial.tools.list_ports.comports()):
		print(f"Trying port: {port.device}")
		try:
			ser = serial.Serial(port=port.device, baudrate=baudrate, timeout=DEF_TMO)
			portHandler = PortHandler(ser.name)
			packetHandler = PacketHandler(PROTOCOL_VERSION)
			portHandler.setBaudRate(baudrate)
			portHandler.openPort()

			outping_data, dxl_comm_result, dxl_error = packetHandler.ping(portHandler, dxl_id)
			if dxl_comm_result == COMM_SUCCESS:
				print("Device found!")
				return portHandler, packetHandler

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
	
	# Iterate through each port register to find the sensor
	for reg_address, port_name in PORT_REGISTERS.items():
		
		time.sleep(1)
		# Attempt to read the sensor ID from the current register
		sns_id_curr, dxl_comm_result, dxl_error = packetHandler.read2ByteTxRx(portHandler, dxl_id, reg_address)
		
		# Check for communication errors
		if dxl_comm_result != COMM_SUCCESS:
			comm_error_msg = packetHandler.getTxRxResult(dxl_comm_result)
			print(f"Communication error {port_name} ({hex(reg_address)}): {comm_error_msg} (Error Code: {dxl_comm_result})")
			continue  # Skip to the next register if there's a communication error
		elif dxl_error != 0:
			device_error_msg = packetHandler.getRxPacketError(dxl_error)
			print(f"Device error on register {reg_address} ({port_name}): {device_error_msg} (Error Code: {dxl_error})")
		else:
			print(f"Successfully read from {port_name}: Sensor ID {sns_id_curr}")		
		
		# Check if the current sensor ID matches the desired sensor ID
		if sns_id_curr == sns_id_desired:
			print(f"Sensor {sns_id_desired} found on {port_name}.")
			return reg_address  # Return the register address if the sensor is found
	
	# If no matching sensor is found after checking all ports
	print(f"Sensor {sns_id_desired} not found on any port.")
	return None
	
def toggle_sns(dxl_id, portHandler, packetHandler, sns_port):
	"""Initialize and toggle the sensor, then read its data."""
	print(f"Initializing and toggling sensor.")
	
	dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, dxl_id, (sns_port + 4), 3)
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
	vals_sns, dxl_comm_result, dxl_error = packetHandler.read4ByteTxRx(portHandler, dxl_id, DX_SENSORS_DATA_FIRST)
	if dxl_comm_result != COMM_SUCCESS:
		print(f"Communication error: {packetHandler.getTxRxResult(dxl_comm_result)}")
		return None
	elif dxl_error != 0:
		print(f"Error: {packetHandler.getRxPacketError(dxl_error)}")
		return None
	else:
		# print(f"Data from reg: {vals_sns}")
		f_num = vals_sns & 0xFFFF
		s_num = (vals_sns >> 16) & 0xFFFF
		list_of_data = [f_num, s_num]
		#list_of_data = [(vals_sns[i], vals_sns[i + 1]) for i in range(0, len(vals_sns), 2)]
		print(f"Data: {hex(vals_sns)}")
		print(f"Two 2-byte numbers: {list_of_data}")
		input("After read data from regs")
		return list_of_data

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
		sns_port = find_port_sns(DXL_ID, portHandler, packetHandler, SNS_ETHANOL_ID)
		if sns_port:
			toggle_sns(DXL_ID, portHandler, packetHandler, sns_port)
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