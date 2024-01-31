import socket
import time
import threading
import secrets


def generate_token(length):
    # 安全なランダムトークンを生成
    return secrets.token_urlsafe(length)


class Chatclient:
    def __init__(
        self, userid: int, token: str, address=None, last_activity: float = None
    ):
        self.userid = userid
        self.token = token
        self.address = address
        self.last_activity = (
            last_activity if last_activity is not None else time.time()
        )  # ユーザーが最後にメンションした時刻

    def update_last_activity(self):
        self.last_activity = time.time()

    def set_address(self, address):
        self.address = address


class Chatroom:
    def __init__(self, room_name: str, owner_token: str, owner_info: Chatclient):
        self.room_name = room_name
        active_clients = {}  # Chatclientのデータが入っていく
        # まず、作成者を入れておく owner_infoはChatclientである
        active_clients[owner_info.userid] = owner_info
        self.active_clients = active_clients
        self.owner_token = owner_token

        self.messagelist = ["first message"]

    def add_message(self, message):
        self.messagelist.append(message)

    def del_userlist(self, userid):
        self.userlist.pop(userid, None)

    def update_userlist(self, userid, address):
        # アクティブなクライアントのマップに既に存在するか確認
        if userid not in self.userlist:
            # トークン生成
            secret_num = secrets.token_urlsafe(255 - len(userid))
            token = str(userid) + secret_num
            # なかったら新たにクライアントのデータを作って入れる
            self.userlist[userid] = Chatclient(userid, address, token)
        else:
            # あったら最終メンション時刻を更新
            self.userlist[userid].update_last_activity()


# チャットルームのマップ
chatrooms: {int: Chatroom} = {}


def enter_chatroom():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = "0.0.0.0"
    server_port = 9002
    # 次に、サーバは bind()関数を使用して、ソケットをサーバのアドレスとポートに紐付けします。その後、listen()関数を呼び出すことで、サーバは着信接続の待ち受けを開始します。サーバは一度に最大1つの接続を受け入れることができます。
    sock.bind((server_address, server_port))

    sock.listen(1)

    print("starting up on port {}".format(server_port))

    while True:
        # その後、サーバは無限ループに入り、クライアントからの着信接続を継続的に受け付けます。このコードでは、accept()関数を使用して、着信接続を受け入れ、クライアントのアドレスを取得します。
        connection, client_address = sock.accept()
        try:
            print("connection from", client_address)
            reaction = 0
            # サーバの初期化（0）: クライアントが新しいチャットルームを作成するリクエストを送信します。ペイロードには希望するユーザー名が含まれます。
            connection.sendall(reaction.to_bytes(1, "big"))

            # 次に、クライアントから受信したデータのヘッダを読み取り、変数headerに格納します。
            # ヘッダー（32 バイト）: RoomNameSize（1 バイト） | Operation（1 バイト） | State（1 バイト） | OperationPayloadSize（29 バイト）
            # 重要：ユーザー名はペイロードの中！

            header = connection.recv(32)

            # 長さはヘッダから抽出され、別々の変数に格納されます。
            roomname_size = int.from_bytes(header[:1], "big")
            operation = int.from_bytes(header[1:2], "big")
            state = int.from_bytes(header[2:3], "big")
            operation_payload_size = int.from_bytes(header[3:32], "big")
            print("roomname_size", roomname_size)
            print("operation", operation)
            print("state", state)
            print("operation_payload_size", operation_payload_size)

            # ルーム名の最大バイト数は 28 バイトであり、OperationPayloadSize の最大バイト数は 229 バイトです。
            if roomname_size > 28 or operation_payload_size > 229:
                raise Exception(
                    "roomname_size should be under 28 bytes and operation_payload_size should be under 229 bytes"
                )

            # ボディ: 最初の RoomNameSize バイトがルーム名で、その後にユーザー名、 OperationPayloadSize バイトが続きます。
            # 次に、クライアントからチャットルーム名とユーザー名とoperation_payloadを読み取り、変数に格納します。
            body = connection.recv(roomname_size + operation_payload_size)
            # RoomNamesとユーザー名 は UTF-8 でエンコード/デコードされます。
            room_name = body[:roomname_size].decode("utf-8")

            # OperationPayload は、操作と状態に応じて異なる方法でデコードされる可能性があります（整数、文字列、JSON ファイルなど）
            operation_payload = body[
                roomname_size : roomname_size + operation_payload_size
            ]
            # ペイロードの中にユーザー名が入っている
            user_name = operation_payload.decode("utf-8")

            print("room_name", room_name)
            print("user_name", user_name)

            # 新しいチャットルームを作成する場合、操作コードは 1 です。0 はリクエスト、1 は準拠、2 は完了です。TCP は完全なトランザクションを保証するために使用されます。
            if operation == 1:
                # 新しいチャットルームを作成

                # クライアントにリクエストを処理していることを伝える
                reaction = 1
                connection.sendall(reaction.to_bytes(1, "big"))

                # 新しいチャットルームを作成開始
                # トークンを生成
                # なおかつ、ユーザーをチャットルームのメンバーに入れる
                owner_token = secrets.token_urlsafe(255)
                owner_info = Chatclient(operation_payload_size, owner_token)
                newroom = Chatroom(room_name, owner_token, owner_info)

                # 作成したチャットルームを全チャットルームのマップに入れておく
                chatrooms[roomname_size] = newroom

                # リクエストの完了（2）: サーバは特定の生成されたユニークなトークンをクライアントに送り、このトークンにユーザー名を割り当てます。
                # クライアントにリクエストが完了したことを伝える
                reaction = 2
                connection.sendall(reaction.to_bytes(1, "big"))

                # クライアントにトークンを送る
                print("owner_token", owner_token)
                connection.sendall(owner_token.encode("utf-8"))

                # このトークンはクライアントをチャットルームのホストとして識別します。トークンは最大 255 バイトです。
            elif operation == 2:
                # 既存のチャットルームに参加
                connection.sendall("既存のチャットルーム".encode())

        # 新しいチャットルームに参加しようとするとき、操作コードは 2 です。状態は作成時と同様で、クライアントも生成されたトークンを受け取りますが、ホストではありません。
        # チャットルームごとに、サーバは許可されたリストトークンのリストを追跡する必要があります。ユーザーがそのトークンで参加すると、トークンの所有者として設定されます。メッセージがチャットルーム内の他のすべての人にリレーされるためには、トークンと IP アドレスが一致しなければなりません。

        except Exception as e:
            print("Error: " + str(e))

        finally:
            print("Closing current connection")
            connection.close()


def send_chat():
    # タイムアウト期間（秒）
    timeout_period = 60 * 2

    # AF_INETを使用し、UDPソケットを作成
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    server_address = "0.0.0.0"
    server_port = 9001
    print("starting up on port {}".format(server_port))

    # ソケットを特殊なアドレス0.0.0.0とポート9001に紐付け
    sock.bind((server_address, server_port))

    while True:
        print("\nwaiting to receive message")
        # メッセージ送信時、サーバとクライアントは一度に最大で 4096 バイトのメッセージを処理します。
        # これは、クライアントが送信できるメッセージの最大サイズです。
        # 同じく、最大 4096 バイトのメッセージが他の全クライアントに転送されます。

        # メッセージの最初の 1 バイト、usernamelen は、ユーザー名の全バイトサイズを示し、これは最大で 255バイト（28 - 1 バイト）
        # サーバはこの初めの usernamelen バイトを読み、送信者のユーザー名を特定します。
        data, address = sock.recvfrom(4096)

        # サーバにはリレーシステムが組み込まれており、現在接続中のすべてのクライアントの情報を一時的にメモリ上に保存します。新しいメッセージがサーバに届くと、そのメッセージは現在接続中の全クライアントにリレーされます。
        print("received {} bytes from {}".format(len(data), address))
        print(data.decode())

        if data:
            # 受信データのデコード
            decoded_data = data.decode("utf-8")

            # チャットルーム名、トークン、ユーザー名、メッセージの分解
            room_name, token, user_name, message = decoded_data.split(":", 3)

            # チャットルームの情報を取り出す
            chatroom_info = chatrooms[len(room_name)]
            print("chatroom_info", chatroom_info)

            # 認証されているユーザーであるか確認
            active_clients = chatroom_info.active_clients
            print("active_clients", active_clients)

            # バイトからintに変換
            userid_int = len(user_name)
            # アクティブなクライアントのマップに既に存在するか確認
            if userid_int not in active_clients:
                raise Exception("this user is not authorized")
            else:
                # チャットルーム内にあったら、トークンが一致するか確認
                userinfo = active_clients[userid_int]
                print("userinfo", userinfo.token)
                if token == userinfo.token:
                    # トークンが一致＝認証OK
                    # アドレスを入れる
                    active_clients[userid_int].set_address(address)
                    # あったら最終メンション時刻を更新
                    active_clients[userid_int].update_last_activity()
                else:
                    raise Exception("this user is not authorized")

            # タイムアウトチェック→タイムアウトしたユーザーはアクティブユーザーリストから削除する
            current_time = time.time()
            for userid in list(active_clients):
                if current_time - active_clients[userid].last_activity > timeout_period:
                    print(f"Client {userid} has timed out and will be removed.")
                    del active_clients[userid]

            # 現在アクティブなユーザーにのみメッセージを送る
            all_message = user_name + ":" + message
            for userid in list(active_clients):
                # アクティブなユーザーのアドレスにメッセージを送る
                print(active_clients[userid].address)
                sent = sock.sendto(
                    all_message.encode("utf-8"), active_clients[userid].address
                )


def main():
    # カウントダウンのためのスレッドを作成
    chatroom_thread = threading.Thread(target=enter_chatroom)

    # メッセージ出力のためのスレッドを作成
    sendchat_thread = threading.Thread(target=send_chat)

    # スレッドを開始
    chatroom_thread.start()
    sendchat_thread.start()

    # 無限ループを含むスレッドなので、joinは使用しない
    # 必要に応じて他の方法でスレッドの終了を管理する


main()
