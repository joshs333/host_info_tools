"""
Author: Josh Spisak <jspisak@andrew.cmu.edu>
Date: 8/26/2021
Description: stores information on various hosts that have been interacted with
"""
import sys
import time
import json
import ifcfg
import threading
import hashlib

class LocalHostInfo():
    def __init__(self, hostname):
        self.hostname = hostname

    def serialize(self):
        return {
            "hostname": self.hostname,
            "ip_addr": "127.0.1.1",
            "last_update": time.time()
        }

class HostDatabase():
    class HostInfo():
        def serialize(self):
            return {
                "hostname": self.hostname,
                "ip_addr": self.ip_addr,
                "last_update": self.last_update
            }
        hostname = None
        ip_addr = None
        last_update = None

    def __init__(self, local_host_info = None):
        self.local_host_info = local_host_info
        self.host_lists = {}
        self.mutex = threading.Lock()

    def updateHost(self, hostname, ip_addr, update_time, force = False):
        """
        This function assumes the mutex is held and doesn't try to claim it!
        """
        self.mutex.acquire()
        try:
            if hostname not in self.host_lists:
                entry = HostDatabase.HostInfo()
                entry.hostname = hostname
                entry.ip_addr = ip_addr
                entry.last_update = time.time()
                self.host_lists[hostname] = entry
            else:
                entry = self.host_lists[hostname]
                if force or entry.last_update < update_time:
                    entry.last_update = update_time
                    if entry.ip_addr != ip_addr:
                        print("WARN: Host [%s] ip changed from [%s] to [%s]"%(hostname, entry.ip_addr, ip_addr), file=sys.stderr)
                        entry.ip_addr = ip_addr
        except Exception as err:
            print("ERROR: unable to update host - %s"%(str(err)), file=sys.stderr)
        self.mutex.release()

    def processHostID(self, host_id, ip_addr):
        """
        Handles when a HOST_ID message is received
        """
        self.updateHost(host_id, ip_addr, time.time(), force=True)

    def getHostListings(self):
        """
        Generate serialized list of hosts / update_times / hash
        """
        listings = []
        self.mutex.acquire()
        try:
            for host in self.host_lists:
                listings.append(self.host_lists[host].serialize())
            if self.local_host_info is not None:
                listings.append(self.local_host_info.serialize())

        except Exception as err:
            self.mutex.release()
            raise err

        self.mutex.release()
        return listings

    def processHostListing(self, host_list, interface):
        for host_info in host_list.keys():
            host_name = host_info["hostname"]
            if self.local_host_info is not None:
                if host_name == self.local_host_info.hostname:
                    continue
        
            self.updateHost(host_name, host_info["ip_addr"], host_info["interface"], host_info["update_time"])
