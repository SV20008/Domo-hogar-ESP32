"""
============================================================
 DomoHogar ESP32 - Firmware con DIAGNOSTICO por LED
 El LED amarillo (GPIO2) avisa en que etapa va el arranque:
   * 1 destello largo (1 seg)        -> el codigo ESTA corriendo
   * 3 parpadeos rapidos             -> Wi-Fi conectado OK
   * 6 parpadeos muy rapidos         -> Broker MQTT conectado OK
   * parpadeo LENTO sin parar (1/1s) -> FALLO al conectar al broker
   * el LED nunca enciende           -> el codigo no esta corriendo
                                        (simulacion en pausa / archivo mal)
 Si llega a los 6 parpadeos, ya esta publicando por MQTT.
============================================================
"""
import network, time
from machine import Pin, ADC, PWM, time_pulse_us
from umqtt.simple import MQTTClient
import dht

# ===================== CONFIGURACION =====================
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASS = ""
BROKER    = "broker.hivemq.com"

PREFIJO   = "uesfia-g3"
CLIENT_ID = "esp32-domohogar-g3"
BASE      = PREFIJO + "/casa"

T_TEMP = BASE + "/sala/temperatura"
T_HUM  = BASE + "/sala/humedad"
T_LUZ  = BASE + "/sala/luz"
T_MOV  = BASE + "/seguridad/movimiento"
T_NIV  = BASE + "/tanque/nivel"
T_LED   = BASE + "/actuadores/led"
T_SERVO = BASE + "/actuadores/servo"
T_BUZ   = BASE + "/actuadores/buzzer"
T_FAN   = BASE + "/actuadores/ventilador"
T_MODO  = BASE + "/modo"

# ===================== PINES =====================
dht22  = dht.DHT22(Pin(15))
pir    = Pin(13, Pin.IN)
ldr    = ADC(Pin(34)); ldr.atten(ADC.ATTN_11DB)
trig   = Pin(5, Pin.OUT)
echo   = Pin(19, Pin.IN)
led    = Pin(2, Pin.OUT)
buzzer = Pin(4, Pin.OUT)
fan    = Pin(23, Pin.OUT)
servo  = PWM(Pin(18), freq=50)

auto_mode = True

# ===================== SEÑALES POR LED =====================
def parpadear(n, on=0.1, off=0.1):
    for _ in range(n):
        led.value(1); time.sleep(on)
        led.value(0); time.sleep(off)

# Señal 0: el codigo arranco
led.value(1); time.sleep(1); led.value(0); time.sleep(0.3)

# ===================== FUNCIONES =====================
def servo_angulo(grados):
    duty = int(26 + (grados / 180) * (128 - 26))
    servo.duty(duty)

def medir_distancia_cm():
    trig.value(0); time.sleep_us(2)
    trig.value(1); time.sleep_us(10); trig.value(0)
    dur = time_pulse_us(echo, 1, 30000)
    if dur < 0:
        return -1
    return round((dur * 0.0343) / 2, 1)

def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    print("Conectando a Wi-Fi", end="")
    for _ in range(40):                 # ~12 s maximo
        if wlan.isconnected():
            break
        print("."); time.sleep(0.3)
    return wlan.isconnected()

def callback(topic, msg):
    global auto_mode
    t = topic.decode(); m = msg.decode().strip().upper()
    print("Comando:", t, "=", m)
    if t == T_MODO:    auto_mode = (m == "AUTO")
    elif t == T_LED:   led.value(1 if m == "ON" else 0)
    elif t == T_BUZ:   buzzer.value(1 if m == "ON" else 0)
    elif t == T_FAN:   fan.value(1 if m == "ON" else 0)
    elif t == T_SERVO: servo_angulo(90 if m == "ABRIR" else 0)

# ===================== ARRANQUE =====================
if conectar_wifi():
    print("Wi-Fi OK")
    parpadear(3)                        # Señal 1: Wi-Fi OK
else:
    print("Wi-Fi FALLO")

cliente = MQTTClient(CLIENT_ID, BROKER, keepalive=60)
cliente.set_callback(callback)

try:
    cliente.connect()
    print("Broker MQTT OK:", BROKER)
    parpadear(6, 0.06, 0.06)            # Señal 2: MQTT OK
except Exception as e:
    print("ERROR al conectar al broker:", e)
    while True:                         # Señal de error: parpadeo lento
        led.value(1); time.sleep(1)
        led.value(0); time.sleep(1)

for t in (T_LED, T_SERVO, T_BUZ, T_FAN, T_MODO):
    cliente.subscribe(t)
servo_angulo(0)

# ===================== BUCLE PRINCIPAL =====================
while True:
    try:
        dht22.measure()
        temp = dht22.temperature(); hum = dht22.humidity()
    except Exception:
        temp, hum = 0, 0
    luz = ldr.read(); mov = pir.value(); niv = medir_distancia_cm()

    cliente.publish(T_TEMP, str(temp))
    cliente.publish(T_HUM,  str(hum))
    cliente.publish(T_LUZ,  str(luz))
    cliente.publish(T_MOV,  str(mov))
    cliente.publish(T_NIV,  str(niv))
    print("T=%sC H=%s%% Luz=%s Mov=%s Niv=%scm [%s]" %
          (temp, hum, luz, mov, niv, "AUTO" if auto_mode else "MANUAL"))

    if auto_mode:
        led.value(1 if luz < 1000 else 0)
        fan.value(1 if temp >= 28 else 0)
        buzzer.value(1 if mov == 1 else 0)

    for _ in range(20):
        cliente.check_msg()
        time.sleep(0.1)