import network
from microdot import Microdot, send_file, Response, redirect
import random, gc
import urequests as requests
from machine import Pin, I2C, ADC
from bme_module import BME280Module
from utime import sleep
from hcsr04 import HCSR04

# === Inisialisasi Sensor & Aktuator ===
sda = Pin(21)
scl = Pin(22)
bme_module = BME280Module(0, scl, sda)
sensor = HCSR04(trigger_pin=5, echo_pin=18, echo_timeout_us=10000)
gas = ADC(Pin(36))
ldr = ADC(Pin(33))

air = Pin(25, Pin.OUT)
fan = Pin(26, Pin.OUT)
lamp = Pin(27, Pin.OUT)
sprinkle = Pin(15, Pin.OUT)
led = Pin(16, Pin.OUT)
led_state = {"status": "off"}

# Mode jamur (default incubation)
current_mode = {"mode": "incubation"}

# === WiFi Config ===
SSID = "BOE-"
PASSWORD = ""

def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    print("Menghubungkan ke Wi-Fi...")
    while not wlan.isconnected():
        sleep(1)
        print("Masih mencoba...")
    print("Wi-Fi Terhubung!")
    print("Alamat IP:", wlan.ifconfig()[0])
    return wlan.ifconfig()[0]

ip_address = connect_wifi(SSID, PASSWORD)

# === Microdot ===
app = Microdot()
Response.default_content_type = 'application/json'

# Simulasi login session
login_session = {"logged_in": False}

# === API Flask (ambil user) ===
FLASK_API_URL = "http://192.168.56.51:5050"

# === ROUTES ===
@app.route('/')
def index(request):
    if not login_session["logged_in"]:
        return redirect("/login")
    return send_file('templates/index.html')

@app.route('/static/<path:path>')
def static_files(request, path):
    return send_file('static/' + path)

# Halaman login
@app.route('/login', methods=['GET', 'POST'])
def login(request):
    if request.method == 'GET':
        return send_file('templates/login.html')

    if request.method == 'POST':
        try:
            username = request.form.get("username")
            pin = request.form.get("pin")

            # Ambil user dari Flask
            response = requests.get(f"{FLASK_API_URL}/api/user")
            users = response.json()
            response.close()
            gc.collect()

            for user in users:
                if user.get("username") == username and user.get("pin") == pin:
                    login_session["logged_in"] = True
                    login_session["username"] = user.get("name")
                    return redirect("/")  # sukses -> dashboard

            return send_file('templates/login.html', {"error": "Login gagal!"})

        except Exception as e:
            return {"error": str(e)}, 500

# Logout
@app.route('/logout')
def logout(request):
    login_session["logged_in"] = False
    login_session["username"] = None
    return redirect("/login")

# API untuk info user login
@app.route('/api/user/status')
def user_status(request):
    return login_session

# === API MODE JAMUR ===
@app.route('/api/mode', methods=['POST'])
def set_mode(request):
    global current_mode
    mode = request.json.get('mode')
    if mode in ["incubation", "fruiting"]:
        current_mode["mode"] = mode
    return current_mode

@app.route('/api/mode/status')
def mode_status(request):
    return current_mode

# === API DATA SENSOR ===
@app.route('/api/data')
def data_api(request):
    valuegas = gas.read()
    valueldr = ldr.read()
    distance = sensor.distance_cm()
    temp, pressure, humdt, altitude = bme_module.get_sensor_readings()
    humi = round(random.uniform(70, 100), 2)
        
    # Kontrol pompa air (buzz)
    databuzz = 0
    if distance > 100:
        air.on()
        databuzz = 1
    else:
        air.off()

    # Kontrol fan, lamp, sprinkle
    datafan = datalamp = datasprinkle = 0
    if temp > 30:
        fan.on(); sprinkle.on()
        datafan, datasprinkle = 1, 1
    else:
        fan.off(); sprinkle.on()
        if temp < 27:
            lamp.on(); datalamp = 1
        else:
            lamp.off()

    # Status jamur
    status = "Happy"
    mode = current_mode["mode"]
    if mode == "incubation":
        if not (24 <= temp <= 29 and humi >= 70):
            status = "Not Happy"
    elif mode == "fruiting":
        if not (25 <= temp <= 30 and 80 <= humi <= 95):
            status = "Not Happy"

    # Setelah dapat data sensor
    data = {
        "mode": mode,
        "temperature": temp,
        "pressure": pressure,
        "humidity": humi,
        "altitude": altitude,
        "distance": distance,
        "valuegas": valuegas,
        "valueldr": valueldr,
        "databuzz": databuzz,
        "datafan": datafan,
        "datalamp": datalamp,
        "datasprinkle": datasprinkle,
        "status": status
    }
    try:
        requests.post(f"{FLASK_API_URL}/api/data/save", json=data)
    except Exception as e:
        print("Gagal kirim ke server:", e)
        
    return data

# === API LAMPU ===
@app.route('/api/lamp', methods=['POST'])
def control_lamp(request):
    global led_state
    action = request.json.get('action')
    if action == "on":
        led.on(); led_state["status"] = "on"
    elif action == "off":
        led.off(); led_state["status"] = "off"
    return led_state

@app.route('/api/lamp/status')
def lamp_status(request):
    return led_state

# === Jalankan server ===
if __name__ == '__main__':
    print(ip_address)
    app.run(host=ip_address, port=5000, debug=True)
