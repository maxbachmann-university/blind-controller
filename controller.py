#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import paho.mqtt.client as mqtt
import json
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
    'küche': 0,
}

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

def blind_states():
    print()
    print()
    print("----CONTROL STATE-----")
    print("BRIGHTNESS: " + str(brightness) + " lux")
    print("{:<15}".format("room") + " | " + "{:<10}".format("state"))
    print("----------------------------")
    for room, timestamp in blinds.items():
        state = "automatic"
        if (timestamp != 0):
            state = "manual"
        print("{:<15}".format(room) + " | " + "{:<10}".format(state))
    print()
    print()

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

                    message = {'room':room, 'value':position}
                    send_position(message)
                    blind_states()

def brightness_callback(client, userdata, msg):
    global brightness
    with lock:
        print('[MQTT] Received brightness')
        try:
            data = json.loads(msg.payload.decode("utf-8"))
            brightness = data['value']
            
            position = calc_position()

            for room, timestamp in blinds.items():
                if (timestamp == 0):
                    message = {'room':room, 'value':position}
                    send_position(message)

            blind_states()
        except:
            pass

def manual_callback(client, userdata, msg):
    print('[MQTT] Received manual position')
    with lock:
        try:
            data = json.loads(msg.payload.decode("utf-8"))
            seconds = time.time() + pause_time * 60

            position = data['value']
            rooms = data['rooms']

            if 'all' in rooms:
                rooms = blinds

            for room in rooms:
                if room in blinds:
                    blinds[room] = seconds
                    message = {'room':room, 'value': position}
                    send_position(message)
            blind_states()
        except:
            pass


def send_position(msg):
    print('[MQTT] Send Message:' + json.dumps(msg))
    mqtt_client.publish(('blindcontrol/position'),
                        json.dumps(msg))


if __name__ == "__main__":
    blind_states()
    mqtt_client.on_connect = on_connect
    mqtt_client.message_callback_add("blindcontrol/control/brightness", brightness_callback)
    mqtt_client.message_callback_add("blindcontrol/control/manual", manual_callback)
    mqtt_client.username_pw_set(username="user", password="password")
    mqtt_client.connect("localhost", 1883)
    t = threading.Thread(target=update_positions, args=())
    t.start()
    mqtt_client.loop_forever()
