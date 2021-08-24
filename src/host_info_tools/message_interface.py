import math
import json
import time
import ifcfg
import socket
import _thread

MESSAGE_DELIM = "!{!}!"

class Message():
    HANDSHAKE = 0
    LIST_RQST = 1
    HOST_LIST = 2
    INFO_RQST = 3
    HOST_INFO = 4

def deserialize_message(data):
    buffer_after = bytes("", 'utf-8')
    cur_msg_data = None
    dd = data.decode('utf-8')
    if MESSAGE_DELIM in dd:
        parts = dd.split(MESSAGE_DELIM)
        cur_msg_data = parts[0]
        if len(parts) > 2 or len(parts[1]) > 0:
            for i in range(1, len(parts)):
                if len(parts[i]) == 0:
                    continue
                buffer_after +=  bytes(parts[i] + MESSAGE_DELIM, 'utf-8')
    else:
        return None, None, data

    msg = json.loads(cur_msg_data)
    return msg["type"], msg["payload"], buffer_after

def serialize_message(type, payload):
    return bytes(json.dumps({
        "type": type,
        "payload": payload
    }) + MESSAGE_DELIM, 'utf-8')

def create_handshake(ip):
    return serialize_message(Message.HANDSHAKE,
    {
        "ip": ip
    })

def create_listing_request():
    return serialize_message(Message.LIST_RQST, {})

def create_host_list(host_list):
    return serialize_message(Message.HOST_LIST, host_list)

class MessageBuffer():
    def __init__(self, sock, timeout = 0.1, receive_buffer_size = 1024, msg_queue_size = 1):
        self.sock = sock
        self.buffer = bytes('', "utf-8")
        self.receive_buffer_size = receive_buffer_size
        self.timeout = timeout
        self.messages = {}
        self.msg_queue_size = msg_queue_size

        self.message_callbacks = {}
    
    def receiveData(self):
        self.sock.settimeout(self.timeout)
        try:
            self.buffer += self.sock.recv(self.receive_buffer_size)
            if len(self.buffer) == 0:
                raise Exception("Disconnected")
        except socket.timeout:
            pass

    def processBuffer(self):
        msg_type, payload, self.buffer = deserialize_message(self.buffer)
        if msg_type is not None:
            if msg_type in self.message_callbacks:
                self.message_callbacks[msg_type](msg_type, payload)
            if msg_type not in self.messages:
                self.messages[msg_type] = []
            if len(self.messages[msg_type]) < self.msg_queue_size:
                self.messages[msg_type].append(payload)

    def process(self):
        self.receiveData()
        self.processBuffer()

    def getMessage(self, msg_type):
        if msg_type in self.messages:
            if len(self.messages[msg_type]) > 0:
                msg = self.messages[msg_type].pop(0)
                if len(self.messages[msg_type]) == 0:
                    self.messages.pop(msg_type)
                return msg
        return None

    def waitForMessage(self, msg_type, timeout = 1.0):
        start = time.time()
        while math.fabs(time.time() - start) < timeout:
            self.process()
            res = self.getMessage(msg_type)
            if res is not None:
                return res
        return None
    
    def setMessageCallback(self, msg_type, callback):
        if callback is None:
            self.message_callbacks.pop(msg_type)
        self.message_callbacks[msg_type] = callback

class ClientConnection():
    def __init__(self, address, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.sock.connect((address, port))
        self.sock.send(create_handshake(address))

        self.message_queue = MessageBuffer(self.sock)
        msg = self.message_queue.waitForMessage(Message.HANDSHAKE, timeout = 1.0)
        if msg is None:
            raise Exception("Did not receive heartbeat :(")

    def getHostList(self):
        self.sock.send(create_listing_request())
        resp = self.message_queue.waitForMessage(Message.HOST_LIST)
        if resp is not None:
            return resp
        raise Exception("Disconnected or something :(")
    
    def sendHostList(self, host_list):
        self.sock.send(create_host_list(host_list))

class Server():
    @staticmethod
    def get_iface_from_ip(ipaddr):
        interfaces = ifcfg.interfaces()
        local = None
        for iface in interfaces:
            if interfaces[iface]["inet"] == "127.0.0.1":
                local = iface
            if interfaces[iface]["inet"] == ipaddr:
                return iface
        if ipaddr == "127.0.1.1" and local is not None:
            return local
        raise Exception("Unable to identify interface.")

    @staticmethod
    def server_connection_handler(sock, client_address, host_database):
        myaddr = sock.getsockname()[0]
        iface = Server.get_iface_from_ip(myaddr)
        print("Server connected to %s over %s"%(client_address[0], iface))
        sock.send(create_handshake(client_address))

        handshake = False
        def handshake_handler(msg_type, payload):
            handshake = True
        def list_rqst_handler(msg_type, payload):
            new_msg = host_database.getHostListings(iface)
            sock.send(create_host_list(new_msg))
        def host_list_handler(msg_type, payload):
            print(host_database.getHostListings(iface))
            host_database.processHostListing(payload, iface)


        message_queue = MessageBuffer(sock, timeout = 1.0)
        message_queue.setMessageCallback(Message.HANDSHAKE, handshake_handler)
        message_queue.setMessageCallback(Message.LIST_RQST, list_rqst_handler)
        message_queue.setMessageCallback(Message.HOST_LIST, host_list_handler)
        while True:
            try:
                message_queue.process()
            except Exception as err:
                print("Disconnected from %s"%(client_address[0]))
                break

    def __init__(self, host_address, host_port, host_database):
        print("HIS starting on  %s:%d"%(host_address, host_port))
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((host_address, host_port))
        self.host_database = host_database


    def listen(self, a1 = "filler", a2 = "filler"):
        print("HIS listening...")
        self.server_socket.listen(5)

        while True:
            connection, client_address = self.server_socket.accept()
            _thread.start_new_thread(Server.server_connection_handler,(connection, client_address, self.host_database))



