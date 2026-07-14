#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiManager.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>
#include <Preferences.h>

#if __has_include("config.h")
#include "config.h"
#else
#define API_BASE_URL "http://192.168.1.100:8000"
#define DEVICE_ID_PREFIX "valphone-"
#define POLL_INTERVAL_MS 180000
#define OLED_SDA 8
#define OLED_SCL 9
#endif

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
Preferences prefs;

String deviceId;
String deviceSecret;
String pairingCode;
unsigned long lastPollMs = 0;

void showMessage(const String &line1, const String &line2 = "", const String &line3 = "") {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println(line1);
  if (line2.length()) display.println(line2);
  if (line3.length()) display.println(line3);
  display.display();
}

String buildDeviceId() {
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char buf[32];
  snprintf(buf, sizeof(buf), "%s%02X%02X%02X", DEVICE_ID_PREFIX, mac[3], mac[4], mac[5]);
  return String(buf);
}

bool registerDevice() {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  String url = String(API_BASE_URL) + "/api/devices/register";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<128> body;
  body["device_id"] = deviceId;
  body["firmware_version"] = "1.0.0";

  String payload;
  serializeJson(body, payload);

  int code = http.POST(payload);
  if (code != 200) {
    http.end();
    return false;
  }

  String response = http.getString();
  http.end();

  StaticJsonDocument<512> doc;
  if (deserializeJson(doc, response)) return false;

  deviceSecret = doc["device_secret"].as<String>();
  pairingCode = doc["pairing_code"].as<String>();

  prefs.begin("valphone", false);
  prefs.putString("secret", deviceSecret);
  prefs.putString("pairing", pairingCode);
  prefs.end();

  return true;
}

bool fetchStats(String &kda, String &riotId, bool &linked, String &message) {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  String url = String(API_BASE_URL) + "/api/devices/" + deviceId + "/stats";
  http.begin(url);
  http.addHeader("X-Device-Secret", deviceSecret);

  int code = http.GET();
  if (code != 200) {
    http.end();
    return false;
  }

  String response = http.getString();
  http.end();

  StaticJsonDocument<768> doc;
  if (deserializeJson(doc, response)) return false;

  linked = doc["linked"] | false;
  message = doc["message"].as<String>();
  riotId = doc["riot_id"].as<String>();

  JsonObject last = doc["last_match"];
  if (!last.isNull()) {
    kda = last["kda_display"].as<String>();
    return true;
  }

  return linked;
}

void setupWiFi() {
  showMessage("WiFi setup", "Red: ValorantPhone");
  WiFiManager wm;
  wm.setConfigPortalTimeout(180);
  bool ok = wm.autoConnect("ValorantPhone-Setup");
  if (!ok) {
    showMessage("WiFi fallo", "Reiniciando...");
    delay(2000);
    ESP.restart();
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);

  Wire.begin(OLED_SDA, OLED_SCL);
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED no encontrado");
    while (true) delay(1000);
  }

  showMessage("Valorant Phone", "Iniciando...");

  prefs.begin("valphone", true);
  deviceSecret = prefs.getString("secret", "");
  pairingCode = prefs.getString("pairing", "");
  prefs.end();

  deviceId = buildDeviceId();
  setupWiFi();

  showMessage("WiFi OK", deviceId);

  if (deviceSecret.isEmpty()) {
    if (!registerDevice()) {
      showMessage("Error registro", "Revisa API");
      while (true) delay(5000);
    }
  }

  showMessage("Codigo:", pairingCode, "tracker.gg/setup");
}

void loop() {
  if (millis() - lastPollMs < POLL_INTERVAL_MS) {
    delay(200);
    return;
  }
  lastPollMs = millis();

  String kda, riotId, message;
  bool linked = false;

  if (!fetchStats(kda, riotId, linked, message)) {
    showMessage("Sin conexion", "al servidor");
    return;
  }

  if (!linked) {
    showMessage("Vincula cuenta", "Codigo:", pairingCode);
    return;
  }

  if (kda.isEmpty()) {
    showMessage(riotId, message.length() ? message : "Sin partidas");
    return;
  }

  showMessage("Ultima partida", riotId, "KDA " + kda);
}
