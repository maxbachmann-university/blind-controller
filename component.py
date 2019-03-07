#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from transitions.extensions import LockedMachine as Machine
import paho.mqtt.client as mqtt
import threading
import json
import time
import logging
import yaml
lock = threading.Lock()

logging.basicConfig(level=logging.DEBUG)
# Set transitions' log level to INFO; DEBUG messages will be omitted
logging.getLogger('transitions').setLevel(logging.INFO)

# Functions of the state machine
class Matter(object):
    def __init__(self):
        self.BRIGHTNESS_NIGHT = 150
        self.PAUSE_TIME = 60
        self.position = 0
        self.brightness = 0
        self.time = 0
    
    # set the brightness
    def set_brightness(self, event):
        self.brightness = event.kwargs.get('brightness', 0)
        print('brightness: ', self.brightness)

    # set the position automativc according to the brightness
    def set_automatic_position(self, event):
        if (self.brightness < self.BRIGHTNESS_NIGHT):
            self.position = 0
        else:
            self.position = 100
        print('position: ', self.position)

    # set the position manually
    def set_position(self, event):
        self.position = event.kwargs.get('position', 0)
        self.time = time.time() + self.PAUSE_TIME * 60
        print('position: ', self.position)

    # check wether it should reset to automatic mode
    def compare_time(self, event):
        print('time left: ', (self.time - time.time()))
        return (time.time() > self.time)

    # return the position so it can be used outside the state machine
    def get_position(self):
        return self.position

# dict of State Machines for each room
blinds = {
    'wohnzimmer': Matter(),
    'küche': Matter()
}

# states of the state machine
states = [
    { 'name':'automatic', 'on_enter':['set_automatic_position']},
    'manual'
    ]

# transitions between states of the state machine
transitions = [
    {
        'trigger': 'change_brightness',
        'source': 'automatic',
        'dest': '=',
        'before':[
            'set_brightness',
            'set_automatic_position']
    },
    {
        'trigger': 'change_brightness',
        'source': 'manual',
        'dest': '=',
        'before':'set_brightness'
    },
    {
        'trigger': 'change_pos_manual',
        'source': 'manual',
        'dest': '=',
        'before':'set_position'
    },
    {
        'trigger': 'change_pos_manual',
        'source': 'automatic',
        'dest': 'manual',
        'before':'set_position'
    },
    {
        'trigger': 'check_auto_timeout',
        'source': 'manual',
        'dest': 'automatic',
        'conditions':'compare_time'
    }]

# initialise the state machines in the blinds dict
for room in blinds:
    Machine(blinds[room], states=states, transitions=transitions,
        initial='automatic', send_event=True)


# MQTT client to connect to the bus
mqtt_client = mqtt.Client()

# subsribe to MQTT topic on connect
def on_connect(client, userdata, flags, rc):
    if (rc == 0):
        print('[MQTT] Connected')
        client.subscribe("blindcontrol/control/#")
    elif(rc == 1):
        print('[MQTT] icorrect protocol version')
    elif(rc == 2):
        print('[MQTT] invalid client identifier')
    elif(rc == 3):
        print('[MQTT] server unavaible')
    elif(rc == 4):
        print('[MQTT] bad username or password')
    elif(rc == 5):
        print('[MQTT] not authorised')

# update the state machines when a switch back to the automatic
# mode is required
def update_positions():
    while True:
        with lock:
            for room in blinds:
                if (blinds[room].is_manual() and blinds[room].check_auto_timeout()):
                    position = blinds[room].get_position()
                    message = {'room':room, 'value':position}
                    send_position( message )
        time.sleep(5)

# update the state machines on a brightness change and
# send the new position to the actuator module
def brightness_callback(client, userdata, msg):
    print('[MQTT] Received brightness')
    with lock:
        try:
            data = json.loads(msg.payload.decode("utf-8"))

            for room in blinds:
                error = blinds[room].change_brightness(brightness=data['value'])
                print(error)
                if ( blinds[room].change_brightness(brightness=data['value']) ):
                    position = blinds[room].get_position()
                    message = {'room':room, 'value':position}
                    send_position( message )
        except:
            pass

# update the state machines on a manual position change and
# send the new position to the actuator module
def manual_callback(client, userdata, msg):
    print('[MQTT] Received manual position')
    with lock:
        try:
            data = json.loads(msg.payload.decode("utf-8"))

            position = data['value']
            rooms = data['rooms']

            if 'all' in rooms:
                rooms = blinds

            for room in rooms:
                if (room in blinds and blinds[room].set_position(position=position) ):
                    position = blinds[room].get_position()
                    message = {'room':room, 'value':position}
                    send_position( message )
        except:
            pass


# send MQTT Messages to the actuator module
def send_position(msg):
    print('[MQTT] Send Message:' + json.dumps(msg, ensure_ascii=False))
    mqtt_client.publish(('blindcontrol/position'), json.dumps(msg, ensure_ascii=False))


if __name__ == "__main__":
    # load config parameters from config file
    stream = open("config.yml", "r")
    config = yaml.safe_load(stream)

    mqtt_client.on_connect = on_connect

    # Set callbacks for mqtt topics
    # Sensor module
    mqtt_client.message_callback_add(
        "blindcontrol/control/brightness", brightness_callback)
    # manual control
    mqtt_client.message_callback_add(
        "blindcontrol/control/manual", manual_callback)

    # set password
    mqtt_client.username_pw_set(
        username=config['username'],
        password=config['password'])

    # Connect to MQTT Broker
    mqtt_client.connect(config['hostname'], config['port'])

    # start thread that tests wether it should select automatic mode again
    t = threading.Thread(target=update_positions, args=())
    t.start()

    # start mqtt loop
    mqtt_client.loop_forever()
