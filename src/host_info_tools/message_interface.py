"""
Author: Josh Spisak <jspisak@andrew.cmu.edu>
Date: 8/26/2021
Description: a quick, lightweight network protocol
"""

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

    # Used to request a host ID
    HOST_ID_RQST = 5

    # Contains a 
    HOST_ID = 7

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

def create_host_id_rqst():
    return serialize_message(Message.HOST_ID_RQST, {})

def create_host_id(host_name):
    return serialize_message(Message.HOST_ID, host_name)

class MessageBuffer():
    def __init__(self, sock, timeout = 0.1, receive_buffer_size = 1024, msg_queue_size = 1, multicast = False):
        self.sock = sock
        self.buffer = bytes('', "utf-8")
        self.multicast_buffers = {}
        self.receive_buffer_size = receive_buffer_size
        self.timeout = timeout
        self.messages = {}
        self.msg_queue_size = msg_queue_size
        self.multicast = multicast

        self.message_callbacks = {}
    
    def receiveData(self):
        self.sock.settimeout(self.timeout)
        try:
            if self.multicast:
                buffer, source_ip = self.sock.recvfrom(self.receive_buffer_size)
                if len(buffer) == 0:
                    raise Exception("Disconnected")
                if source_ip not in self.multicast_buffers:
                    self.multicast_buffers[source_ip] = bytes('', "utf-8")
                self.multicast_buffers[source_ip] += buffer
            else:
                self.buffer += self.sock.recv(self.receive_buffer_size)
                if len(self.buffer) == 0:
                    raise Exception("Disconnected")
        except socket.timeout:
            pass

    def processBuffer(self, buffer, buffer_source = None):
        msg_type, payload, buffer = deserialize_message(buffer)
        if msg_type is not None:
            if msg_type in self.message_callbacks:
                if buffer_source is not None:
                    self.message_callbacks[msg_type](msg_type, payload, buffer_source)
                else:
                    self.message_callbacks[msg_type](msg_type, payload)
            if len(self.message_callbacks) <= 0:
                if msg_type not in self.messages:
                    self.messages[msg_type] = []
                if len(self.messages[msg_type]) < self.msg_queue_size:
                    self.messages[msg_type].append(payload)
        return buffer

    def process(self):
        self.receiveData()
        if self.multicast:
            for source_ip in self.multicast_buffers.keys():
                self.multicast_buffers[source_ip] = self.processBuffer(self.multicast_buffers[source_ip], source_ip)
        else:
            self.buffer = self.processBuffer(self.buffer)

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
