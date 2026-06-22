#  Sistema de Domótica Residencial (DomoHogar ESP32)
### Universidad de El Salvador - Facultad de Ingeniería y Arquitectura
[cite_start]**Materia:** EBB115 - Avance de Proyecto No. 2 [cite: 10, 14]

[cite_start]Este proyecto implementa un ecosistema IoT completo para el monitoreo y control automatizado/manual de una residencia, empleando un **ESP32** virtualizado, comunicación **MQTT (Broker HiveMQ)**, almacenamiento persistente en una **Base de Datos SQLite** y un **Dashboard interactivo en Python (Tkinter)** con generación de gráficos históricos[cite: 15, 21, 24].

---

## Arquitectura del Sistema

[cite_start]El flujo de comunicación opera bajo el modelo Publicador/Suscriptor a través de Wi-Fi usando el IoT Gateway de Wokwi[cite: 22, 24, 65]:
1. [cite_start]**Sensores (ESP32 $\rightarrow$ MQTT):** El hardware lee las variables del entorno y las publica en tópicos específicos[cite: 24, 36].
2. [cite_start]**Dashboard Local (MQTT $\rightarrow$ SQLite & UI):** El script de Python recibe las lecturas, las guarda automáticamente en la base de datos local y actualiza los indicadores en tiempo real[cite: 24, 44, 45].
3. [cite_start]**Control Remoto (UI $\rightarrow$ MQTT $\rightarrow$ ESP32):** Al presionar un botón del Dashboard en modo manual, se envía un comando al ESP32 para accionar los periféricos físicos.

---

##  Recursos del Circuito (Hardware en Wokwi)
[cite_start]De acuerdo con los requerimientos técnicos fijados, el sistema integra la siguiente distribución de pines[cite: 39, 61]:

### [cite_start]Sensores (Entradas) [cite: 39, 61]
* [cite_start]**DHT22 (Temperatura y Humedad):** Conectado al **GPIO 15** 
* [cite_start]**PIR (Sensor de Movimiento):** Conectado al **GPIO 13** 
* [cite_start]**LDR (Fotorresistencia de Luz):** Conectado al **GPIO 34** (ADC) 
* [cite_start]**HC-SR04 (Ultrasonido/Nivel del Tanque):** **Trig** en **GPIO 5** / **Echo** en **GPIO 19** 

### [cite_start]Actuadores (Salidas) [cite: 39, 61]
* [cite_start]**LED de Diagnóstico/Iluminación:** Conectado al **GPIO 2** 
* [cite_start]**Ventilador (Motor DC):** Conectado al **GPIO 23** 
* [cite_start]**Servomotor (Portón de Acceso):** Conectado al **GPIO 18** (PWM) 
* [cite_start]**Buzzer (Alarma Sonora):** Conectado al **GPIO 4** 

🔗 **Enlace del circuito simulado:** [Simulación en Wokwi](https://wokwi.com/projects/466771905527914497)

---

##  Requisitos previos e Instalación Local

Para ejecutar el Dashboard y almacenar las lecturas, necesitas tener **Python 3.12** instalado en tu computadora.

1. Abre tu terminal o **Símbolo del Sistema (CMD)**.
2. Instala las librerías necesarias ejecutando el siguiente comando:
   ```bash
   pip install paho-mqtt matplotlib
   ```

3. El dashboard Python se conecta al broker HiveMQ usando WebSockets seguros. En HiveMQ Websocket Demo usa:
   * Anfitrión: `broker.hivemq.com`
   * Puerto: `8884`
   * Ruta WebSocket: `/mqtt`
   * Conexión segura/TLS: activada
   * Client ID: `dashboard-domotica-py`
   * Suscribirse a: `casa/#`

4. El ESP32 virtualizado se conecta al mismo broker con MQTT normal sobre TCP:
   * Broker: `broker.hivemq.com`
   * Puerto: `1883`
   * Usa el mismo conjunto de tópicos `casa/...` definidos en el sketch y en el dashboard.

5. Para depurar, el dashboard también suscribe `#` y muestra todos los mensajes MQTT recibidos.

##  Comandos para ejecutar el servidor / dashboard

1. Abre tu terminal en la carpeta del proyecto:
   ```bash
   cd C:/Users/Josue/Desktop/ProyectoDomotica
   ```

2. Activa el entorno virtual si lo tienes:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   O en CMD:
   ```cmd
   .\.venv\Scripts\activate.bat
   ```

3. Si no tienes el entorno virtual, crea uno:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Instala las dependencias:
   ```bash
   pip install paho-mqtt matplotlib
   ```

5. Ejecuta el dashboard Python:
   ```bash
   python dashboard.py
   ```

6. Para detenerlo, cierra la ventana del dashboard o presiona `Ctrl+C` en la terminal.

##  Comandos para el broker HiveMQ WebSocket Demo

En la demo de HiveMQ usa los siguientes valores:
* Anfitrión: `broker.hivemq.com`
* Puerto: `8884`
* TLS/SSL: activado
* Client ID: `dashboard-domotica-py`
* Topic subscribe: `casa/#`
