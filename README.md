# Sensor Management Script

## Overview

This Python script interacts with a sensor system connected via a serial port using the Dynamixel SDK. It performs tasks such as connecting to the device, finding specific sensors, starting and stopping measurements, and logging data to a file.

## Features

- Connects to a device via available COM ports.
- Identifies the port to which a specific sensor is connected.
- Starts and stops sensor measurements.
- Logs sensor data to a text file.
- Provides verification of data written to the file.

## Requirements

- Python 3.x
- Dynamixel SDK
- `pyserial` for serial communication

## Installation

1. **Clone the Repository**

    ```sh
    git clone https://github.com/yourusername/your-repo.git
    cd your-repo
    ```

2. **Install Dependencies**

    Ensure you have `pyserial` and `dynamixel_sdk` installed. You can install them using pip:

    ```sh
    pip install pyserial dynamixel_sdk
    ```

## Configuration

Before running the script, you need to adjust the following constants in the script:

- `DXL_ID`: ID of the Dynamixel device.
- `BAUDRATE`: Baud rate for serial communication.
- `PROTOCOL_VERSION`: Protocol version used by the Dynamixel device.
- `PORT_REGISTERS`: Dictionary mapping register addresses to port names.

## Usage

    Run the script from the command line:

   ```sh 
   python sns_talk_chat.py
   ```

The script will:

1.	Attempt to connect to the device on available COM ports.
2.	Check each port for the specified sensor ID.
3.	Start measurements on the identified sensor.
4.	Log the sensor data to results_term_compens.txt.
5.	Verify and print whether the data was successfully written.

## Example Output

   ```sh
   Trying port: /dev/cu.usbserial-1140
   Device found!
   Checking where sensor 46 is connected.
   Sensor 46 found on Port1.
   Initializing and toggling sensor 46.
   Sensor Data Pairs: [(2500, 3000), (2600, 3100), ...]
   Data written to results_term_compens.txt
   Data successfully written to file. Measurements can continue.
   ```

## Error Handling

If the script encounters errors such as communication issues or sensor not found, it will print error messages to the console. Ensure that your device is properly connected and configured.

## Contributing

Feel free to fork the repository and submit pull requests. If you encounter any issues or have suggestions for improvements, please open an issue on GitHub.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contact

For any questions or feedback, please contact
