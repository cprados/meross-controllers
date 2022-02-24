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
     
async def run_controller(node):    
    '''
    Runs an instance of a controller for the given node
    Parameters:
        node (dict): the node in the config of the device
    '''

    global config
    
    # Checks meross device exists
    meross_device = meross.meross_get_device (node['meross-name'])
    if meross_device is None:
        await meross.meross_disconnect()
        return 1
        
    # Tells if keyboard is currently connected. 
    keyboard_connected = True
    
    # Tells if it is first time it checks keyboard connection since last disconnection
    first_keyboard_check = True

    while(True):

        try:
            # Wait for keyboard connection (only output first log)
            if first_keyboard_check == True:
                first_keyboard_check = False
                logging.info('Waiting for keyboard connection')                    
            keyboard = evdev.InputDevice(node['button-device'])
            first_keyboard_check = True                
            
            # Keyboard is reconnected.   
            # Toggle device as button was pressed while to reconnect keyboard
            if keyboard_connected == False:
                keyboard_connected = True
                logging.info('Keyboard reconnected at %s connected',keyboard)
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
            keyboard_connected = False
            if first_keyboard_check == True:
                logging.info(e)
            await asyncio.sleep(0.5)               
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
