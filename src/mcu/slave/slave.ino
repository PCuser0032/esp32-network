#include <esp_now.h>
#include <WiFi.h>
#include <esp_mac.h>

#define LED_PIN 2  // Указываем, что светодиод на GPIO 2

// MAC-адрес Хаба (замените на свой!)
uint8_t hubMac[] = { 0x14, 0x33, 0x5C, 0x2F, 0xB8, 0xB8 };

const char* DEVICE_ID = "01";
const char* TOPIC = "sensors";
const char* SCHEMA = "v1";

// Переменные для неблокирующего мигания светодиодом
bool isLedActive = false;
unsigned long ledStartTime = 0;
unsigned long ledDuration = 0;

void OnDataRecv(const esp_now_recv_info_t* info, const uint8_t* incomingData, int len) {
  String msg = String((char*)incomingData).substring(0, len);

  // 1. Обработка планового запроса телеметрии
  if (msg == "REQ") {
    float mockTemp = random(200, 300) / 10.0;
    float mockHum = random(400, 700) / 10.0;
    unsigned long timestamp = millis() / 1000;

    String payload = "TLM " + String(DEVICE_ID) + " " + String(TOPIC) + " " + String(timestamp) + " " + String(SCHEMA) + " " + String(mockTemp, 1) + " " + String(mockHum, 1);

    esp_now_send(hubMac, (uint8_t*)payload.c_str(), payload.length());
    Serial.println("TX: " + payload);
  }

  // 2. Обработка внеплановой команды (CMD)
  else if (msg.startsWith("CMD")) {
    Serial.println("RX CMD: " + msg);

    int space1 = msg.indexOf(' ');
    int space2 = msg.indexOf(' ', space1 + 1);
    int space3 = msg.indexOf(' ', space2 + 1);
    int space4 = msg.indexOf(' ', space3 + 1);

    if (space4 > 0) {
      String cmdId = msg.substring(space2 + 1, space3);
      String cmdType = msg.substring(space3 + 1, space4);
      String arg = msg.substring(space4 + 1);

      if (cmdType == "led") {
        // НЕБЛОКИРУЮЩИЙ ЗАПУСК
        ledDuration = arg.toInt();
        ledStartTime = millis();
        isLedActive = true;
        digitalWrite(LED_PIN, HIGH);  // Включаем сразу

        Serial.println("Action: LED ON for " + String(ledDuration) + " ms");

        // Отправляем ACK СРАЗУ, как только приняли команду к исполнению
        String ack = "ACK " + String(DEVICE_ID) + " " + cmdId + " OK";
        esp_now_send(hubMac, (uint8_t*)ack.c_str(), ack.length());
        Serial.println("TX: " + ack);
      }
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);  // Изначально выключен

  WiFi.mode(WIFI_STA);
  esp_now_init();
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
  // Неблокирующая проверка: не пора ли выключить светодиод?
  if (isLedActive && (millis() - ledStartTime >= ledDuration)) {
    digitalWrite(LED_PIN, LOW);
    isLedActive = false;
    Serial.println("Action: LED OFF");
  }

  delay(10);
}