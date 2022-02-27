#!/usr/bin/python3
'''
ip-controller.py: checks status of a computers whose IPs are defined in configuration file and
turn on/off the the plug where they are connected as the corresponding IP goes online/offline
'''

import logging
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO) 
logging.getLogger("meross_iot").setLevel(logging.ERROR) 

import argparse
import yaml
import meross
import os
import asyncio
import requests
import scapy.all

# Global config dictionary
config = None

def scan_node(ip):
    '''
    Scans the network for a given IP address ussing arping method.
    Parameters: 
        ip (str): the ip v4 address or cidr range
    Returns:
        true: IP found
        false: IP not found
    '''
    answer=scapy.all.arping(ip, verbose=False, timeout=2)[0]
    if len(answer)>0:
        logging.debug("IP %s is up", ip)
        result = True
    else:
        logging.debug("IP %s is down", ip)
        result = False            
    
    return result 

def check_update_status (node):
    '''
    Checks current state of an IP and compares with the previous state stored.
    Parameters: 
        node (dict): the node in the config of the device
    Returns: 
        0: IP still disconnected, 
        1: IP has connected
        2: IP still connected
        3: IP disconnected       
    '''

    # Creates status folder
    folder = node['status-db']
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Check current IP status
    ip = node['ip']
    trials = node['ip-scan-trials']
    scan_response = scan_node(ip)

    # Check if IP was registered before
    file_path = os.path.join(folder, ip)
    file_exists = os.path.exists(file_path)
    
    # IP was not connected
    if not file_exists:
        # IP has connected
        if (scan_response == True):

            # Set counter to #trials
            status_file = open(file_path, "w")
            status_file.write(str(trials))
            status_file.close()
            logging.info("IP %s has connected", ip)
            return 1

        # IP still disconnected
        else:
            logging.debug("IP %s is still disconnected", ip)
            return 0

    # IP was connected
    else:
        # IP still connected
        if (scan_response == True): 

            # Set counter to #trials
            status_file = open(file_path, "w")
            status_file.write(str(trials))
            status_file.close()
            logging.debug("IP %s is still connected", ip)
            return 2

        # IP has disconnected
        else:
            # Read value of counter
            status_file = open(file_path, "r+")
            counter = int(status_file.read())

            # Decreases value of counter
            counter = counter - 1
            if (counter == 0):
                status_file.close()
                os.remove(file_path)
                logging.info("IP %s has disconnected", ip)
                return 3
            else:
                status_file.seek(0)
                status_file.write(str(counter))
                status_file.close()
                logging.debug("IP %s is still connected", ip)
                return 2 

async def main():
    '''
    Main program
    '''
    
    global config
        
    # Processes each node
    for node in config['ip-controller']:

        # Checks status of IP has changed
        status = check_update_status(node)

        # Connects if needed and turns on or off the device
        if status == 1:         
            await meross.meross_switch (config, node, "on");

        elif status == 3:
            await meross.meross_switch (config, node, "off");
    
    # Disconnects from meross server if connected
    await meross.meross_disconnect()

if __name__ == '__main__':
    
    # Parse input parameters
    parser = argparse.ArgumentParser(description='Switch on and off a Meross plug as the IP of a computer connected to the plug becomes online or offline')
    parser.add_argument('-c', '--config', type=str, help='Configuration file (yaml)', required=True)
    args = parser.parse_args()
    
    # Processes config file
    with open(args.config) as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)
    
    # Windows and python 3.8 requires to set up a specific event_loop_policy.
    #  On Linux and MacOSX this is not necessary.
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
