#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import paho.mqtt.client as mqtt
import json
import logging
import threading

lock = threading.Lock()

# MQTT client to connect to the bus
mqtt_client = mqtt.Client()

# Brightness Day (in lux)
BRIGHTNESS_NIGHT = 150

# Pause when manual defined in min
pause_time = 1

brightness = 0

# define blinds
blinds = {
    'wohnzimmer': 0,
    'kueche': 0,
}

def on_connect(client, userdata, flags, rc):
    if (rc == 0):
        logging.info('[MQTT] Connected')
        client.subscribe("blindcontrol/control/#")
    elif(rc == 1):
        logging.warning('[MQTT] icorrect protocol version')
    elif(rc == 2):
        logging.warning('[MQTT] invalid client identifier')
    elif(rc == 3):
        logging.warning('[MQTT] server unavaible')
    elif(rc == 4):
        logging.warning('[MQTT] bad username or password')
    elif(rc == 5):
        logging.warning('[MQTT] not authorised')

def calc_position():
    position = 0
    if (brightness < BRIGHTNESS_NIGHT):
        position = 0
    elif (brightness >= BRIGHTNESS_NIGHT):
        position = 100
    return position

def update_positions():
    while True:
        with lock:
            seconds = time.time()
            position = calc_position()
            for room, timestamp in blinds.items():
                if (timestamp != 0 and timestamp < seconds):
                    blinds[room] = 0

                    logging.info('[Brightness] Room: ' + room + ', position: ' + str(position))
                    msg = {'room':room, 'value':position}
                    send_position(msg)

def brightness_callback(client, userdata, msg):
    global brightness
    with lock:
        logging.info('[MQTT] Received brightness')
        try:
            data = json.loads(msg.payload.decode("utf-8"))
            brightness = data['value']
            logging.info('[Brightness] ' + str(brightness) + ' lux')
            
            position = calc_position()

            for room, timestamp in blinds.items():
                if (timestamp == 0):
                    logging.info('[Brightness] Room: ' + room + ', position: ' + str(position))
                    msg = {'room':room, 'value':position}
                    send_position(msg)
        except:
            pass

def manual_callback(client, userdata, msg):
    logging.info('[MQTT] Received manual position')
    with lock:
        try:
            data = json.loads(msg.payload.decode("utf-8"))
            seconds = time.time() + pause_time * 20

            position = data['value']
            rooms = data['rooms']

            if 'all' in rooms:
                rooms = blinds

            for room in rooms:
                if room in blinds:
                    logging.info('[Manual] Room: ' + room + ', position: ' + str(position))
                    blinds[room] = seconds
                    msg = {'room':room, 'value': position}
                    send_position(msg)
        except:
            pass


def send_position(msg):
    logging.info('[MQTT] Send Message:' + json.dumps(msg))
    mqtt_client.publish(('blindcontrol/position'),
                        json.dumps(msg))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mqtt_client.on_connect = on_connect
    mqtt_client.message_callback_add("blindcontrol/control/brightness", brightness_callback)
    mqtt_client.message_callback_add("blindcontrol/control/manual", manual_callback)
    mqtt_client.username_pw_set(username="user", password="password")
    mqtt_client.connect("localhost", 1883)
    t = threading.Thread(target=update_positions, args=())
    t.start()
    mqtt_client.loop_forever()
