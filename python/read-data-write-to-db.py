#!/usr/bin/env python3

import time
import datetime
import configparser
import logging
from logging.handlers import RotatingFileHandler
import minimalmodbus
import serial
import sys
import json
from influxdb import InfluxDBClient
import paho.mqtt.client as mqtt
import socket
import random
import time
import ast


##### init section ------------------------------------------------------------------------------------------------------------------------------------------

##### logging section
try:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # create a file handler
    handler = RotatingFileHandler('../log/read-data-write-to-db.log', maxBytes=10*1024*1024, backupCount=2)
    handler.setLevel(logging.DEBUG)

    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(handler)

    # logging examples
    logger.debug("Debug Log")
    # logger.info("Info Log")
    # logger.warning("Warning Log")
    # logger.error("Error Log")
    # logger.critical("Critical Log")

except Exception as e:
    sys.exit(1)

##### Process Lock section
locked = True
while locked == True:
    try:
        logger.debug("Lock schleife start")
        lock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        logger.debug("Lock schleife bind")
        lock.bind( '\0postconnect_gateway_notify_lock') 
        locked = False

    except socket.error as e:
        logger.debug(e)
        delay = random.randint(5, 15)
        logger.info("Process is already running. Waiting "+str(delay)+" seconds")
        time.sleep(delay)

else:
    logger.info("No other processes running. Going forward")

##### config section
try:
    config = configparser.ConfigParser()
    config.read('../conf/proxon-control.conf')

    influxDB_ip = config['influxDB']['ipAdresse']
    influxDB_port = config['influxDB']['port']
    influxDB_user = config['influxDB']['user']
    influxDB_passwd = config['influxDB']['password']
    influxDB_db = config['influxDB']['db']
    influxDB_tag_instance = config['influxDB']['tag_instance']
    influxDB_tag_source = config['influxDB']['tag_source']

    serial_port = config['modbus']['port']
    # - write_register(registeraddress: int, value: Union[int, float], number_of_decimals: int = 0, functioncode: int = 16, signed: bool = False)
    # - read_register(registeraddress: int, number_of_decimals: int = 0, functioncode: int = 3, signed: bool = False)
    reg = ast.literal_eval(config.get("modbus", "register"))
   
    mqtt_broker_address = config['mqtt']['broker_address']
    mqtt_client_name = str(socket.gethostname()+sys.argv[0])
    mqtt_topic_prefix = "/proxon"
    mqtt_topic_debug = mqtt_topic_prefix+"/debug"

    points = []

except Exception as e:
    logger.debug(e)
    sys.exit(2)

##### Proxon section
try:
    instr = minimalmodbus.Instrument(serial_port, 41)
    instr.serial.baudrate = 19200 
    instr.serial.bytesize = 8
    instr.serial.parity   = minimalmodbus.serial.PARITY_EVEN
    instr.serial.stopbits = 1
    instr.serial.timeout  = 0.05

except Exception as e:
    logger.debug(e)
    sys.exit(3)


##### MQTT section ------------------------------------------------------------------------------------------------------------------------------------------

# logging MQTT
def on_log(client, userdata, level, buf):
    logger.debug("MQTT-Log: ",buf)

# handling disconnects
def on_disconnect(client, userdata, rc):
    logging.info("DISCONNECT REASON "  +str(rc))
    client.connected_flag=False
    client.disconnect_flag=True

# when connecting to mqtt do this;
def on_connect(client, userdata, flags, rc):
    logger.debug("TEST CONNECT")
    try:
        logger.info("Connected with result code "+str(rc))
        client.publish(mqtt_topic_debug,"Devive "+str(mqtt_client_name)+" connected with result code "+str(rc))

        ##### Proxon section
        logger.debug("Starte Lesevorgang")

        for i in range(len(reg)):
            mqtt_state_topic = mqtt_topic_prefix+"/"+str(reg[i][6])+"/"+str(reg[i][5])+"/state"
            logger.debug("state_topic - "+mqtt_state_topic)
            logger.debug("Register Array - "+str(reg[i]))
            value = instr.read_register(reg[i][0],reg[i][1],reg[i][3],True)

            if reg[i][5] == 'wp_soll-temp_zone1':
                value = value + 0.5
                logger.debug("Value: "+str(value))

            if reg[i][5] == 't300_temp_wasser':
                value = value - 100
                logger.debug("Value: "+str(value))

            if reg[i][6] == 'mode' or reg[i][6] == 'switch' or reg[i][6] == 'level' or reg[i][6] == 'min':
                value = int(value)

            if reg[i][6] == 'temp':
                value = float(value)

            logger.debug("Value: "+str(value))

            client.publish(mqtt_state_topic,str(value),qos=2,retain=True)

            logger.debug(str(reg[i][7]).ljust(35)+": "+str(value)+" "+str(reg[i][6]))
            point = {
                "measurement": str(reg[i][5]),
                "tags": {
                    "instance": influxDB_tag_instance,
                    "source": influxDB_tag_source
                },
                #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
                "fields": {
                    str(reg[i][6]): value
                    }
                }
            logger.debug(str(point))
            points.append(point)

        clientInfluxDB.write_points(points)

        lock.close()
        logger.info("Closed running processes")

        loop.stop()

    except Exception as e:
        logger.debug(e)
        sys.exit(5)


##### Runtime section ------------------------------------------------------------------------------------------------------------------------------------------
try:
    ##### influxDB section
    clientInfluxDB = InfluxDBClient(influxDB_ip, influxDB_port, influxDB_user, influxDB_passwd, influxDB_db)
    
    ##### MQTT section
    logger.info("Creating new MQTT instance")
    client = mqtt.Client(mqtt_client_name)
    client.on_log=on_log
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    logger.info("Connection to MQTT broker")
    client.connect(mqtt_broker_address)
    logger.info("Closed connection to MQTT broker")

except Exception as e:
    logger.error(e)
    sys.exit(6)