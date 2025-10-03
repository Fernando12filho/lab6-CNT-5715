import socket
import threading
import os

HOST = '127.0.0.1'  # Server IP
PORT = 2121         # FTP control port
control_socket = None  # Global control socket for use by the console thread
authenticated = False


def ftp_command(command):
    control_socket.send(f"{command}\r\n".encode('utf-8'))
    response = control_socket.recv(1024).decode('utf-8').strip()
    print(f"Server response: {response}")
    return response


def parse_pasv_response(response):
    start = response.find('(') + 1
    end = response.find(')')
    numbers = response[start:end].split(',')
    ip_address = '.'.join(numbers[:4])
    port = int(numbers[4]) * 256 + int(numbers[5])
    return ip_address, port


def data_connection_pasv():
    response = ftp_command("PASV")
    ip, port = parse_pasv_response(response)
    data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data_socket.connect((ip, port))
    return data_socket


def ftp_retrieve(filename):
    response = ftp_command(f"RETR {filename}")
    if response.startswith('150'):
        data_conn = data_connection_pasv()
        total_bytes = 0
        with open(filename, 'wb') as f:
            while True:
                data = data_conn.recv(1024)
                if not data:
                    break
                f.write(data)
                total_bytes += len(data)
        data_conn.close()
        print(f"Downloaded {filename} with {total_bytes} bytes.")
        response = control_socket.recv(1024).decode('utf-8').strip()
        print(f"Server response: {response}")


def ftp_store(filename):
    response = ftp_command(f"STOR {filename}")
    if response.startswith('150'):
        data_conn = data_connection_pasv()
        total_bytes = 0
        with open(filename, 'rb') as f:
            while True:
                data = f.read(1024)
                if not data:
                    break
                data_conn.sendall(data)
                total_bytes += len(data)
        data_conn.close()
        print(f"Uploaded {filename} with {total_bytes} bytes.")
        response = control_socket.recv(1024).decode('utf-8').strip()
        print(f"Server response: {response}")


def ftp_list():
    response = ftp_command("LIST")
    if response.startswith('150'):
        data_conn = data_connection_pasv()
        total_bytes = 0
        print("Directory listing:")
        while True:
            data = data_conn.recv(1024)
            if not data:
                break
            total_bytes += len(data)
            print(data.decode('utf-8'), end='')
        data_conn.close()
        response = control_socket.recv(1024).decode('utf-8').strip()
        print(f"\nServer response: {response}")


def ftp_quit():
    ftp_command("QUIT")
    control_socket.close()


def console_thread():
    global authenticated
    while True:
        command = input("ftp> ").strip()

        if not authenticated:
            if command.startswith('USER'):
                response = ftp_command(command)
                if response.startswith("331"):
                    pass  # waiting for password
            elif command.startswith('PASS'):
                response = ftp_command(command)
                if response.startswith("230"):
                    authenticated = True
            elif command == 'HELP':
                print("Invalid command before authenticated. Available commands: USER <username>, PASS <password>")
            elif command == 'QUIT':
                ftp_quit()
                print("Connection closed. Exiting.")
                break
            else:
                print("You must login first. Try USER <username> and PASS <password>.")
        else:
            if command.startswith('LIST'):
                ftp_list()
            elif command.startswith('RETR'):
                parts = command.split()
                if len(parts) < 2:
                    print("Usage: RETR <filename>")
                else:
                    ftp_retrieve(parts[1])
            elif command.startswith('STOR'):
                parts = command.split()
                if len(parts) < 2:
                    print("Usage: STOR <filename>")
                else:
                    if not os.path.exists(parts[1]):
                        print("File does not exist locally.")
                    else:
                        ftp_store(parts[1])
            elif command == 'QUIT':
                ftp_quit()
                print("Connection closed. Exiting.")
                break
            elif command == 'HELP':
                print("Invalid command after authenticated. Available commands: LIST, RETR <filename>, STOR <filename>, QUIT")
            else:
                print("Invalid command. Type HELP for available commands.")


def main():
    global control_socket

    control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    control_socket.connect((HOST, PORT))
    response = control_socket.recv(1024).decode('utf-8').strip()
    print(f"Server: {response}")

    console = threading.Thread(target=console_thread)
    console.start()
    console.join()


if __name__ == "__main__":
    main()
