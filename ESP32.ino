#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <PID_v1.h>

#define PIN_PWM 18
#define PIN_V_IN 32
#define PIN_I_IN 33
#define PIN_I_OUT 34
#define PIN_V_OUT 35

String admin_password = "admin";
String sta_ssid = "";
String sta_pass = "";
String mqtt_broker = "";
int mqtt_port = 1883;
String mqtt_topic = "factory/buck1/data";

bool in_ap_mode = true;
unsigned long last_wifi_check = 0;
unsigned long last_telemetry_pub = 0;
unsigned long last_pid_compute = 0;
const unsigned long WIFI_TIMEOUT_MS = 20000;

bool system_is_on = false;
float vin = 0.0, vout = 0.0, iin = 0.0, iout = 0.0;
float p_in = 0.0, p_out = 0.0, efficiency = 0.0, hw_temp = 25.0;
float target_v = 12.0;
float current_target = 0.0;

double Setpoint, Input, Output;
double Kp = 3.57, Ki = 143.0, Kd = 0.0;
PID myPID(&Input, &Output, &Setpoint, Kp, Ki, Kd, DIRECT);

WebServer server(80);
WiFiClient espClient;
PubSubClient mqttClient(espClient);

void startAPMode() {
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char ap_ssid[20];
  sprintf(ap_ssid, "BUCK_CV_%02X%02X", mac[4], mac[5]);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid, "00000000");
  in_ap_mode = true;
}

void connectToSTA() {
  if (sta_ssid == "") return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(sta_ssid.c_str(), sta_pass.c_str());
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    in_ap_mode = false;
  } else {
    startAPMode();
  }
}

void handleTelemetry() {
  StaticJsonDocument<256> doc;
  doc["vin"] = vin;
  doc["vout"] = vout;
  doc["iin"] = iin;
  doc["iout"] = iout;
  doc["pin"] = p_in;
  doc["pout"] = p_out;
  doc["eff"] = efficiency;
  doc["temp"] = hw_temp;
  doc["state"] = system_is_on ? "ON" : "OFF";
  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void handleControl() {
  if (!server.hasArg("plain")) {
    server.send(400, "text/plain", "");
    return;
  }
  StaticJsonDocument<256> doc;
  deserializeJson(doc, server.arg("plain"));
  String pwd = doc["password"];
  if (pwd != admin_password) {
    server.send(401, "application/json", "{\"status\":\"error\"}");
    return;
  }
  String cmd = doc["command"];
  if (cmd == "ON") {
    system_is_on = true;
  } else if (cmd == "OFF") {
    system_is_on = false;
    current_target = 0.0;
    Setpoint = 0.0;
    ledcWrite(0, 0);
  }
  server.send(200, "application/json", "{\"status\":\"success\"}");
}

void handleParams() {
  if (!server.hasArg("plain")) {
    server.send(400, "text/plain", "");
    return;
  }
  StaticJsonDocument<256> doc;
  deserializeJson(doc, server.arg("plain"));
  String pwd = doc["password"];
  if (pwd != admin_password) {
    server.send(401, "application/json", "{\"status\":\"error\"}");
    return;
  }
  if (doc.containsKey("target_v")) target_v = doc["target_v"];
  if (doc.containsKey("kp")) Kp = doc["kp"];
  if (doc.containsKey("ki")) Ki = doc["ki"];
  if (doc.containsKey("kd")) Kd = doc["kd"];
  myPID.SetTunings(Kp, Ki, Kd);
  server.send(200, "application/json", "{\"status\":\"success\"}");
}

void handleNetworkConfig() {
  if (!server.hasArg("plain")) {
    server.send(400, "text/plain", "");
    return;
  }
  StaticJsonDocument<256> doc;
  deserializeJson(doc, server.arg("plain"));
  String pwd = doc["password"];
  if (pwd != admin_password) {
    server.send(401, "application/json", "{\"status\":\"error\"}");
    return;
  }
  sta_ssid = doc["ssid"].as<String>();
  sta_pass = doc["pass"].as<String>();
  mqtt_broker = doc["mqtt_broker"].as<String>();
  mqtt_port = doc["mqtt_port"];
  mqtt_topic = doc["mqtt_topic"].as<String>();
  server.send(200, "application/json", "{\"status\":\"success\"}");
  delay(500);
  connectToSTA();
}

void setup() {
  ledcSetup(0, 10000, 10);
  ledcAttachPin(PIN_PWM, 0);
  ledcWrite(0, 0);

  myPID.SetMode(AUTOMATIC);
  myPID.SetSampleTime(10);
  myPID.SetOutputLimits(0, 1023);

  startAPMode();

  server.on("/api/telemetry", HTTP_GET, handleTelemetry);
  server.on("/api/control", HTTP_POST, handleControl);
  server.on("/api/params", HTTP_POST, handleParams);
  server.on("/api/network", HTTP_POST, handleNetworkConfig);
  server.begin();
}

void loop() {
  server.handleClient();
  unsigned long currentMillis = millis();

  if (currentMillis - last_pid_compute >= 10) {
    last_pid_compute = currentMillis;

    vin = analogRead(PIN_V_IN) * 0.00814652;
    vout = analogRead(PIN_V_OUT) * 0.00814652;
    iin = analogRead(PIN_I_IN) * 0.007326;
    iout = analogRead(PIN_I_OUT) * 0.007326;

    p_in = vin * iin;
    p_out = vout * iout;
    if (p_in > 0.1) efficiency = (p_out / p_in) * 100.0;
    else efficiency = 0.0;

    Input = vout;

    if (system_is_on) {
      if (current_target < target_v) current_target += 0.02;
      else if (current_target > target_v) current_target -= 0.02;
      Setpoint = current_target;
      myPID.Compute();
      ledcWrite(0, (int)Output);
    } else {
      current_target = 0.0;
      Setpoint = 0.0;
      ledcWrite(0, 0);
    }
  }

  if (currentMillis - last_telemetry_pub >= 1000) {
    last_telemetry_pub = currentMillis;
    hw_temp = temperatureRead();
    if (hw_temp == -127.0) hw_temp = 25.0;

    if (!in_ap_mode && mqttClient.connected()) {
      StaticJsonDocument<256> doc;
      doc["vin"] = vin;
      doc["vout"] = vout;
      doc["iin"] = iin;
      doc["iout"] = iout;
      doc["temp"] = hw_temp;
      doc["eff"] = efficiency;
      doc["state"] = system_is_on ? "ON" : "OFF";
      char buffer[256];
      serializeJson(doc, buffer);
      mqttClient.publish(mqtt_topic.c_str(), buffer);
    }
  }

  if (!in_ap_mode && (currentMillis - last_wifi_check >= WIFI_TIMEOUT_MS)) {
    last_wifi_check = currentMillis;
    if (WiFi.status() != WL_CONNECTED) {
      startAPMode();
    }
  }

  if (!in_ap_mode && WiFi.status() == WL_CONNECTED) {
    if (mqtt_broker != "" && !mqttClient.connected()) {
      mqttClient.setServer(mqtt_broker.c_str(), mqtt_port);
      String clientId = "ESP32-BuckConverter-" + String(random(0xffff), HEX);
      mqttClient.connect(clientId.c_str());
    }
    mqttClient.loop();
  }
}
