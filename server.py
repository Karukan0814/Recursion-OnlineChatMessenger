import socket

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
        sent = sock.sendto(data, address)
        print("sent {} bytes back to {}".format(sent, address))
