#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

#define SENSOR_PIN   13
#define LED_INTERNO   2

const char* ssid      = "HONOR X7";
const char* password  = "0123456789";
const char* serverUrl = "http://18.222.199.177:5000/sensor";
const char* controlUrl = "http://18.222.199.177:5000/estado_control";

// Cada cuántos ciclos se consulta el estado de control (1 ciclo = 500 ms)
// 10 ciclos = cada 5 segundos
const int CONTROL_CADA_N_CICLOS = 10;

bool sensorActivo = true;  // Estado local; se sincroniza con el servidor
int  cicloActual  = 0;

// ── Consulta al servidor si el sensor debe estar activo ──────────────────────
void sincronizarControl() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(controlUrl);
  int code = http.GET();

  if (code == 200) {
    String payload = http.getString();
    // Respuesta esperada: {"sensor_activo": true} o {"sensor_activo": false}
    StaticJsonDocument<64> doc;
    if (deserializeJson(doc, payload) == DeserializationError::Ok) {
      sensorActivo = doc["sensor_activo"].as<bool>();
    }
  }
  http.end();
}

// ── Parpadeo rápido para indicar que el sensor está APAGADO ─────────────────
void parpadeoBloqueado() {
  // 3 destellos rápidos del LED y apagado
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_INTERNO, HIGH);
    delay(80);
    digitalWrite(LED_INTERNO, LOW);
    delay(80);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(SENSOR_PIN, INPUT_PULLDOWN);
  pinMode(LED_INTERNO, OUTPUT);
  digitalWrite(LED_INTERNO, LOW);

  WiFi.begin(ssid, password);
  Serial.print("Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConectado! IP: " + WiFi.localIP().toString());

  // Sincronizar estado inicial desde el servidor
  sincronizarControl();
  Serial.println("Estado inicial del sensor: " + String(sensorActivo ? "ACTIVO" : "APAGADO"));

  Serial.println("Esperando calibracion del sensor (10 segundos)...");
  delay(10000);
  Serial.println("Listo!");
}

void loop() {
  // ── 1. Sincronizar estado de control cada N ciclos ─────────────────────────
  cicloActual++;
  if (cicloActual >= CONTROL_CADA_N_CICLOS) {
    cicloActual = 0;
    sincronizarControl();
    Serial.println("[Control] sensor_activo = " + String(sensorActivo ? "true" : "false"));
  }

  // ── 2. Si el sensor está apagado: LED apagado, sin lecturas, sin envíos ────
  if (!sensorActivo) {
    digitalWrite(LED_INTERNO, LOW);   // Apagar LED completamente
    Serial.println("Sensor APAGADO — esperando...");
    delay(500);
    return;  // <-- sale del loop sin leer ni enviar nada
  }

  // ── 3. Sensor activo: leer y enviar normalmente ───────────────────────────
  int estado = digitalRead(SENSOR_PIN);
  digitalWrite(LED_INTERNO, estado == HIGH ? HIGH : LOW);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/x-www-form-urlencoded");
    String body = "movimiento=" + String(estado);
    http.POST(body);
    http.end();
  }

  Serial.print("Pin GPIO13: ");
  Serial.print(estado);
  Serial.println(estado == HIGH ? " --> MOVIMIENTO detectado" : " --> Sin movimiento");

  delay(500);
}