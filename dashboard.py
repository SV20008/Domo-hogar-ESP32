import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

# --- CONFIGURACIÓN DE TÓPICOS ---
MQTT_BROKER = "broker.hivemq.com"
PREFIJO = "uesfia-g3"
BASE = PREFIJO + "/casa"

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

# Variables globales de sensores
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
    conn = sqlite3.connect("domotica_ues.db")
    cursor = conn.cursor()
    fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO historico (fecha, temperatura, humedad, luz) VALUES (?, ?, ?, ?)",
                   (fecha_actual, ultima_temp, ultima_hum, ultima_luz))
    conn.commit()
    conn.close()

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UES Grupo 4 - Dashboard DomoHogar")
        self.root.geometry("700x650")
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # Panel Monitoreo
        f_monitoreo = ttk.LabelFrame(root, text=" Telemetría en Tiempo Real ", padding=15)
        f_monitoreo.pack(pady=15, fill="x", padx=20)
        
        self.lbl_temp = ttk.Label(f_monitoreo, text="Temperatura: -- °C", font=("Arial", 13, "bold"))
        self.lbl_temp.pack(anchor="w", pady=2)
        self.lbl_hum = ttk.Label(f_monitoreo, text="Humedad: -- %", font=("Arial", 13, "bold"))
        self.lbl_hum.pack(anchor="w", pady=2)
        self.lbl_luz = ttk.Label(f_monitoreo, text="Nivel de Luz (LDR): --", font=("Arial", 13, "bold"))
        self.lbl_luz.pack(anchor="w", pady=2)
        self.lbl_mov = ttk.Label(f_monitoreo, text="Movimiento: --", font=("Arial", 13, "bold"), foreground="orange")
        self.lbl_mov.pack(anchor="w", pady=2)
        self.lbl_niv = ttk.Label(f_monitoreo, text="Nivel Tanque: -- cm", font=("Arial", 13, "bold"))
        self.lbl_niv.pack(anchor="w", pady=2)
        
        # Panel Control
        f_control = ttk.LabelFrame(root, text=" Panel de Control Remoto ", padding=15)
        f_control.pack(pady=15, fill="x", padx=20)
        
        ttk.Button(f_control, text="Modo: AUTOMÁTICO", command=lambda: self.enviar_cmd(T_MODO, "AUTO")).pack(side="left", padx=5)
        ttk.Button(f_control, text="Modo: MANUAL", command=lambda: self.enviar_cmd(T_MODO, "MANUAL")).pack(side="left", padx=5)
        
        f_botones = ttk.Frame(root, padding=10)
        f_botones.pack(fill="x", padx=20)
        
        ttk.Button(f_botones, text="Encender LED", command=lambda: self.enviar_cmd(T_LED, "ON")).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(f_botones, text="Apagar LED", command=lambda: self.enviar_cmd(T_LED, "OFF")).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(f_botones, text="Abrir Portón", command=lambda: self.enviar_cmd(T_SERVO, "ABRIR")).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(f_botones, text="Cerrar Portón", command=lambda: self.enviar_cmd(T_SERVO, "CERRAR")).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(f_botones, text="Encender Ventilador", command=lambda: self.enviar_cmd(T_FAN, "ON")).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(f_botones, text="Apagar Ventilador", command=lambda: self.enviar_cmd(T_FAN, "OFF")).grid(row=2, column=1, padx=5, pady=5)
        
        f_hist = ttk.LabelFrame(root, text=" Análisis de Datos ", padding=15)
        f_hist.pack(pady=15, fill="x", padx=20)
        ttk.Button(f_hist, text="Ver Histórico de Temperatura", command=self.graficar).pack()

    def enviar_cmd(self, topico, comando):
        # Asegura la publicación inmediata hacia el broker
        client.publish(topico, comando, qos=1)
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
            ax.plot(horas, temps, marker='s', color='crimson', linestyle='--')
            ax.set_title("Historial de Variación Térmica (Sala)")
            ax.set_ylabel("°C")
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            ventana = tk.Toplevel(self.root)
            ventana.title("Gráfica Histórica")
            canvas = FigureCanvasTkAgg(fig, master=ventana)
            canvas.draw()
            canvas.get_tk_widget().pack(padx=10, pady=10)

def on_connect(client, userdata, flags, rc, properties=None):
    print("Conectado con éxito al Broker de HiveMQ")
    # Nos suscribimos usando el comodín multinivel para capturar todo el flujo
    client.subscribe("uesfia-g3/casa/#")

def on_message(client, userdata, msg):
    global ultima_temp, ultima_hum, ultima_luz
    payload = msg.payload.decode().strip()
    topico = msg.topic
    
    if topico == T_TEMP:
        ultima_temp = float(payload)
        app.lbl_temp.config(text=f"Temperatura: {ultima_temp} °C")
    elif topico == T_HUM:
        ultima_hum = float(payload)
        app.lbl_hum.config(text=f"Humedad: {ultima_hum} %")
    elif topico == T_LUZ:
        ultima_luz = float(payload)
        app.lbl_luz.config(text=f"Nivel de Luz (LDR): {ultima_luz}")
        guardar_en_bd()
    elif topico == T_MOV:
        estado_mov = "¡ALERTA - DETECTADO!" if payload == "1" else "Sin novedad (Despejado)"
        app.lbl_mov.config(text=f"Movimiento: {estado_mov}")
    elif topico == T_NIV:
        app.lbl_niv.config(text=f"Nivel Tanque: {payload} cm")

# --- FLUJO PRINCIPAL ---
iniciar_bd()
root = tk.Tk()
app = DashboardApp(root)

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, 1883, 60)
client.loop_start()

root.mainloop()
