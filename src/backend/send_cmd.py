import socket
import sys

TCP_PORT = 65432


def main():
    if len(sys.argv) < 2:
        print("Использование: python send_cmd.py \"CMD 01 101 led 2000\"")
        return

    cmd = " ".join(sys.argv[1:])

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', TCP_PORT))
        client.sendall(cmd.encode('ascii'))
        print(f"[*] Команда отправлена бэкенду: {cmd}")
    except ConnectionRefusedError:
        print("[-] Ошибка: Бэкенд (parser.py) не запущен или не слушает порт.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
