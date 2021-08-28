"""
Author: Josh Spisak <jspisak@andrew.cmu.edu>
Date: 8/26/2021
Description: support for discovering hosts on an interface with multicast
"""
import sys
import time
import ifcfg
import socket
import struct
import _thread
import threading

from host_info_tools import message_interface as hit_mi

class HostDiscovery():
    """
    Used to identify other hosts on the network via multicast
    """
    @staticmethod
    def getIfaceIP(interface):
        """
        Gets this hosts IP on a particular interface
        """
        if interface not in ifcfg.interfaces():
            raise Exception("Iface [%s] does not exist in ifcfg"%interface)
        info = ifcfg.interfaces()[interface]
        return info["inet"]

    def __init__(self, hostname, mcast_group, mcast_port, host_database):
        """
        Initializes host discovery
        """
        self.hostname = hostname
        self.mcast_group = mcast_group
        self.mcast_port = mcast_port
        self.host_database = host_database
        self.sockets_available = False
        self.broadcast_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) #, proto=socket.IPPROTO_UDP, fileno=None)
        self.broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.broadcast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, 
                struct.pack("4sL", socket.inet_aton(self.mcast_group), socket.INADDR_ANY))
        self.broadcast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
        self.broadcast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)

        self.broadcast_sock.bind((self.mcast_group, self.mcast_port))

    def broadcast_on_timer(self, interval = 1):
        """
        Broadcasts along a certain interval
        Does not return unless there is an error with the socket
        """
        while True:
            self.broadcast()
            time.sleep(interval)

    def request_broadcast(self):
        self.broadcast_sock.sendto(hit_mi.create_host_id_rqst(), (self.mcast_group, self.mcast_port))

    def broadcast(self):
        """
        Performs a single broadcast
        """
        self.broadcast_sock.sendto(hit_mi.create_host_id(self.hostname), (self.mcast_group, self.mcast_port))
        

    def scan(self, placeholder="placeholder"):
        """
        Scans for requests and broadcasts when HOST_ID_RQST is received
        Does not return unless we disconnect
        """
        def id_rqst_handler(msg_type, payload, source):
            self.broadcast()
        def id_handler(msg_type, payload, source):
            if payload == self.hostname:
                return
            self.host_database.processHostID(payload, source[0])

        message_queue = hit_mi.MessageBuffer(self.broadcast_sock, timeout = 1.0, multicast = True)
        message_queue.setMessageCallback(hit_mi.Message.HOST_ID_RQST, id_rqst_handler)
        message_queue.setMessageCallback(hit_mi.Message.HOST_ID, id_handler)

        while True:
            try:
                message_queue.process()
            except Exception as err:
                print("WARN: listener on disconnected (%s)"%(str(err)), file=sys.stderr)
                break
        
    def spawn_scanning_thread(self):
        """
        Spawns a thread to scan for hosts
        """
        _thread.start_new_thread(HostDiscovery.scan,(self, None))

    def spawn_broadcast_thread(self, broadcast_inverval = 5):
        """
        Spawns a thread to broadcast on a certain interval
        """
        _thread.start_new_thread(HostDiscovery.broadcast_on_timer,(self, broadcast_inverval))