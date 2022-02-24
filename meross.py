'''
meross.py: Module that groups Meross IOT API calls for convenience of the controller modules
See: https://github.com/albertogeniola/MerossIot
'''

import datetime
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
import logging

# Global config dictionary
config = None

# Manager of the Meross API
manager = None

async def meross_init (init_config):
    '''
    Connects to Meross cloud.
    Parameters:
        init_config (dict): config dictionary
    '''    
    global manager
    global config
    
    if manager is None:
    
        # Setup the HTTP client API from user-password
        config = init_config
        http_api_client = await MerossHttpClient.async_from_user_password(email=config['meross-email'], password=config['meross-password'])
    
        # Setup and start the device manager
        manager = MerossManager(http_client=http_api_client)
        await manager.async_init()
    
        # Retrieve all the devices that are registered on this account
        await manager.async_device_discovery()
        logging.info("Connected to Meross server")

def meross_get_device (name):
    '''
    Fetches device with given name.
    Parameters:
        name (str): name of the device to fetch
    Returns:
        device (meross_iot.controller.device.BaseDevice): the device
    '''
    
    global manager
    
    # Fetches device with given name            
    devices = manager.find_devices(device_name=name);
    if len(devices) < 1:
        logging.info("Meross device %s not found", name)
        return None
        
    logging.info("Meross device %s found", name)
    return devices[0]

async def meross_switch (init_config, node, op):
    '''
    Executes action requested on a Meross device, initializing connection if needed first time it is invoked .
    Parameters:
        init_config (dict): config dictionary
        node (dict): the node in the config of the device
        op (str): string containing the operation to do on the device: on, off (otherwise toggle).
    '''

    global manager
    
    # Initialices meross connection if first time
    if manager is None:
        await meross_init (init_config)

    # Fetches device with given name
    device = meross_get_device(node['meross-name'])
        
    # Acts on the device
    if not (device is None):

        # Check last toggle was triggered > 1 minute ago
        meross_last_toggle = node.get('meross-last-toggle')
        if meross_last_toggle is None or meross_last_toggle < datetime.datetime.now()-datetime.timedelta(minutes=1):
            # Update device status: this is needed only the very first time
            # or if the connection goes down
            logging.info('Updating device status %s', device.name)
            await device.async_update()
    
        # Toggle device status (on, off, toggle)
        if op == "on":
            logging.info('Switching on device %s', device.name)
            await device.async_turn_on(channel=0)
        elif op == "off":
            logging.info('Switching off device %s', device.name)
            await device.async_turn_off(channel=0)
        else: 
            logging.info('Toggling device %s', device.name)
            await device.async_toggle(channel=0)
        
        # Saves last toggle timestamp
        node['meross-last-toggle']= datetime.datetime.now()

async def meross_disconnect ():
    '''
    Disconnects from Meross cloud
    '''

    global manager

    # Close the manager and logout from http_api
    if not (manager is None):
        manager.close()
        await manager._http_client.async_logout()
        logging.info("Disconnected from Meross server")
