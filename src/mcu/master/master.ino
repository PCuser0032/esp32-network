#include <esp_now.h>
#include <WiFi.h>
#include <esp_mac.h>

// MAC-адрес Узла (замените на свой!)
uint8_t nodeMac[] = { 0x20, 0xE7, 0xC8, 0xAD, 0x0C, 0xC8 };

unsigned long lastPoll = 0;
const unsigned long POLL_INTERVAL = 5000;  // Раз в 5 секунд для теста

// Функция расчета CRC-16/CCITT-FALSE
uint16_t calculateCRC16(const uint8_t *data, size_t length) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < length; i++) {
    crc ^= (uint16_t)data[i] << 8;
    for (uint8_t j = 0; j < 8; j++) {
      if (crc & 0x8000) {
        crc = (crc << 1) ^ 0x1021;
      } else {
        crc <<= 1;
      }
    }
  }
  return crc;
}

// Функция сборки UART-кадра и вывода его в порт
void sendUartFrame(String payload) {
  uint8_t len = payload.length();
  uint8_t frame[len + 5];  // Start(1) + Len(1) + Payload(N) + CRC(2) + End(1)

  frame[0] = 0xAA;  // Start
  frame[1] = len;

  for (int i = 0; i < len; i++) {
    frame[2 + i] = payload[i];
  }

  // Считаем CRC от длины и полезной нагрузки
  uint8_t dataToCrc[len + 1];
  dataToCrc[0] = len;
  for (int i = 0; i < len; i++) dataToCrc[1 + i] = payload[i];

  uint16_t crc = calculateCRC16(dataToCrc, len + 1);

  frame[len + 2] = (crc >> 8) & 0xFF;  // CRC High
  frame[len + 3] = crc & 0xFF;         // CRC Low
  frame[len + 4] = 0x55;               // End

  // Вывод в монитор порта в HEX (чтобы мы видели байты, а не кракозябры)
  Serial.print("UART FRAME (HEX): ");
  for (int i = 0; i < len + 5; i++) {
    if (frame[i] < 16) Serial.print("0");
    Serial.print(frame[i], HEX);
    Serial.print(" ");
  }
  Serial.println();
}

void OnDataRecv(const esp_now_recv_info_t *info, const uint8_t *incomingData, int len) {
  String payload = String((char *)incomingData).substring(0, len);
  Serial.println("RX from Node: " + payload);

  // Упаковываем в UART
  sendUartFrame(payload);
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
  memcpy(peerInfo.peer_addr, nodeMac, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

  uint8_t mac[6];
  esp_read_mac(mac, ESP_MAC_WIFI_STA);
  Serial.printf("HUB MAC: %02X:%02X:%02X:%02X:%02X:%02X\n", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

void loop() {
  if (millis() - lastPoll >= POLL_INTERVAL) {
    lastPoll = millis();
    const char *req = "REQ";
    esp_now_send(nodeMac, (uint8_t *)req, strlen(req));
  }
}