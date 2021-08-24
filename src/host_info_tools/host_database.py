#!/usr/bin/env python3
import sys
import time
import json
import ifcfg
import threading
import hashlib

class LocalHostInfo():
    def __init__(self, hostname):
        self.hostname = hostname

    def getInfo(self, iface):
        if iface not in ifcfg.interfaces():
            raise Exception("Iface [%s] does not exist in ifcfg"%self.iface)
        info = ifcfg.interfaces()[iface]

        return {
            "hostname": self.hostname,
            "ip": info["inet"],
            "update_time": time.time()
        }

class HostInfo():
    @staticmethod
    def deSerialize(data):
        info = json.loads(data.decode('utf-8'))
        return HostInfo(info["hostname"], info["iface"], info["ip"], info["update_time"])

    def serialize(self):
        return bytes(json.dumps({
            "hostname": self.hostname,
            "iface": self.iface,
            "ip": self.ip,
            "update_time": self.update_time 
            }), 'utf-8')

    @staticmethod
    def fromInfo(info, interface):
        return HostInfo(info["hostname"], interface, info["ip"], info["update_time"])

    def __init__(self, hostname, iface, ip, update_time):
        self.hostname = hostname
        self.iface = iface
        self.ip = ip
        self.update_time = update_time

    def getInfo(self):
        return {
            "hostname": self.hostname,
            "ip": self.ip,
            "update_time": self.update_time
        }
    
    def updateTo(self, new_info, iface):
        if new_info["hostname"] != self.hostname:
            return
        if new_info["update_time"] > self.update_time or self.update_time > time.time():
            self.update_time = new_info["update_time"]
            self.ip = new_info["ip"]
            if self.iface != iface:
                print("Warning: swapping %s from iface %s to %s"%(), file=sys.stderr)
            self.iface = iface

class HostDatabase():
    def __init__(self, local_host_info = None):
        # If cache_data is not none, read in host history
        self.host_info_list = {}
        self.local_host_info = local_host_info
        self.mutex = threading.Lock()

    def getHostListings(self, interface = None):
        """
        Generate serialized list of hosts / update_times / hash
        """
        self.mutex.acquire()
        try:
            listings = []
            for host in self.host_info_list:
                if interface is not None and self.host_info_list[host].iface != interface:
                    continue
                listings.append(self.host_info_list[host].getInfo())
            if self.local_host_info is not None:
                listings.append(self.local_host_info.getInfo(interface))

            self.mutex.release()
            return listings
        except Exception as err:
            self.mutex.release()
            raise err

    def processHostListing(self, host_list, interface):
        self.mutex.acquire()
        try:
            for host_info in host_list:
                host_name = host_info["hostname"]
                if self.local_host_info is not None:
                    if host_name == self.local_host_info.hostname:
                        continue
                if host_name in self.host_info_list:
                    self.host_info_list[host_name].updateTo(host_info, interface)
                else:
                    self.host_info_list[host_name] = HostInfo.fromInfo(host_info, interface)
            self.mutex.release()
        except Exception as err:
            self.mutex.release()
            raise err
