import sys
import time
import math
import ifcfg
import heapq
import fnmatch

from multiprocessing import Pool
from host_info_tools import message_interface as hit_mi


def getIFaceInfo(iface_name):
    if iface_name not in ifcfg.interfaces():
        raise Exception("Iface [%s] does not exist in ifcfg"%iface_name)
    info = ifcfg.interfaces()[iface_name]
    return info["inet"], info["netmask"]

class IFaceScanner():
    def getIPs(self):
        ip_split = self.ip.split(".")
        netmask_split = self.netmask.split(".")
        ip_range_split = self.ip_range.split(".")

        if len(ip_split) != 4:
            raise Exception("Invalid IP: %s"%(self.ip))
        if len(netmask_split) != 4:
            raise Exception("Invalid Netmask: %s"%(self.netmask))
        if len(ip_range_split) != 4:
            raise Exception("Invalid IP Range: %s"%(self.ip_range))

        resulting_ip_list = []
        def getIPsInRange(idx, cur_ip = ""):
            """
            There's probably a better way to do this... at any rate - yay recursion! :)
            """
            if idx == 4:
                if cur_ip[0] == ".":
                    cur_ip = cur_ip[1:]
                if not self.skip_self or cur_ip != self.ip:
                    resulting_ip_list.append(cur_ip)
                return
            if netmask_split[idx] == "255":
                ip = cur_ip + "." + ip_split[idx]
                getIPsInRange(idx + 1, ip)
            elif ip_range_split[idx] == "255":
                ip = cur_ip + "." + ip_split[idx]
                getIPsInRange(idx + 1, ip)
            elif "-" in ip_range_split[idx]:
                rsp = ip_range_split[idx].split("-")
                if len(rsp) != 2:
                    raise Exception("Invalid range: %s"%(ip_range_split[idx]))
                try:
                    rsp_start = int(rsp[0])
                    rsp_end = int(rsp[1])
                    if rsp_start < 0:
                        rsp_start = 0
                    if rsp_end > 255:
                        rsp_end = 255
                    while rsp_start < rsp_end:
                        ip = cur_ip + "." + str(rsp_start)
                        getIPsInRange(idx + 1, ip)
                        rsp_start += 1
                except Exception as err:
                    raise Exception("Invalid range: %s. %s"%(ip_range_split[idx], str(err)))
            else:
                try:
                    ipn = int(ip_range_split[idx])
                    if ipn < 0 or ipn > 254:
                        raise Exception("Invalid range: %s (not within 0 - 254)."%(ip_range_split[idx]))
                    ip = cur_ip + "." + str(ipn)
                    getIPsInRange(idx + 1, ip)
                except Exception as err:
                    raise Exception("Invalid range: %s."%(ip_range_split[idx]))
        
        getIPsInRange(0, "")
        return resulting_ip_list

    def __init__(self, interface, ip_range, skip_self = True):
        self.interface = interface
        self.ip, self.netmask = getIFaceInfo(self.interface)
        self.ip_range = ip_range
        self.skip_self = skip_self
        self.ip_listing = self.getIPs()

    def getScanJobs(self, port):
        ip, netmask = getIFaceInfo(self.interface)
        if ip != self.ip or netmask != self.netmask:
            self.ip = ip
            self.netmask = netmask
            self.ip_listing = self.getIPs()

        jobs = []
        for ip in self.ip_listing:
            jobs.append((self.interface, ip, port))
        return jobs

def scan_job(args):
    interface, ip, sp = args
    c = None
    try:
        c = hit_mi.ClientConnection(ip, sp)
    except Exception as err:
        pass
    return (interface, ip, c)  

class ScanScheduler():
    def __init__(self, iface_whitelest, iface_blacklist, scan_range_default, scan_pool_size, scan_port, host_database, skip_self = True):
        self.iface_whitelest = iface_whitelest
        self.iface_blacklist = iface_blacklist
        self.scan_range_default = scan_range_default
        self.scan_pool_size = scan_pool_size
        self.skip_self = skip_self
        self.scan_port = scan_port
        self.host_database = host_database
        self.scanners = {}
        self.scan_timers = []

        # If the whitelist isn't specified - generate it from the interfaces not in the blacklist
        if len(self.iface_whitelest) < 1:
            for iface in ifcfg.interfaces():
                match = False
                for biface in self.iface_blacklist:
                    if fnmatch.fnmatch(iface, biface):
                        match = True
                
                if not match:
                    print("Adding interface %s - %s"%(iface, self.scan_range_default), file=sys.stderr)
                    self.iface_whitelest.append({
                        "interface": iface
                    })
        self.generateScanners()
            
    def generateScanners(self):
        # Delete scanners that are for no longer valid interfaces
        for scanner in self.scanners.keys():
            if scanner not in ifcfg.interfaces():
                self.scanners.pop(scanner)

        # Generate scanners for each valid interface
        for scan_info in self.iface_whitelest:
            if scan_info["interface"] in self.scanners:
                continue
            try:
                sr = self.scan_range_default
                if "scan_range" in scan_info:
                    sr = scan_info["scan_range"]
                scanner = IFaceScanner(scan_info["interface"], sr, self.skip_self)
                self.scanners[scan_info["interface"]] = scanner
            except Exception as err:
                print("Error: unable to scan %s - %s"%(scan_info["interface"], str(err)), file=sys.stderr)

    def scanOnInterval(self, interval, aa = "This is filler"):
        """
        Spawn a thread for this to scan on a requested interval
        """
        next_scan_time = 0.0

        while True:
            now = time.time()
            scan = False

            if math.fabs(now - next_scan_time) > interval:
                next_scan_time = now + interval
                scan = True
            elif now > next_scan_time:
                next_scan_time += interval
                scan = True
            
            if scan:
                self.scanAll()
            
            wait = next_scan_time - time.time()
            if wait > interval:
                wait = interval
            if wait < 0.:
                continue
            time.sleep(wait)

    def scanAll(self):
        """
        Scan all interfaces and update the host database
        """
        self.generateScanners()

        print("Scanning all.")

        jobs = []
        for interface in self.scanners:
            scanner = self.scanners[interface]
            try:
                jobs.extend(scanner.getScanJobs(self.scan_port))
            except Exception as err:
                print("Error: unable to get scan jobs for %s."%(interface), file=sys.stderr)
        self.performScanJobs(jobs)

        print("Scan complete.")
        
    def performScanJobs(self, jobs):

        results = None
        with Pool(processes = self.scan_pool_size) as pool:
            results = pool.map(scan_job, jobs)

        print("GOt map results")
        connections = {}
        for result in results:
            interface, addr, connection = result
            if connection is None:
                continue
            print(addr)
            clist = connection.getHostList()
            self.host_database.processHostListing(clist, interface)
            if interface not in connections:
                connections[interface] = []
            connections[interface].append(connection)
        for interface in connections:
            ilist = self.host_database.getHostListings(interface)
            for c in connections[interface]:
                c.sendHostList(ilist)
