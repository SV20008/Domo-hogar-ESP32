"""
   Proyecto Domótica - ESP32 + Wi-Fi + MQTT
   Universidad de El Salvador en línea - EISI
   Avance No. 2

   Sensores:
     - DHT22   -> GPIO 15 (temperatura y humedad)
     - PIR     -> GPIO 13 (movimiento)
     - LDR     -> GPIO 34 (luz ambiental, entrada analógica)

   Actuadores:
     - LED     -> GPIO 2  (luz de la casa)
     - Servo   -> GPIO 18 (cochera/ventana)
     - Buzzer  -> GPIO 4  (alarma)
""" 

#include <WiFi.h>
#include <WiFiClientSecure.h> // Se cambia a la versión segura para TLS
#include <PubSubClient.h>
#include <DHT.h>
#include <ESP32Servo.h>

// ---------- CONFIGURACIÓN WI-FI ----------
const char* WIFI_SSID     = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

// ---------- CONFIGURACIÓN MQTT ----------
const char* MQTT_BROKER    = "broker.hivemq.com";
const int   MQTT_PORT      = 8884; // Reestablecido a 8884 por restricción del entorno
const char* MQTT_CLIENT_ID = "esp32-domotica-grupo03"; 

// ---------- TÓPICOS MQTT CONFIGURADOS ----------
const char* TOPIC_TEMP        = "uesfia-g3/casa/sala/dht22/temperatura";
const char* TOPIC_HUM         = "uesfia-g3/casa/sala/dht22/humedad";
const char* TOPIC_PIR         = "uesfia-g3/casa/entrada/pir/movimiento";
const char* TOPIC_LDR         = "uesfia-g3/casa/exterior/ldr/luz";

const char* TOPIC_LED_SET     = "uesfia-g3/casa/sala/led/set";
const char* TOPIC_LED_STATE   = "uesfia-g3/casa/sala/led/state";
const char* TOPIC_SERVO_SET   = "uesfia-g3/casa/garage/servo/set";
const char* TOPIC_SERVO_STATE = "uesfia-g3/casa/garage/servo/state";
const char* TOPIC_BUZZER_SET  = "uesfia-g3/casa/alarma/buzzer/set";
const char* TOPIC_BUZZER_STATE= "uesfia-g3/casa/alarma/buzzer/state";

// ---------- PINES ----------
#define PIN_DHT22  15
#define PIN_PIR    13
#define PIN_LDR    34
#define PIN_LED     2  
#define PIN_SERVO  18
#define PIN_BUZZER  4  

#define DHTTYPE DHT22

DHT dht(PIN_DHT22, DHTTYPE);
Servo servoGaraje;

WiFiClientSecure espClient; // Cliente seguro para manejar puerto 8884
PubSubClient mqttClient(espClient);

bool estadoLed     = false;
int  estadoServo   = 0;     
bool estadoBuzzer  = false;
bool pirAnterior   = false;

unsigned long ultimaLecturaSensores = 0;
const unsigned long INTERVALO_SENSORES = 5000; 

void setupWifi() {
  Serial.print("Conectando a ");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi conectado");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  // IMPORTANTE: Permitir conexión segura sin validar certificado raíz en el simulador
  espClient.setInsecure(); 
}

void publicarEstadoLed() {
  mqttClient.publish(TOPIC_LED_STATE, estadoLed ? "ON" : "OFF", true);
}

void publicarEstadoServo() {
  char buf[8];
  itoa(estadoServo, buf, 10);
  mqttClient.publish(TOPIC_SERVO_STATE, buf, true);
}

void publicarEstadoBuzzer() {
  mqttClient.publish(TOPIC_BUZZER_STATE, estadoBuzzer ? "ON" : "OFF", true);
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String mensaje;
  for (unsigned int i = 0; i < length; i++) {
    mensaje += (char)payload[i];
  }
  mensaje.trim();

  Serial.printf("MQTT IN [%s] %s\n", topic, mensaje.c_str());
  String t = String(topic);

  if (t == TOPIC_LED_SET) {
    estadoLed = (mensaje == "ON" || mensaje == "1");
    digitalWrite(PIN_LED, estadoLed ? HIGH : LOW);
    publicarEstadoLed();
  }
  else if (t == TOPIC_SERVO_SET) {
    if (mensaje == "OPEN")        estadoServo = 90;
    else if (mensaje == "CLOSE")  estadoServo = 0;
    else                          estadoServo = constrain(mensaje.toInt(), 0, 180);
    servoGaraje.write(estadoServo);
    publicarEstadoServo();
  }
  else if (t == TOPIC_BUZZER_SET) {
    estadoBuzzer = (mensaje == "ON" || mensaje == "1");
    digitalWrite(PIN_BUZZER, estadoBuzzer ? HIGH : LOW);
    publicarEstadoBuzzer();
  }
}

void reconnectMqtt() {
  while (!mqttClient.connected()) {
    Serial.print("Conectando a MQTT Seguro (8884)...");
    if (mqttClient.connect(MQTT_CLIENT_ID)) {
      Serial.println("conectado");

      mqttClient.subscribe(TOPIC_LED_SET);
      mqttClient.subscribe(TOPIC_SERVO_SET);
      mqttClient.subscribe(TOPIC_BUZZER_SET);

      publicarEstadoLed();
      publicarEstadoServo();
      publicarEstadoBuzzer();
    } else {
      Serial.printf("fallo, rc=%d. Reintentando en 3s\n", mqttClient.state());
      delay(3000);
    }
  }
}

void leerYPublicarSensores() {
  float temperatura = dht.readTemperature();
  float humedad = dht.readHumidity();

  if (!isnan(temperatura) && !isnan(humedad)) {
    char bufT[8], bufH[8];
    dtostrf(temperatura, 4, 1, bufT);
    dtostrf(humedad, 4, 1, bufH);
    mqttClient.publish(TOPIC_TEMP, bufT);
    mqttClient.publish(TOPIC_HUM, bufH);
    Serial.printf("Temp: %s C  Hum: %s %%\n", bufT, bufH);
  } else {
    Serial.println("Error leyendo DHT22");
  }

  int valorLdr = analogRead(PIN_LDR); 
  char bufLdr[8];
  itoa(valorLdr, bufLdr, 10);
  mqttClient.publish(TOPIC_LDR, bufLdr);
  Serial.printf("LDR: %s\n", bufLdr);
}

void revisarPir() {
  bool pirActual = digitalRead(PIN_PIR) == HIGH;
  if (pirActual != pirAnterior) {
    mqttClient.publish(TOPIC_PIR, pirActual ? "1" : "0");
    Serial.printf("PIR: %s\n", pirActual ? "movimiento detectado" : "sin movimiento");
    pirAnterior = pirActual;
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_PIR, INPUT);

  digitalWrite(PIN_LED, LOW);
  digitalWrite(PIN_BUZZER, LOW);

  dht.begin();

  servoGaraje.setPeriodHertz(50);
  servoGaraje.attach(PIN_SERVO, 500, 2400);
  servoGaraje.write(estadoServo);

  setupWifi();
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
}

void loop() {
  if (!mqttClient.connected()) {
    reconnectMqtt();
  }
  mqttClient.loop();

  revisarPir();

  unsigned long ahora = millis();
  if (ahora - ultimaLecturaSensores >= INTERVALO_SENSORES) {
    ultimaLecturaSensores = ahora;
    leerYPublicarSensores();
  }
}
