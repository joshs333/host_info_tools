#!/usr/bin/env python3
import yaml

def load_config(file):
    try:
        with open(file, 'r') as stream:
            return yaml.safe_load(stream)
    except Exception as err:
        print("Unable to load config: %s", str(err))


if __name__ == "__main__":
    iface = "eno1"

    sr = ScanRange("eno1")
    sr.getIPs()

    # for k in ifcfg.interfaces():
    #     print(k)