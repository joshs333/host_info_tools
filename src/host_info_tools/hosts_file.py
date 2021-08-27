"""
Author: Josh Spisak <jspisak@andrew.cmu.edu>
Date: 8/26/2021
Description: Generates a hosts file from hosts database
"""
import os
import re
import sys
import time
import ifcfg
import socket
import struct
import shutil
import _thread
import tempfile

class HostFile():
    def __init__(self, file, host_database, override_without_id = False, line_id="Host Info Tools Generated Line"):
        self.file = file
        self.host_database = host_database
        self.line_id = line_id
        self.override_without_id = override_without_id
        self.list = {}

        self.suppress_warning = {}

    def update(self):
        new_list = self.host_database.getHostListings()

        new_list_map = {}
        for h in new_list:
            new_list_map[h["hostname"]] = h

        # Get the lines from the input file (if it exists)
        lines = []
        try:
            with open(self.file, 'r') as f:
                # for line in f.read().split("\n"):
                for line in f:
                    lines.append(line)
        except Exception as err:
            # print(err)
            pass

        # For each line we compare against our new list
        # to see what needs / can be changed
        out_lines = []
        for line in lines:
            # There is probably a better parser than this lolz
            # First we will split based on spacing (retaining comments)
            host_split_init = re.split('\t|\n| +', line)

            # If this is not a valid entry we will spit it back out
            if len(host_split_init) < 2 or "#" in host_split_init[0]:
                out_lines.append(line)
                continue
            
            # We know we have 2 blocks (space or tab delimited)
            # lets make sure the second block is not a comment
            if len(host_split_init[1]) <= 0 or (len(host_split_init[1]) > 0 and host_split_init[1][0] == "#"):
                out_lines.append(line)
                continue
            
            # We know this is a valid line so we can split out comments too
            host_split = re.split(r'#|\t|\n| +', line)
            ip = host_split[0]
            host = host_split[1]
            
            can_change = self.line_id in line or self.override_without_id

            # print(host)
            # print(new_list_map)
            if host in new_list_map:
                if ip != new_list_map[host]["ip_addr"] and can_change:
                    continue
                # If it's different then we can't change it and print a warning
                if ip != new_list_map[host]["ip_addr"] and host not in self.suppress_warning:
                    print("WARN: unable to change host [%s] in [%s]"%(host, self.file))
                    self.suppress_warning[host] = True
                new_list_map.pop(host)
            out_lines.append(line)

        changes = len(new_list_map) > 0
        for host in new_list_map:
            out_lines.append("%s\t%s\t# %s\n"%(
                new_list_map[host]["ip_addr"], host, self.line_id
            ))

        if changes:
            # tmp_file = "/tmp/host_info_%s"%(self.file.replace("\\", "_").replace("/", "_"))
            fd, tmp_file = tempfile.mkstemp()
            with open(tmp_file, "w+") as f:
                for i in range(len(out_lines)):
                    f.write("%s"%out_lines[i])
            try:
                shutil.copymode(self.file, tmp_file)
                os.remove(self.file)
            except:
                pass
            shutil.move(tmp_file, self.file)
        
    def update_on_interval(self, interval = 1.):
        while True:
            self.update()
            time.sleep(interval)

    def spawn_update_thread(self, interval = 1.):
        _thread.start_new_thread(HostFile.update_on_interval,(self, interval))