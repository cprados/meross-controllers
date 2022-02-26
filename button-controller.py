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

async def get_button_by_name (button_name, lock):
    '''
    Detects when a device with the given name, address or /dev/input/* path is connected
    Parameters:
        keyboard_name (str): the name, address or device path of the keyboard
        lock (bool):
            true: lock untill keyboard is connected
            false: check keyboard it is present and return without locking
    Returns:
        device (evdev.device.InputDevice): the device or None if lock is false and keyboard is not pressent
    '''

    result = None
    compare = button_name.lower()
    while (True):

        for path in evdev.list_devices():
            device = evdev.InputDevice(path)
            if (device.uniq.lower() == compare or device.name.lower() == compare or device.path == compare):
                logging.info('Button connected: %s %s %s', device.uniq, device.name, device.path)
                result = device
                break

        if (not result is None or lock == False):
            break

        await asyncio.sleep(0.5)

    return result

async def run_controller(node):
    '''
    Runs an instance of a button-controller
    Parameters:
        node (dict): the button-controller node in the config dictionary
    '''

    global config

    # Check if the button is initially connected
    button_name = node['button-name']
    logging.info('Checking if button %s is connected', button_name)
    button = await get_button_by_name (button_name, False)

    while (True):

        try:
            # If button is not connected wait for connection
            if (button is None):
                logging.info('Waiting for button %s to be connected', button_name)
                button = await get_button_by_name (button_name, True)

                # Button reconnected: toggle device as button was pressed
                await meross.meross_switch (config, node, "toggle")

            # Wait for button pressed
            logging.info('Waiting for key event on button %s', button_name)
            async for event in button.async_read_loop():
                if event.type == evdev.ecodes.EV_KEY and event.value == 0:
                    logging.info('Key %s pressed on button %s', evdev.ecodes.KEY[event.code], button_name)
                    await meross.meross_switch (config, node, "toggle")
                    logging.info('Waiting for key event on button %s', button_name)

        # Button disconnected while waiting for key pressed
        except OSError as ose:
            logging.info("Button %s disconnected: %s", button_name, ose)
            button = None
            continue

        # Track other exceptions
        except Exception as e:
            logging.info("Other exception: %s, %s", e.__class__.__name__, e)
            continue

    # Disconnects from meross server if connected
    await meross.meross_disconnect()

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
