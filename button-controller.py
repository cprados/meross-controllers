#!/usr/bin/python3
'''
button-controller.py: toggles a Meross plug by pressing a bluetooth button
'''

import logging
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO) 
logging.getLogger("meross_iot").setLevel(logging.ERROR) 

import argparse
import yaml
import meross
import evdev
import asyncio
import os

# Global config dictionary
config = None

def get_keyboard_by_name (keyboard_name): 
    '''
    Blocks untill a keyboard with given name is detected. Checks every 0.5 sec.
    Parameters:
        keyboard_name (str): the name of the keyboard expected
    Returns:
        result (evdev.device.InputDevice): the device
    '''
    
    result = None
    logging.info('Waiting for keyboard % to be connected', keyboard_name) 
    while (result is None):
        for path in evdev.list_devices():
            device = evdev.InputDevice(path)
            if (device.name == keyboard_name):
                result = device
        await asyncio.sleep(0.5)
                 
async def run_controller(node):    
    '''
    Runs an instance of a controller for the given node
    Parameters:
        node (dict): the node in the config of the device
    '''

    global config
            
    # Tells if keyboard is currently connected. 
    keyboard_connected = True

    while(True):

        try:
            # Wait for keyboard connection
            # Problem: button names aren't unique neither...
            keyboard = get_keyboard_by_name (node['button-name'])            
            
            # Keyboard is reconnected. Toggle device as button was pressed
            if keyboard_connected == False:
                keyboard_connected = True
                logging.info('Keyboard reconnected at %s connected', keyboard)
                await meross.meross_switch (config, node, "toggle")
            else:
                logging.info('Keyboard was connected at %s',keyboard)

            # Wait for key pressed
            logging.info('Waiting for key pressed')
            
            async for event in keyboard.async_read_loop():
                if event.type == evdev.ecodes.EV_KEY and event.value == 0:
                    logging.info('Key %s pressed', evdev.ecodes.KEY[event.code])
                    await meross.meross_switch (config, node, "toggle")
                    logging.info('Waiting for key pressed')
        
        except Exception as e:
            # Problem: if Exception is in meros_switch and keyboard is connected it will go to an endless loop invoking meros_switch
            keyboard_connected = False
            logging.info(e)             
            continue

    # Disconnects from meross server if connected
    await meross.meross_disconnect()
    return 0

async def main():
    '''
    Main program
    '''
    
    global config
    
    # Connects to meross cloud
    await meross.meross_init (config)

    # Run as many tasks as controller nodes defined
    loop = asyncio.get_running_loop()
    for node in config['button-controller']:
        logging.info('Running button-controller for %s', node['meross-name'])
        loop.create_task(run_controller(node))

if __name__ == '__main__':

    # Parse input parameters
    parser = argparse.ArgumentParser(description='Toggles a Meross plug by pressing a bluetooth button')
    parser.add_argument('-c', '--config', type=str, help='Configuration file (yaml)', required=True)
    args = parser.parse_args()
    
    # Processes config file
    with open(args.config) as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)
    
    # Windows and python 3.8 requires to set up a specific event_loop_policy.
    #  On Linux and MacOSX this is not necessary.
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())       
    
    # Rus as many async io loops as controller nodes defined
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever() 
