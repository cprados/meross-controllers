![Bluetooth Media Button to controll an IKEA lamp connected to a Meross plug](satechi_button_on_lamp.jpg)

### Meross Controllers
#### Set of programs to control devices connected to a [Meross smart plug](https://www.meross.com/home)
Control your Meross smart plugs in two differet ways: 

 - Switch on and off lamps and other devices with a bluetooth button.
 - Automatically cut the power supply to a laptop when it is not in use, to avoid damage to the battery in the long term.

These controllers run on a Linux server, tipically a [Raspberry Pi](https://www.raspberrypi.org/), and interact with the Meross devices, the bluetooth buttons and the network:

#### Controller #1: button-controller
This controller is intended to be used to switch on and off a Meross plug by pressing a button. It can be used with an unexpensive [Satechi Bluetooth Media Button](https://www.amazon.com/Satechi-Bluetooth-Button-compatible-Samsung-Media/dp/B00RM75NL0/) or with any other device that emulates a keyboard.

As in the photo, the button can be sticked to the lamp or the controlled device, emulating a switch of the device itself. 

Controller interacts with Meross cloud to switch the plugs on and off, allowing the simultaneous use of the physical button and voice commands trough Alexa or Google Home without interference.

#### Controller #2: ip-controller
If a laptop is used in a fixed location, it is common to keep the power supply always connected. In some devices this can end up damaging the battery in the long run.

A Meross smart plug can be used with this controller to automate disconnection of the power supply when the laptop is not in use. The controller will detect the laptop is on when its IP address becomes online in the local network, and will use that event to switch on the smart plug and viceversa.
 
I first created IFTTT applet that switched the plug on and off, but after writing the button controller I decided to integrate this logic in as an additional controller.

#### Acknowledgements
I based part of my work (and this README file) in [Jonathan Blake's Bluetooth Sonos Controller](https://github.com/mochi-co/bluetooth-sonos-controller). Initially I reused his controller for my purposse without even chaning a line of code as I could configure it to invoke my IFTTT applets by pressing the Satechi Media Button, but later I decided to integrate the Meross IOT library bellow, as IFTTT was too slow and did not allow me to do "toggle". That made me write these controllers in Python3.

The magic part of controlling the Meross smart devices is thanks to the magnificent library [MerossIot](https://github.com/albertogeniola/MerossIot) written by [albertogeniola](https://github.com/albertogeniola).

#### Prerequisites
You will need:

 - One or more [Meross plugs](https://www.amazon.es/gp/product/B08PF3R4BG) to controll devices.
 - Meross [Android](https://play.google.com/store/apps/details?id=com.meross.meross) or [IOS](https://apps.apple.com/es/app/meross/id1260842951) app.
 - A bluetooth media button like the Satechi Media Button, although it will also work with any other device that emulates a keyboard or with a normal USB keyboard.
 - A Raspberry Pi or any linux machine connected to the local network, to run the controllers.

#### Setup
Steps:
1. Clone this repo to your Raspberry Pi.
2. Install Python3 if you don't have it yet.
3. Install all prerequired packages if you don't have them jet.
4. Pair and Connect the bluetooth media button with the Raspberry Pi.
5. Setup config.yaml configuration file. 
6. Configure the controllers to start on boot.

##### Clone the Repo	
	git clone https://github.com/cprados/meross-controllers.git

##### Install Python3
	sudo apt-get install python3

##### Install prerequired packages
The IP controller has to be run as root, so install the prerequired packages as root:

	sudo pip3 install evdev
	sudo pip3 install meross_iot==0.4.4.4
	sudo pip3 install --pre scapy[basic]
	sudo pip3 install PyYAML

#####  Connect to your Media Button
First you need to pair the bluetooth button to your device. We can do this with `bluetoothctl`. In raspbian I had to do it as root:

```
$ sudo bluetoothctl
agent on
scan on
```
This will then scan for nearby bluetooth devices. If you are lucky, you will see your Media Button show up. Note the device address (for later). Once you have seen the device address, trust and pair it:
```
trust DC:2C:26:BD:E0:AA
pair DDC:2C:26:BD:E0:AA
connect DC:2C:26:BD:E0:AA
```
Once it says `Connected`, you can type  `exit` to leave `bluetoothctl`.

##### Setup config.yaml configuration file
In this repo you will find an example `config.yaml` which contains the configuration of two instances of each controller. You can setup from zero to any number of instances of both controllers.

For the name of the device (meross-name) you should use the same names as in the Meross app.

For the name of the button (button-name) you can use either the name, path under `/dev/input/eventX` or bluetooth address of the button, as printed in `bluetoothctl`.

To check devices and see their names and paths, you should use `evtest`:

	$ sudo apt-get install evtest
	$ evtest

	Available devices:
        /dev/input/event0:  Logitech Wireless Keyboard PID:4023
        /dev/input/event1:  Satechi Media Button Keyboard

##### Configure the controllers to start on boot

To have the controllers automatically started, run:
```
$ crontab -e
```
And add the following lines to the crontab of a user, such as the default `pi`:
```
# Meross ip controller
*/1 * * * * sudo /home/pi/meross-controllers/ip-controller.py --config /home/pi/meross-controllers/config.yaml >>/home/pi/meross-controllers/ip-controller.log 2>>/home/pi/meross-controllers/ip-controller.log

# Meross button controller
@reboot sleep 15 && (/home/pi/meross-controllers/button-controller.py --config /home/pi/meross-controllers/config.yaml >>/home/pi/meross-controllers/button-controller.log 2>>/home/pi/meross-controllers/button-controller.log)
```
The ip-controller has to be run as root so it has to be invoked with `sudo`. To be allowed to do so, the user must have sudo permissions

This can be also automated with `systemd` services.

### Understanding config.yaml
Setup your Meross account login and password and any number of button and ip controllers. Each controller configuration contains the name of the device it controls and the controller details:

````yaml
# Meross account email
meross-email: "thisisyouremail@yourdomain.com"
    
# Meross account password
meross-password: "ThisIsYourCrearTextPassword"

# Button controllers configuration
button-controller:

    -
        # Name of the Meross device that toggles with the bluetooth button
        meross-name: "Bedroom Lamp Plug"

        # Button name, address or device path
        button-name: "DC:2C:26:BD:E0:AA"
    -
        # Name of the Meross device that toggles with the bluetooth button
        meross-name: "Another Plug"

        # Button name, address or device path
        button-name: "Logitech Wireless Keyboard PID:4023"

# IP controllers configuration
ip-controller:

    -
        # Name of the Meross device that toggles with the IP
        meross-name: "My Home Laptop Plug"

        # IP of the node 
        ip: "192.168.0.134"

        # Path to the folder with the db of status
        status-db: "/home/pi/meross-controllers/.status"

        # Number of times a node must be seen offline to consider it off
        ip-scan-trials: 3
      
    - 
        # Name of the Meross device that toggles with the IP
        meross-name: "My Work Laptop Plug"

        # IP of the node 
        ip: "192.168.0.135"

        # Path to the folder with the db of status
        status-db: "/home/pi/meross-controllers/.status"

        # Number of times a node must be seen offline to consider it off
        ip-scan-trials: 3
````
### Contributions
Contributions and feedback are both welcomed and encouraged! Open an [issue](https://github.com/cprados/meross-controllers/issues) to report a bug, ask a question, or make a feature request.
