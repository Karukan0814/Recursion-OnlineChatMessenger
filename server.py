import socket
import time


class Chatclient:
    def __init__(self, userid, address, last_activity=None):
        self.userid = userid
        self.address = address

        self.last_activity = (
            last_activity if last_activity is not None else time.time()
        )  # ユーザーが最後にメンションした時刻

    def update_last_activity(self):
        self.last_activity = time.time()


all_message = b""

# アクティブなクライアントのマップ
active_clients = {}

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
        # クライアントから来たデータから最初の1バイト＝ゆーざーIDを抜き出す
        userid = data[0:1]
        # バイトからintに変換
        userid_int = int.from_bytes(userid, "big")
        # アクティブなクライアントのマップに既に存在するか確認
        if userid_int not in active_clients:
            # なかったら新たにクライアントのデータを作って入れる
            active_clients[userid_int] = Chatclient(userid_int, address)
        else:
            # あったら最終メンション時刻を更新
            active_clients[userid_int].update_last_activity()

        # タイムアウトチェック→タイムアウトしたユーザーはアクティブユーザーリストから削除する
        current_time = time.time()
        for userid in list(active_clients):
            if current_time - active_clients[userid].last_activity > timeout_period:
                print(f"Client {userid} has timed out and will be removed.")
                del active_clients[userid]

        # 現在アクティブなユーザーにのみメッセージを送る
        message = data[1:]
        all_message = all_message + b"\n" + message
        for userid in list(active_clients):
            # アクティブなユーザーのアドレスにメッセージを送る
            print(active_clients[userid].address)
            sent = sock.sendto(all_message, active_clients[userid].address)
