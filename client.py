import socket


# メッセージ送信時、サーバとクライアントは一度に最大で 4096 バイトのメッセージを処理します。これは、クライアントが送信できるメッセージの最大サイズです。同じく、最大 4096 バイトのメッセージが他の全クライアントに転送されます。
# セッションが開始される際には、クライアントはユーザーにユーザー名を入力させます。
# バイトデータは UTF-8 でエンコードおよびデコードされます。これは、1 文字が 1 から 4 バイトで表現される意味です。Python の str.encode と str.decode メソッドは、デフォルトでこの挙動を持っています。
# サーバにはリレーシステムが組み込まれており、現在接続中のすべてのクライアントの情報を一時的にメモリ上に保存します。新しいメッセージがサーバに届くと、そのメッセージは現在接続中の全クライアントにリレーされます。
# クライアントは、何回か連続で失敗するか、しばらくメッセージを送信していない場合、自動的にリレーシステムから削除されます。この点で TCP と異なり、UDP はコネクションレスであるため、各クライアントの最後のメッセージ送信時刻を追跡する必要があります。


# サーバとクライアントは、UDP ネットワークソケットを使ってメッセージのやり取りをします。
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = "localhost"
server_port = 9001

address = ""
port = 9050
message = b"Message to send to the client."

max_size = 4096  # 最大バイトサイズ


# 接続の失敗回数　最大３回接続に失敗したらコネクションを切る
failure_count = 0

user_name = None

while True:
    try:
        if user_name is None:
            # 起動後初回はユーザー名を入力させる
            user_name = input("Please input your name")

        # ユーザー名をバイト変換
        user_name_byte = user_name.encode("utf-8")
        # ユーザー名（バイト）の長さを取得
        user_name_length = len(user_name_byte)
        if user_name_length > 255:
            print("User name must be less than 256 bytes!")
            break

        # メッセージを入力させる
        message = input("Input your message")
        message = user_name + ":" + message  # メッセージの最初にユーザー名をつけておく
        # メッセージをバイト変換
        message_byte = message.encode("utf-8")

        if len(message_byte) > 4095:
            print("Message must be less than 4095 bytes!")
            break

        # 最終的に送るメッセージを作成（ユーザー名の長さ＋メッセージ→バイト）
        final_message = user_name_length.to_bytes(1, "big") + message_byte

        # この情報はサーバとクライアントによって自由に使用され、ユーザー名の表示や保存が可能です。

        print("sending {!r}".format(final_message))
        # サーバへのデータ送信
        sent = sock.sendto(final_message, (server_address, server_port))
        print("Send {} bytes".format(sent))

        # 応答を受信
        print("waiting to receive")
        data, server = sock.recvfrom(4096)
        print("received {!r}".format(data))

    except:
        failure_count = failure_count + 1
        print("connection failed" + str(failure_count))
        # 3回以上エラーが起きたら接続を切る
        if failure_count >= 3:
            break

sock.close()
