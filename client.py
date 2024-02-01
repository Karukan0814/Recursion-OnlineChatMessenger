import socket
import sys

# チャットルームの作成と接続（TCP）


def create_header(room_name_size, operation, state, operation_payload_size):
    # 各値をバイト列に変換
    room_name_size_bytes = room_name_size.to_bytes(1, byteorder="big")
    operation_bytes = operation.to_bytes(1, byteorder="big")
    state_bytes = state.to_bytes(1, byteorder="big")
    operation_payload_size_bytes = operation_payload_size.to_bytes(29, byteorder="big")

    # ヘッダーの組み立て
    header = (
        room_name_size_bytes
        + operation_bytes
        + state_bytes
        + operation_payload_size_bytes
    )
    return header


def create_body(room_name, operation_payload):
    # ルーム名とオペレーションペイロードをUTF-8でバイト列にエンコード
    room_name_bytes = room_name.encode("utf-8")
    operation_payload_bytes = operation_payload.encode("utf-8")

    # ボディの組み立て
    body = room_name_bytes + operation_payload_bytes
    return body


import threading

# グローバル変数で認証エラーを追跡
auth_error = False

# ユーザーがチャットを終了したい場合のためのグローバル変数
exit_command = False


def receive_message(sock, stop_event):
    global auth_error
    while not stop_event.is_set():
        try:
            data, _ = sock.recvfrom(4096)
            print("Received:", data.decode("utf-8"))
            message = data.decode("utf-8")
            if message == "Invalid token":
                #  認証エラーが起きていた場合、停止
                # 認証エラー時にメッセージの送受信を停止→main()の最初からやり直したい
                auth_error = True
                stop_event.set()
        except:
            pass


def talk_in_room(user_name, token, room_name):
    global auth_error
    global exit_command

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ("localhost", 9001)
    stop_event = threading.Event()

    # 受信スレッドを開始
    receiver_thread = threading.Thread(target=receive_message, args=(sock, stop_event))
    receiver_thread.start()

    try:
        while True:
            if auth_error:
                print("Authentication error occurred. Exiting chat room.")
                return "auth_error"
            if exit_command:
                print("Exiting chat room.")
                return "exit_command"
            message = input("Input your message (or type 'exit' to quit): ")
            if message.lower() == "exit":
                print("exit", message)
                exit_command = True
                # return "exit_command"
            full_message = f"{room_name}:{token}:{user_name}:{message}"
            if len(full_message.encode("utf-8")) > 4096:
                print("message should be less than 4096 bytes")
                continue
            else:
                # サーバにメッセージを送る
                sock.sendto(full_message.encode("utf-8"), server_address)
    finally:
        # 受信スレッドを停止
        print("talk_in_room finally")
        stop_event.set()
        receiver_thread.join()
        sock.close()


def input_validation_max(input_name: str, max_length: int):
    while True:
        input_val = input("Please input " + input_name + ": ")
        encoded_name = input_val.encode("utf-8")

        if len(encoded_name) <= max_length:
            return input_val
        else:
            print(input_name + " must be less than " + str(max_length) + " bytes!")


def main():
    global auth_error
    global exit_command
    while True:
        auth_error = False
        exit_command = False

        user_name = input_validation_max("user name", 255)
        start_room = input("Do you start a new chat? - y/n")
        room_name = input_validation_max("room name", 28)

        # サーバが待ち受けているポートにソケットを接続します
        server_address = "localhost"
        server_port = 9002
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print("connecting to {}".format(server_address, server_port))
        try:
            sock.connect((server_address, server_port))
        except socket.error as err:
            print(err)
            sys.exit(1)

        operation = 2
        print("start_room", start_room)
        if start_room == "y" or start_room == "Y":
            operation = 1
            # 新たなチャットルームを作成する
            print("starting a new chat room...")
        else:
            print("entering the chat room...")

        try:
            # ヘッダー（32 バイト）: RoomNameSize（1 バイト） | Operation（1 バイト） | State（1 バイト） | OperationPayloadSize（29 バイト）
            header = create_header(len(room_name), operation, 0, len(user_name))
            # ヘッダの送信
            sock.send(header)
            # ボディの送信
            body = create_body(room_name, user_name)
            sock.send(body)

            # サーバーからの応答（トークン）を待ち受ける
            while True:
                response = sock.recv(1)
                response_value = int.from_bytes(response, "big")  # レスポンスを整数に変換
                if response_value == 0:
                    print("initializing")
                elif response_value == 1:
                    print("preparing")
                elif response_value == 2:
                    print("success!")
                    break
                else:
                    raise Exception("something wrong with starting chatroom")

            # サーバーからトークンを受け取る
            response = sock.recv(4096)

            token = response.decode("utf-8")
            print("received token", token)
            sock.close()

            # チャット開始
            # talk_in_room(user_name, token, room_name)
            chat_result = talk_in_room(user_name, token, room_name)

            if chat_result == "exit_command":  # ユーザーが終了を希望する場合
                print("Exiting the chat room...")
                # break  # main()関数から抜ける
                continue  # main()関数の最初からやり直す

            if chat_result == "auth_error":
                print("Authentication error. Restarting...")
                continue  # main()関数の最初からやり直す

        except:
            print("starting a chat room failed")
            sock.close()
            sys.exit(1)


main()
