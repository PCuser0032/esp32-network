#include <esp_now.h>
#include <WiFi.h>
#include <esp_mac.h>

// MAC-адрес Узла (замените на свой!)
uint8_t nodeMac[] = { 0x20, 0xE7, 0xC8, 0xAD, 0x0C, 0xC8 };

unsigned long lastPoll = 0;
const unsigned long POLL_INTERVAL = 5000;

// Буфер для приема команд из UART
uint8_t rxBuf[260];
int rxIdx = 0;
bool rxFrame = false;

uint16_t calculateCRC16(const uint8_t *data, size_t length) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < length; i++) {
    crc ^= (uint16_t)data[i] << 8;
    for (uint8_t j = 0; j < 8; j++) {
      if (crc & 0x8000) crc = (crc << 1) ^ 0x1021;
      else crc <<= 1;
    }
  }
  return crc;
}

void sendUartFrame(String payload) {
  uint8_t len = payload.length();
  uint8_t frame[len + 5];

  frame[0] = 0xAA;
  frame[1] = len;
  for (int i = 0; i < len; i++) frame[2 + i] = payload[i];

  uint8_t dataToCrc[len + 1];
  dataToCrc[0] = len;
  for (int i = 0; i < len; i++) dataToCrc[1 + i] = payload[i];

  uint16_t crc = calculateCRC16(dataToCrc, len + 1);
  frame[len + 2] = (crc >> 8) & 0xFF;
  frame[len + 3] = crc & 0xFF;
  frame[len + 4] = 0x55;

  Serial.write(frame, len + 5);
}

void OnDataRecv(const esp_now_recv_info_t *info, const uint8_t *incomingData, int len) {
  String payload = String((char *)incomingData).substring(0, len);
  sendUartFrame(payload);
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  esp_now_init();
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
  // 1. Плановый опрос
  if (millis() - lastPoll >= POLL_INTERVAL) {
    lastPoll = millis();
    const char *req = "REQ";
    esp_now_send(nodeMac, (uint8_t *)req, strlen(req));
  }

  // 2. Прием команд из UART и отправка на Узел
  while (Serial.available() > 0) {
    uint8_t b = Serial.read();

    if (b == 0xAA) {
      rxFrame = true;
      rxIdx = 0;
    } else if (rxFrame) {
      rxBuf[rxIdx++] = b;

      // Если мы прочитали хотя бы байт длины
      if (rxIdx >= 1) {
        uint8_t payloadLen = rxBuf[0];

        // Длина кадра = 1(LEN) + payloadLen(PAYLOAD) + 2(CRC) + 1(END)
        if (rxIdx >= payloadLen + 4) {
          if (rxBuf[rxIdx - 1] == 0x55) {  // Проверка стопового байта
            // Извлекаем только полезную нагрузку (строку команды)
            String payloadStr = "";
            for (int i = 0; i < payloadLen; i++) {
              payloadStr += (char)rxBuf[1 + i];  // 1 - потому что rxBuf[0] это длина
            }

            // Отправляем чистую строку по ESP-NOW
            esp_now_send(nodeMac, (uint8_t *)payloadStr.c_str(), payloadStr.length());
          }
          rxFrame = false;  // Сбрасываем флаг приема
        }
      }
    }
  }
}