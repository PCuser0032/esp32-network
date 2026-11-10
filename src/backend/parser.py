from db.repository import get_repository
import serial
import struct
import sys
import os
import threading
import socket
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

SERIAL_PORT = "COM4"
BAUD_RATE = 115200
TCP_PORT = 65432


def calculate_crc16(data):
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


def send_command(ser, command_str):
    """Формирует UART-фрейм и отправляет его в порт"""
    payload_bytes = command_str.encode('ascii')
    length = len(payload_bytes)
    data_to_crc = bytes([length]) + payload_bytes
    crc = calculate_crc16(data_to_crc)

    frame = bytearray([0xAA, length])
    frame.extend(payload_bytes)
    frame.append((crc >> 8) & 0xFF)
    frame.append(crc & 0xFF)
    frame.append(0x55)

    ser.write(frame)
    print(f"\n[>>>] Отправлено в порт: {command_str}")


def tcp_server_thread(ser):
    """Фоновый сервер для приема команд от других программ (или скриптов)"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', TCP_PORT))
    server.listen(1)
    print(f"[TCP] Сервер команд запущен на 127.0.0.1:{TCP_PORT}")

    while True:
        conn, addr = server.accept()
        data = conn.recv(1024)
        if data:
            cmd = data.decode('ascii').strip()
            send_command(ser, cmd)
        conn.close()


def main():
    repo = get_repository(db_type="sqlite", db_path="iot.db")
    repo.init_db()

    print(f"Открываю порт {SERIAL_PORT}...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    except Exception as e:
        print(f"Ошибка открытия порта: {e}")
        return

    # Запускаем TCP-сервер в фоне
    t = threading.Thread(target=tcp_server_thread, args=(ser,), daemon=True)
    t.start()

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

                            if payload_str.startswith("ACK"):
                                print(f"[<<<] Получен ACK: {payload_str}")
                            elif payload_str.startswith("TLM"):
                                parts = payload_str.split()
                                if len(parts) >= 7:
                                    dev_id = parts[1]
                                    try:
                                        payload_dict = {
                                            "temperature": float(parts[5]),
                                            "humidity": float(parts[6])
                                        }
                                        repo.save_telemetry(
                                            dev_id, payload_dict)
                                        print(
                                            f"[{datetime.now().strftime('%H:%M:%S')}] [+] DB Save OK | {dev_id} | {payload_dict}")
                                    except ValueError as e:
                                        print(f"[-] Ошибка парсинга: {e}")
                        else:
                            print(f"[-] Ошибка CRC!")

                        buffer = buffer[frame_size:]
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
        ser.close()


if __name__ == "__main__":
    main()
