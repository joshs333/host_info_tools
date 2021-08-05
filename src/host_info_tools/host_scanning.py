import ifcfg

class ScanRange():
    def __init__(self, iface, ip_range = "255.255.255.10-15"):
        self.iface = iface
        self.ip_range = ip_range

    def getIFace(self):
        if self.iface not in ifcfg.interfaces():
            raise Exception("Iface [%s] does not exist in ifcfg"%self.iface)
        info = ifcfg.interfaces()[self.iface]
        return info["inet"], info["netmask"]

    def getIPs(self):
        ip_list = []

        ip, netmask = self.getIFace()
        ip_split = ip.split(".")
        netmask_split = netmask.split(".")
        ip_range_split = self.ip_range.split(".")

        if len(ip_split) != 4:
            raise Exception("Invalid IP: %s"%(ip))
        if len(netmask_split) != 4:
            raise Exception("Invalid Netmask: %s"%(netmask))
        if len(ip_range_split) != 4:
            raise Exception("Invalid IP Range: %s"%(ip_range))

        def getIPsInRange(idx, cur_ip = ""):
            if idx == 4:
                if cur_ip[0] == ".":
                    cur_ip = cur_ip[1:]
                ip_list.append(cur_ip)
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
                    raise Exception("Invalid range: %s."%(ip_range_split[idx]))
            else:
                try:
                    ipn = int(ip_range_split[idx])
                    if ipn < 0 or ipn > 254:
                        raise Exception("Invalid range: %s (not within 0 - 254)."%(ip_range_split[idx]))
                    ip = cur_ip + "." + str(ipn)
                    getIPsInRange(idx + 1, ip)
                except Exception as err:
                    raise Exception("Invalid range: %s."%(ip_range_split[idx]))
        

                print(cur_ip)
        getIPsInRange(0, "")
        return ip_list

