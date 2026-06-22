import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

"""
--- CONFIGURACIÓN DE TÓPICOS INDIVIDUALIZADOS (Filtro Anti-Saturación) ---
"""
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 8884 # Ajustado al puerto seguro obligatorio
MQTT_CLIENT_ID = "dashboard-domotica-py-g3" 
PREFIJO = "uesfia-g3/casa"

MQTT_SUBSCRIBE_TOPIC = PREFIJO + "/#"

# Sensores
T_TEMP = PREFIJO + "/sala/dht22/temperatura"
T_HUM  = PREFIJO + "/sala/dht22/humedad"
T_MOV  = PREFIJO + "/entrada/pir/movimiento"
T_LUZ  = PREFIJO + "/exterior/ldr/luz"

# Actuadores
T_LED_SET    = PREFIJO + "/sala/led/set"
T_SERVO_SET  = PREFIJO + "/garage/servo/set"
T_BUZZER_SET = PREFIJO + "/alarma/buzzer/set"

# Retornos de Estado
T_LED_STATE    = PREFIJO + "/sala/led/state"
T_SERVO_STATE  = PREFIJO + "/garage/servo/state"
T_BUZZER_STATE = PREFIJO + "/alarma/buzzer/state"

ultima_temp = 0.0
ultima_hum = 0.0
ultima_luz = 0.0

def iniciar_bd():
    conn = sqlite3.connect("domotica_ues.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS historico (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha TEXT,
                        temperatura REAL,
                        humedad REAL,
                        luz REAL)''')
    conn.commit()
    conn.close()

def guardar_en_bd():
    try:
        conn = sqlite3.connect("domotica_ues.db")
        cursor = conn.cursor()
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO historico (fecha, temperatura, humedad, luz) VALUES (?, ?, ?, ?)",
                       (fecha_actual, ultima_temp, ultima_hum, ultima_luz))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Error al escribir en Base de Datos:", e)

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UES - Dashboard Domótico")
        self.root.geometry("700x650")
        
        style = ttk.Style()
        style.theme_use('clam')
        
        f_monitoreo = ttk.LabelFrame(root, text=" Telemetría de Sensores (ESP32) ", padding=15)
        f_monitoreo.pack(pady=15, fill="x", padx=20)
        
        self.lbl_temp = ttk.Label(f_monitoreo, text="Temperatura Sala: -- °C", font=("Arial", 13, "bold"))
        self.lbl_temp.pack(anchor="w", pady=3)
        self.lbl_hum = ttk.Label(f_monitoreo, text="Humedad Sala: -- %", font=("Arial", 13, "bold"))
        self.lbl_hum.pack(anchor="w", pady=3)
        self.lbl_luz = ttk.Label(f_monitoreo, text="Luz Exterior (LDR): --", font=("Arial", 13, "bold"))
        self.lbl_luz.pack(anchor="w", pady=3)
        self.lbl_mov = ttk.Label(f_monitoreo, text="Estado Entrada (PIR): Sin movimiento", font=("Arial", 13, "bold"), foreground="green")
        self.lbl_mov.pack(anchor="w", pady=3)
        
        f_estados = ttk.LabelFrame(root, text=" Estado Confirmado del Hardware ", padding=10)
        f_estados.pack(fill="x", padx=20, pady=5)
        
        self.lbl_led_st = ttk.Label(f_estados, text="Luz Sala: OFF", font=("Arial", 10, "bold"))
        self.lbl_led_st.pack(side="left", padx=15)
        self.lbl_servo_st = ttk.Label(f_estados, text="Portón Garaje: 0°", font=("Arial", 10, "bold"))
        self.lbl_servo_st.pack(side="left", padx=15)
        self.lbl_buz_st = ttk.Label(f_estados, text="Alarma Alerta: OFF", font=("Arial", 10, "bold"))
        self.lbl_buz_st.pack(side="left", padx=15)

        f_control = ttk.LabelFrame(root, text=" Panel de Control Remoto ", padding=15)
        f_control.pack(pady=15, fill="x", padx=20)
        f_botones = ttk.Frame(f_control, padding=5)
        f_botones.pack()
        
        ttk.Button(f_botones, text="Encender LED", command=lambda: self.enviar_cmd(T_LED_SET, "ON")).grid(row=0, column=0, padx=10, pady=5)
        ttk.Button(f_botones, text="Apagar LED", command=lambda: self.enviar_cmd(T_LED_SET, "OFF")).grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(f_botones, text="Abrir Cochera (90°)", command=lambda: self.enviar_cmd(T_SERVO_SET, "OPEN")).grid(row=1, column=0, padx=10, pady=5)
        ttk.Button(f_botones, text="Cerrar Cochera (0°)", command=lambda: self.enviar_cmd(T_SERVO_SET, "CLOSE")).grid(row=1, column=1, padx=10, pady=5)
        ttk.Button(f_botones, text="Activar Alarma", command=lambda: self.enviar_cmd(T_BUZZER_SET, "ON")).grid(row=2, column=0, padx=10, pady=5)
        ttk.Button(f_botones, text="Apagar Alarma", command=lambda: self.enviar_cmd(T_BUZZER_SET, "OFF")).grid(row=2, column=1, padx=10, pady=5)
        
        f_hist = ttk.LabelFrame(root, text=" Almacenamiento e Históricos ", padding=15)
        f_hist.pack(pady=15, fill="x", padx=20)
        ttk.Button(f_hist, text="Generar Gráfica de Temperatura Histórica", command=self.graficar).pack()

    def enviar_cmd(self, topico, comando):
        client.publish(topico, comando, qos=0)
        print(f"Comando enviado -> {topico} = {comando}")

    def graficar(self):
        conn = sqlite3.connect("domotica_ues.db")
        cursor = conn.cursor()
        cursor.execute("SELECT fecha, temperatura FROM historico ORDER BY id DESC LIMIT 12")
        filas = cursor.fetchall()
        conn.close()
        
        if filas:
            horas = [f[0].split()[1] for f in filas][::-1]
            temps = [f[1] for f in filas][::-1]
            
            fig, ax = plt.subplots(figsize=(6, 3.5))
            ax.plot(horas, temps, marker='o', color='darkblue', linestyle='-')
            ax.set_title("Variación Térmica Reciente (Dht22)")
            ax.set_ylabel("°C")
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            ventana = tk.Toplevel(self.root)
            ventana.title("Historial de Datos")
            canvas = FigureCanvasTkAgg(fig, master=ventana)
            canvas.draw()
            canvas.get_tk_widget().pack(padx=10, pady=10)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Dashboard Python conectado de forma SEGURA al Broker de HiveMQ (Puerto 8884)")
        client.subscribe(MQTT_SUBSCRIBE_TOPIC)
        print(f"Suscripción activa: {MQTT_SUBSCRIBE_TOPIC}")
    else:
        print(f"Error de conexión en puerto seguro: rc={rc}")

def on_message(client, userdata, msg):
    global ultima_temp, ultima_hum, ultima_luz
    try:
        payload = msg.payload.decode().strip()
        topico = msg.topic
        print(f"Mensaje Recibido -> {topico} : {payload}")
        
        if topico == T_TEMP:
            ultima_temp = float(payload)
            app.lbl_temp.config(text=f"Temperatura Sala: {ultima_temp} °C")
        elif topico == T_HUM:
            ultima_hum = float(payload)
            app.lbl_hum.config(text=f"Humedad Sala: {ultima_hum} %")
        elif topico == T_LUZ:
            ultima_luz = float(payload)
            app.lbl_luz.config(text=f"Luz Exterior (LDR): {ultima_luz}")
            guardar_en_bd()
        elif topico == T_MOV:
            if payload == "1":
                app.lbl_mov.config(text="Estado Entrada (PIR): ¡MOVIMIENTO DETECTADO!", foreground="red")
            else:
                app.lbl_mov.config(text="Estado Entrada (PIR): Sin movimiento", foreground="green")
                
        elif topico == T_LED_STATE:
            app.lbl_led_st.config(text=f"Luz Sala: {payload}")
        elif topico == T_SERVO_STATE:
            app.lbl_servo_st.config(text=f"Portón Garaje: {payload}°")
        elif topico == T_BUZZER_STATE:
            app.lbl_buz_st.config(text=f"Alarma Alerta: {payload}")
            
    except Exception as e:
        print("Error al procesar mensaje en puerto seguro:", e)

# --- FLUJO PRINCIPAL ---
iniciar_bd()
root = tk.Tk()
app = DashboardApp(root)

# Configuración explícita de WebSockets para el puerto 8884
try:
    client = mqtt.Client(client_id=MQTT_CLIENT_ID, transport="websockets", callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    client = mqtt.Client(client_id=MQTT_CLIENT_ID, transport="websockets")

# Habilitar TLS/SSL para el puerto seguro de HiveMQ
client.tls_set()

client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

root.mainloop()
