#!/usr/bin/env python3
import sys
import time
import ifcfg
import socket
import struct
import _thread

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

    def __init__(self, hostname, interface, mcast_group, mcast_port, host_database):
        """
        Initializes host discovery on a particular interface
        """
        self.hostname = hostname
        self.interface = interface
        self.mcast_group = mcast_group
        self.mcast_port = mcast_port
        self.host_database = host_database
        self.sockets_available = False

        self.broadcast_sock = None
        # self.listen_sock = None

    def close_sockets(self):
        if self.broadcast_sock is not None:
            self.broadcast_sock.close()
            self.broadcast_sock = None
        # if self.listen_sock is not None:
        #     self.listen_sock.close()
        #     self.listen_sock = None
        self.sockets_available = False

    def check_sockets(self):
        iface_addr = HostDiscovery.getIfaceIP(self.interface)
        if iface_addr is None:
            if self.sockets_available:
                print("WARN: closed discovery on [%s]"%(self.interface), file=sys.stderr)
                self.close_sockets()
            return self.sockets_available
        
        if self.sockets_available:
            return self.sockets_available

        # Set up broadcasting
        self.broadcast_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP, fileno=None)
        self.broadcast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        self.broadcast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(iface_addr))
        self.broadcast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)

        # Set up listening
        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.broadcast_sock.bind((self.mcast_group, self.mcast_port))

        mreq = struct.pack("=4s4s", socket.inet_aton(self.mcast_group), socket.inet_aton(iface_addr))
        self.broadcast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        print("WARN: opened discovery on [%s]"%(self.interface), file=sys.stderr)
        self.sockets_available = True
        return self.sockets_available

    def broadcast_on_timer(self, interval = 1):
        """
        Broadcasts along a certain interval
        Does not return unless there is an error with the socket
        """
        while True:
            self.broadcast()
            time.sleep(interval)

    def request_broadcast(self):
        if self.check_sockets():
            self.broadcast_sock.sendto(hit_mi.create_host_id_rqst, (self.mcast_group, self.mcast_port))

        else:
            print("ERROR: unable to request broadcast on [%s], sockets not initialized."%self.interface)

    def broadcast(self):
        """
        Performs a single broadcast
        """
        if self.check_sockets():
            self.broadcast_sock.sendto(hit_mi.create_host_id(self.hostname), (self.mcast_group, self.mcast_port))
        

    def scan(self, placeholder="placeholder"):
        """
        Scans for requests and broadcasts when HOST_ID_RQST is received
        Does not return unless we disconnect
        """
        def id_rqst_handler(msg_type, payload, source):
            iface_addr = HostDiscovery.getIfaceIP(self.interface)
            if source[0] == iface_addr:
                # print("INFO: Ignoring HOST_ID_RQST request from self", file=sys.stderr)
                return
            self.broadcast()
        def id_handler(msg_type, payload, source):
            iface_addr = HostDiscovery.getIfaceIP(self.interface)
            if payload == self.hostname:
                # print("INFO: Ignoring HOST_ID from self (%s)"%(self.hostname), file=sys.stderr)
                if source[0] != iface_addr:
                    print("WARN: Possible hostname collision? Entity with same hostname [%s] has different IP [%s] instead of [%s]"
                            %(payload, source[0], iface_addr), file=sys.stderr)
                return
            self.host_database.processHostID(payload, source[0], self.interface)


        while True:
            # If the sockets are set up we run until the socket closes
            if self.check_sockets():
                message_queue = hit_mi.MessageBuffer(self.broadcast_sock, timeout = 1.0, multicast = True)
                message_queue.setMessageCallback(hit_mi.Message.HOST_ID_RQST, id_rqst_handler)
                message_queue.setMessageCallback(hit_mi.Message.HOST_ID, id_handler)
                print("WARN: listener on [%s] created"%self.interface)
                while True:
                    try:
                        message_queue.process()
                    except Exception as err:
                        print("WARN: listener on [%s] disconnected (%s)"%(self.interface, str(err)), file=sys.stderr)
                        break
            time.sleep(1.)
        
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