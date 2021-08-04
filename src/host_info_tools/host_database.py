#!/usr/bin/env python3
import time
import json
import hashlib

class HostInfo():
    @staticmethod
    def deSerialize(data):
        """
        Deserializes HostInfo
        """
        raw_data = json.loads(data.decode('utf-8'))
        return HostInfo(raw_data["hostname"], raw_data["update_time"], raw_data["host_info"])
        
    @staticmethod
    def deSerializeListing(data):
        """
        Deserializes a Host Listing to a dict
        """
        return json.loads(data.decode('utf-8'))

    def __init__(self, hostname, update_time, host_info):
        self.hostname = hostname
        self.update_time = update_time
        self.host_info = host_info
        self.host_info_hash = hashlib.md5(bytes(json.dumps(host_info), 'utf-8'))

    def serializeListing(self):
        """
        Returns a serialized information listing describing the host info
        """
        return json.dumps({
            "hostname": self.hostname,
            "update_time": self.update_time,
            "host_info_hash": self.host_info_hash
        })

    def serialize(self):
        """
        serializes the host info to be sent to other hosts
        """
        raw_data = {
            "hostname": self.hostname,
            "update_time": self.update_time,
            "host_info": self.host_info
        }
        return bytes(json.dumps(raw_data), 'utf-8')
    
    def isOld(self, listing):
        """
        determines if a listing is old and needs updating (changes update_time if
        the listing being compared to is newer and data is the same)
        """
        if listing["hostname"] != self.hostname:
            raise Exception("Comparing against different hostname.")
        
        if listing["update_time"] < self.update_time:
            return False
        elif listing["host_info_hash"] == self.host_info_hash:
            self.update_time = listing["update_time"]
            return False
        return True

    def updateToNow(self):
        self.update_time = time.time()

class IfaceHostDatabase():
    @staticmethod
    def deserializeHostList(data):
        ser_host_list = json.loads(cache_data.decode('utf-8'))
        host_list = []
        for h in ser_host_list:
            host_list.append(HostInfo.deSerializeListing(h))
        return host_list

    def __init__(self, iface_name, iface_ip, local_host_info = None, cache_data = None):
        # If cache_data is not none, read in host history

        self.iface_name = iface_name
        self.iface_ip = iface_ip
        self.host_info_list = {}
        self.local_host_info = None

        if cache_data is not None:
            arr = json.loads(cache_data.decode('utf-8'))
            for host_info_data in arr:
                host_info = HostInfo.deSerialize(host_info_data)
                self.host_info_list[host_info.hostname] = host_info

    def serializeHostList(self):
        """
        Generate serialized list of hosts / update_times / hash
        """
        listings = []
        for host in self.host_info_list:
            listings.append(host.getHostListing())
        return bytes(json.dumps(listings), 'utf-8')

    def compareHostLists(self, host_lists = {}}):
        """
        Gets a serial list of hosts / update_times to parse through and determine what info
        is outdated and needs updated

        Returns a list of requests for hosts and updates to send to other hosts
        """


    def getHostInfo(self, host_list):
        """
        Gets the host info for a list of hosts
        """

    def updateHostInfo(self, host_info):
        """
        Ingests host info and 
        """


class MasterHostDatabase():
    def __init__(self, cache_file = None):
        


if __name__ == "__main__":
    hd = HostDatabase()
    print(hd.serializeHosts())