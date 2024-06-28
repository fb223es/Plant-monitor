import network
import urequests as requests
from machine import Pin, ADC
import utime as time
from dht import DHT11

#2 murgröns
#1 novemberkaktus
#0 ariala

# Pin assignments
led_pin = Pin(12, Pin.OUT)
soil_pins = [ADC(Pin(26)), ADC(Pin(27)), ADC(Pin(28))]
sensor_humAndTemp = DHT11(Pin(14, Pin.IN, Pin.PULL_UP))

# Constants for moisture sensor
min_moisture = 0
max_moisture = 65535

# Delays in seconds
DELAY = 5*60  # Delay for temperature and humidity sensor
DELAY_SOIL = 43200  # Delay for soil moisture sensor (12 hours)

# WiFi credentials
WIFI_SSID = "Your_WiFi_SSID"
WIFI_PASS = "Your_WiFi_Password"

# Ubidots configuration
TOKEN = "BBUS-MIjODvzAKxxuZHCzIZVjq7IBsAmUZn"
DEVICE_LABEL = "picoW"

TEMP_VARIABLE_LABEL = "temperature"
HUM_VARIABLE_LABEL = "humidity"
ALARM_VARIABLE_LABEL = "alarm"

WATER_VARIABLE_LABELS = ["water0", "water1", "water2"]
MOISTURE_VARIABLE_LABELS = ["moisture0", "moisture1", "moisture2"]

# Variable to store last measured moisture
last_moisture = [None, None, None]

# Function to control external LED
def led():
    led_pin.value(1)

# Function to build JSON payload for Ubidots
def build_json(temperature, humidity, alarm, water, moisture):
    try:
        data = {
            TEMP_VARIABLE_LABEL: {"value": temperature},
            HUM_VARIABLE_LABEL: {"value": humidity},
            ALARM_VARIABLE_LABEL: {"value": alarm}
        }
        for i in range(3):
            data[WATER_VARIABLE_LABELS[i]] = {"value": water[i]}
            data[MOISTURE_VARIABLE_LABELS[i]] = {"value": moisture[i]}
        return data
    except Exception as e:
        print("Error building JSON:", e)
        return None

# Function to send data to Ubidots
def sendData(device, data):
    try:
        url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{device}"
        headers = {"X-Auth-Token": TOKEN, "Content-Type": "application/json"}

        if data is not None:
            print("Sending data to Ubidots:", data)
            req = requests.post(url=url, headers=headers, json=data)
            return req.json()
        else:
            print("No data to send.")
    except Exception as e:
        print("Error sending data:", e)

# Function to get data from Ubidots
def getData(device, variable):
    try:
        url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{device}/{variable}/lv"
        headers = {"X-Auth-Token": TOKEN, "Content-Type": "application/json"}
        req = requests.get(url=url, headers=headers)
        if req.status_code == 200:
            return req.json()
        else:
            print("Failed to get data from Ubidots:", req.status_code, req.text)
            return None
    except Exception as e:
        print("Error getting data:", e)
        return None

# Function to measure temperature and humidity
def measureTemperatureHumidity():
    try:
        sensor_humAndTemp.measure()
        tempC = sensor_humAndTemp.temperature()
        hum = sensor_humAndTemp.humidity()
        print(f"Temperature: {tempC}°C, Humidity: {hum}%")
        return tempC, hum
    except OSError as e:
        print("Failed to read from DHT11 sensor:", e)
        return None, None

# Function to measure soil moisture
def measureSoilMoisture():
    try:
        moisture = []
        for pin in soil_pins:
            value = round((max_moisture - pin.read_u16()) * 100 / (max_moisture - min_moisture))
            if 0 <= value <= 100:
                print(f"Moisture is {value}%")
            moisture.append(value)
        return moisture
    except Exception as e:
        print("Error measuring soil moisture:", e)
        return [None, None, None]

# Main program flow
def main():
    global last_moisture  # Use global variable for last measured moisture
    try:
        # Connect to WiFi
        connect()

        # Turn on LED
        led()

        # Measure soil moisture at startup
        initial_moisture = measureSoilMoisture()
        if initial_moisture is not None:
            last_moisture = initial_moisture
            data = build_json(0, 0, 0, [0, 0, 0], last_moisture)  # Assuming initial values for temperature, humidity, alarm, and water
            sendData(DEVICE_LABEL, data)
        else:
            last_moisture = [None, None, None]

        # Initialize next soil measurement time
        next_soil_measurement = time.time() + DELAY_SOIL

        while True:
            try:
                # Measure temperature and humidity
                tempC, hum = measureTemperatureHumidity()

                # Determine the alarm value based on humidity
                if hum is not None and (hum < 45 or hum > 60):
                    alarm_value = 0
                else:
                    alarm_value = 1

                print(f"Alarm value: {alarm_value}")

                # Check if it's time to measure soil moisture
                if time.time() >= next_soil_measurement:
                    # Measure soil moisture
                    moisture = measureSoilMoisture()

                    if moisture is not None:
                        last_moisture = moisture

                    # Update next soil measurement time
                    next_soil_measurement = time.time() + DELAY_SOIL

                # Determine water values based on moisture levels
                water_values = [1 if m < 30 else 0 for m in last_moisture]

                # Send data to Ubidots
                data = build_json(tempC, hum, alarm_value, water_values, last_moisture)
                sendData(DEVICE_LABEL, data)

            except Exception as e:
                print("An error occurred in the main loop:", e)

            time.sleep(DELAY)  # Delay between temperature/humidity measurements

    except Exception as e:
        print("An error occurred in the main program:", e)

# Execute the main program
main()
