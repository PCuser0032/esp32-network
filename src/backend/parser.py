from db.repository import get_repository
import serial
import struct
import sys
import os
from datetime import datetime

# Импортируем наш репозиторий (убедитесь, что структура папок правильная)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# НАСТРОЙКИ (замените COM-порт на ваш!)
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
    # 1. Инициализация базы данных
    repo = get_repository(db_type="sqlite", db_path="iot.db")
    repo.init_db()

    print(f"Открываю порт {SERIAL_PORT}...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    except Exception as e:
        print(f"Ошибка открытия порта: {e}")
        return

    buffer = bytearray()
    print("Ожидание данных... (Ctrl+C для выхода)\n")

    try:
        while True:
            if ser.in_waiting > 0:
                buffer.extend(ser.read(ser.in_waiting))

            start_idx = buffer.find(b'\xAA')

            if start_idx != -1:
                if start_idx > 0:
                    buffer = buffer[start_idx:]

                if len(buffer) >= 2:
                    length = buffer[1]
                    frame_size = length + 5

                    if len(buffer) >= frame_size:
                        frame = buffer[:frame_size]

                        if frame[-1] != 0x55:
                            buffer = buffer[1:]
                            continue

                        payload_bytes = frame[2:-3]
                        received_crc = struct.unpack('>H', frame[-3:-1])[0]

                        data_to_crc = bytes([length]) + payload_bytes
                        calculated_crc = calculate_crc16(data_to_crc)

                        if received_crc == calculated_crc:
                            payload_str = payload_bytes.decode(
                                'ascii', errors='ignore')
                            parts = payload_str.split()

                            # Ожидаем: TLM <DEV_ID> <TOPIC> <TIME> <SCHEMA> <VAL_1> <VAL_2>
                            if len(parts) >= 7 and parts[0] == "TLM":
                                dev_id = parts[1]
                                # Для MVP жестко задаем схему sensors v1
                                try:
                                    payload_dict = {
                                        "temperature": float(parts[5]),
                                        "humidity": float(parts[6])
                                    }

                                    # Сохраняем в БД через репозиторий
                                    repo.save_telemetry(dev_id, payload_dict)

                                    print(
                                        f"[{datetime.now().strftime('%H:%M:%S')}] [+] DB Save OK | {dev_id} | {payload_dict}")
                                except ValueError as e:
                                    print(
                                        f"[-] Ошибка парсинга значений: {e} | {payload_str}")
                            else:
                                print(
                                    f"[-] Неизвестный формат строки: {payload_str}")
                        else:
                            print(
                                f"[-] Ошибка CRC! Ожидалось {calculated_crc:04X}, получено {received_crc:04X}")

                        buffer = buffer[frame_size:]
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
        ser.close()


if __name__ == "__main__":
    main()
