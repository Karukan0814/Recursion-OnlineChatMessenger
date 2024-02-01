import socket
import sys

# チャットルームの作成と接続（TCP）


# カスタム TCP プロトコルを作成し、クライアントとサーバがチャットルームの作成と接続のために通信できるようにします。TCP は、メッセージの受信と順序が保証されるため、信頼性が高いです。以下は、チャットルームプロトコル（TCRP）と呼ぶカスタムプロトコルです。
# ヘッダー（32 バイト）: RoomNameSize（1 バイト） | Operation（1 バイト） | State（1 バイト） | OperationPayloadSize（29 バイト）
# ボディ: 最初の RoomNameSize バイトがルーム名で、その後に OperationPayloadSize バイトが続きます。ルーム名の最大バイト数は 28 バイトであり、OperationPayloadSize の最大バイト数は 229 バイトです。
# RoomNames は UTF-8 でエンコード/デコードされます。OperationPayload は、操作と状態に応じて異なる方法でデコードされる可能性があります（整数、文字列、JSON ファイルなど）
# 新しいチャットルームを作成する場合、操作コードは 1 です。0 はリクエスト、1 は準拠、2 は完了です。TCP は完全なトランザクションを保証するために使用されます。
# サーバの初期化（0）: クライアントが新しいチャットルームを作成するリクエストを送信します。ペイロードには希望するユーザー名が含まれます。
# リクエストの応答（1）: サーバはステータスコードを含むペイロードで即座に応答します。
# リクエストの完了（2）: サーバは特定の生成されたユニークなトークンをクライアントに送り、このトークンにユーザー名を割り当てます。このトークンはクライアントをチャットルームのホストとして識別します。トークンは最大 255 バイトです。
# 新しいチャットルームに参加しようとするとき、操作コードは 2 です。状態は作成時と同様で、クライアントも生成されたトークンを受け取りますが、ホストではありません。
# チャットルームごとに、サーバは許可されたリストトークンのリストを追跡する必要があります。ユーザーがそのトークンで参加すると、トークンの所有者として設定されます。メッセージがチャットルーム内の他のすべての人にリレーされるためには、トークンと IP アドレスが一致しなければなりません。
# チャットルームの作成またはチャットルームへの参加が完了すると、TCP コネクションは終了します。クライアントは自動的に UDP でサーバに接続します。
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


def receive_message(sock, stop_event):
    while not stop_event.is_set():
        try:
            data, _ = sock.recvfrom(4096)
            print("Received:", data.decode("utf-8"))
        except:
            pass


def talk_in_room(user_name, token, room_name):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ("localhost", 9001)
    stop_event = threading.Event()

    # 受信スレッドを開始
    receiver_thread = threading.Thread(target=receive_message, args=(sock, stop_event))
    receiver_thread.start()

    try:
        while True:
            message = input("Input your message (or type 'exit' to quit): ")
            if message.lower() == "exit":
                break
            full_message = f"{room_name}:{token}:{user_name}:{message}"
            if full_message.encode("utf-8") > 4096:
                print("message should be less than 4096 bytes")
                continue
            else:
                sock.sendto(full_message.encode("utf-8"), server_address)
    finally:
        # 受信スレッドを停止
        stop_event.set()
        receiver_thread.join()
        sock.close()


def input_validation_max(input_name: str, max_length: int):
    while True:
        input_val = input("Please input your name: ")
        encoded_name = input_val.encode("utf-8")

        if len(encoded_name) <= max_length:
            return input_val
        else:
            print(input_name + " must be less than " + str(max_length) + " bytes!")


def main():
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
        talk_in_room(user_name, token, room_name)

    except:
        print("starting a chat room failed")
        sock.close()
        sys.exit(1)


main()
