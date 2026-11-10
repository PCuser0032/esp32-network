#include <esp_now.h>
#include <WiFi.h>
#include <esp_mac.h>

// MAC-адрес Хаба (замените на свой!)
uint8_t hubMac[] = {0x14, 0x33, 0x5C, 0x2F, 0xB8, 0xB8};

const char* DEVICE_ID = "01";
const char* TOPIC = "sensors";
const char* SCHEMA = "v1";

void OnDataRecv(const esp_now_recv_info_t* info, const uint8_t* incomingData, int len) {
  String req = String((char*)incomingData).substring(0, len);

  if (req == "REQ") {
    // ЗАГЛУШКА: Генерируем случайные данные (температура 20-30, влажность 40-70)
    float mockTemp = random(200, 300) / 10.0;
    float mockHum = random(400, 700) / 10.0;

    // Формируем Unix Timestamp (для MVP используем millis()/1000)
    unsigned long timestamp = millis() / 1000;

    // Собираем строку по протоколу v1.1
    String payload = "TLM " + String(DEVICE_ID) + " " + String(TOPIC) + " " + String(timestamp) + " " + String(SCHEMA) + " " + String(mockTemp, 1) + " " + String(mockHum, 1);

    esp_now_send(hubMac, (uint8_t*)payload.c_str(), payload.length());
    Serial.println("TX: " + payload);
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;  // Останавливаем выполнение, если ESP-NOW не поднялся
  }

  esp_now_register_recv_cb(OnDataRecv);

  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, hubMac, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

  uint8_t mac[6];
  esp_read_mac(mac, ESP_MAC_WIFI_STA);
  Serial.printf("NODE MAC: %02X:%02X:%02X:%02X:%02X:%02X\n", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

void loop() {
  delay(100);
}