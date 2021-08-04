import json
import time

class Message():
    HANDSHAKE = 0
    LIST_RQST = 1
    HOST_LIST = 2
    INFO_RQST = 3
    HOST_INFO = 4

def deserialize_message(data):
    buffer_after = bytes("", 'utf-8')
    cur_msg_data = ""
    dd = data.decode('utf-8')
    if "!!!" in dd:
        parts = dd.split("!!!")
        cur_msg_data = parts[0]
        if len(parts) > 2 or len(parts[1]) > 0:
            for i in range(1, len(parts)):
                if len(parts[i]) == 0:
                    continue
                buffer_after +=  bytes(parts[i] + "!!!", 'utf-8')
    else:
        return None, data

    return json.loads(cur_msg_data), buffer_after

def serialize_message(message):
    return bytes(json.dumps(message) + "!!!", 'utf-8')

def create_handshake(ip):
    return serialize_message({
        "type": Message.HANDSHAKE,
        "ip": ip
    })

def create_listing_request():
    return serialize_message({
        "type": Message.LIST_RQST
    })

def create_info_request(host_list):
    return serialize_message({
        "type": Message.INFO_RQST,
        "len": len(host_list),
        "list": host_list
    })

def create_host_list(host_list):
    return serialize_message({
        "type": Message.HOST_LIST,
        "len": len(host_list),
        "list": host_list
    })

def create_host_info(info_list):
    return serialize_message({
        "type": Message.HOST_LIST,
        "len": len(info_list),
        "list": info_list
    })


class ClientConnection():
    def __init__(self, socket, target_address):
        self.socket = socket
        self.target_address = target_address
        socket.send(create_handshake(target_address))
        socket.send(create_handshake(target_address))
        socket.send(create_handshake(target_address))
    
        socket.settimeout(1.0)
        data = socket.recv(1024)
        if len(data) == 0:
            socket.close()
            raise Exception("Disconnected from server %s"%str(target_address))
        msg = deserialize_message(data)
        if msg["type"] != Message.HANDSHAKE:
            socket.close()
            raise Exception("Disconnected from server %s"%str(target_address))

def server_connection_handler(socket, client_address, host_database):
    def get_data(cur_buffer):
        cur_buffer += socket.recv(4096)
        if len(cur_buffer) == 0:
            raise Exception("Disconnected from %s"%str(client_address))
        return cur_buffer

    data = get_data(bytes("", 'utf-8'))
    while True:
        msg, data = deserialize_message(data)
        if msg is not None:
            print(msg)
        else:
            data = get_data(data)
