import serial
import struct
from datetime import datetime

# НАСТРОЙКИ (замените COM-порт на тот, куда подключен Хаб!)
SERIAL_PORT = "COM4"
BAUD_RATE = 115200


def calculate_crc16(data):
    """Расчет CRC-16/CCITT-FALSE (идентично прошивке ESP32)"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Открываю порт {SERIAL_PORT}...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    except Exception as e:
        print(f"Ошибка открытия порта: {e}")
        return

    buffer = bytearray()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Ожидание данных... (Ctrl+C для выхода)\n")

    try:
        while True:
            # Читаем все доступные байты
            if ser.in_waiting > 0:
                buffer.extend(ser.read(ser.in_waiting))

            # Ищем стартовый байт 0xAA
            start_idx = buffer.find(b'\xAA')

            if start_idx != -1:
                # Если нашли 0xAA, но перед ним был мусор - удаляем его
                if start_idx > 0:
                    buffer = buffer[start_idx:]

                # Проверяем, хватает ли данных для чтения длины
                if len(buffer) >= 2:
                    length = buffer[1]
                    # AA(1) + LEN(1) + Payload(N) + CRC(2) + 55(1)
                    frame_size = length + 5

                    # Если в буфере накопился полный кадр
                    if len(buffer) >= frame_size:
                        frame = buffer[:frame_size]

                        # Проверяем стоповый байт
                        if frame[-1] != 0x55:
                            buffer = buffer[1:]  # Сдвигаем и ищем дальше
                            continue

                        # Извлекаем данные
                        payload_bytes = frame[2:-3]
                        received_crc = struct.unpack('>H', frame[-3:-1])[0]

                        # Считаем CRC от длины и payload'а
                        data_to_crc = bytes([length]) + payload_bytes
                        calculated_crc = calculate_crc16(data_to_crc)

                        if received_crc == calculated_crc:
                            payload_str = payload_bytes.decode(
                                'ascii', errors='ignore')
                            print(
                                f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [+] CRC OK | {payload_str}")
                        else:
                            print(
                                f"[{datetime.now().strftime('%H:%M:%S')}] [-] Ошибка CRC! Ожидалось {calculated_crc:04X}, получено {received_crc:04X}")

                        # Удаляем обработанный кадр из буфера
                        buffer = buffer[frame_size:]
                else:
                    pass  # Ждем длину
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
        ser.close()


if __name__ == "__main__":
    main()
