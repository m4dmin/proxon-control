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


##### init section ------------------------------------------------------------------------------------------------------------------------------------------

##### logging section
try:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # create a file handler
    handler = RotatingFileHandler('../log/mqtt-listener_write_proxon_influxdb.log', maxBytes=10*1024*1024, backupCount=2)
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
unlocked = False
while unlocked == False:
    try:
        logger.debug("Lock schleife start")
        lock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        logger.debug("Lock schleife bind")
        lock.bind( '\0postconnect_gateway_notify_lock') 
        unlocked = True

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
    slave_address = config['modbus']['port']

    mqtt_broker_address = config['mqtt']['broker_address']
    mqtt_client_name = str(socket.gethostname()+"."+sys.argv[0])
    mqtt_topic_prefix = "/proxon"
    mqtt_topic_debug = mqtt_topic_prefix+"/debug"

except Exception as e:
    logger.debug(e)
    sys.exit(2)

##### Proxon section
try:
    instr = minimalmodbus.Instrument(serial_port, slave_address)
    instr.serial.baudrate = 19200 
    instr.serial.bytesize = 8
    instr.serial.parity   = minimalmodbus.serial.PARITY_EVEN
    instr.serial.stopbits = 1
    instr.serial.timeout  = 0.05

except Exception as e:
    logger.debug(e)
    sys.exit(2)

##### Array section
try:
    # JSON data for influxDB write
    points = []

    # Modbus registers
        #Read Holding Register # FC4 = 3
    reg =  [[  16, 0, 3, 'wp_modus_betriebsart',            'mode',     'Betriebsart'],                         # 0=Aus, 1=EcoSommer, 2=EcoWinter, 3=Komfort, 9=Test
            [  62, 0, 3, 'wp_on-off_kuehlung',              'switch',   'Kühlung an/aus'],                      # 0=Aus, 1=An
            [  70, 2, 3, 'wp_soll-temp_zone1',              'temp',     'Wohnen  (Zone1) Soll-Temperatur'],     # -0,5 Abweichung zur Anzeige in der Anlage
            [  75, 2, 3, 'wp_soll-temp_zone2',              'temp',     'Büro KG (Zone2) Soll-Temperatur'],
            [ 133, 0, 3, 'wp_restzeit_intensivlueftung',    'time',     'Intensivlüftung Restzeit'],
            [2001, 0, 3, 't300_on-off_heizstab',            'switch',   'Heizstab an/aus'],                     # 0=Aus, 1=An
            [2000, 1, 3, 't300_soll-temp_wasser',           'temp',     'Wasser Soll-Temperatur'],
            [2003, 1, 3, 't300_schwelle-temp_wasser',       'temp',     'Wasser Temperatur-Schwelle Heizstab'],
            #Read Input Register   # FC3 = 4
            [ 814, 1, 4, 't300_temp_wasser',                'temp',     'Wasser Temperatur'],                   # +100 Abweichung zur tatsächlichen Temperatur
            [  41, 2, 4, 'wp_temp_zone1',                   'temp',     'Wohnen  (Zone1) Temperatur'],
            [  40, 2, 4, 'wp_temp_zone2',                   'temp',     'Büro KG (Zone2) Temperatur'],
            [ 593, 1, 4, 'wp_temp_kochen',                  'temp',     'Kochen Temperatur'],
            [ 596, 1, 4, 'wp_temp_diele',                   'temp',     'Diele Temperatur'],
            [ 599, 1, 4, 'wp_temp_buero-eg',                'temp',     'Büro EG Temperatur'],
            [ 602, 1, 4, 'wp_temp_schlafen',                'temp',     'Schlafen Temperatur'],
            [ 605, 1, 4, 'wp_temp_martha',                  'temp',     'Martha Temperatur'],
            [ 608, 1, 4, 'wp_temp_marlene',                 'temp',     'Marlene Temperatur'],
            [ 614, 1, 4, 'wp_temp_keller2',                 'temp',     'Keller 2 Temperatur'],
            [ 617, 1, 4, 'wp_temp_keller3',                 'temp',     'Keller 3 Temperatur'],
            [ 154, 0, 4, 'wp_stufe_ventilator-zuluft',      'level',    'Ventilator Zuluft Lüftungsstufe']]     # Stufen 1 bis 4

except Exception as e:
    logger.debug(e)
    sys.exit(2)


##### MQTT section ------------------------------------------------------------------------------------------------------------------------------------------

# when connecting to mqtt do this;
def on_connect(client, userdata, flags, rc):
    try:
        logger.info("Connected with result code "+str(rc))
        client.publish(mqtt_topic_debug,"Devive "+str(client_name)+" connected with result code "+str(rc))
    except Exception as e:
        logger.debug(e)
        sys.exit(2)


##### Runtime section ------------------------------------------------------------------------------------------------------------------------------------------
try:
    ##### MQTT section
    logger.info("Creating new MQTT instance")
    client = mqtt.Client(mqtt_client_name)
    client.on_connect = on_connect
    logger.info("Connection to MQTT broker")
    client.connect(mqtt_broker_address)
    
    ##### Proxon section
    logger.debug("0000 - Starte Lesevorgang")

    for i in range(len(reg)):
        mqtt_state_topic = mqtt_topic_prefix+"/"+str(reg[i][4])+"/"+str(reg[i][3])+"/state_topic"
        logger.debug("state_topic - "+mqtt_state_topic)

        logger.debug("Register Array - "+str(reg[i]))

        value = instr.read_register(reg[i][0],reg[i][1],reg[i][2],True)
        logger.debug("Value: "+str(value))

        if reg[i][3] == 'wp_soll-temp_zone1':
            value = value + 0.5
            logger.debug("Value: "+str(value))

        if reg[i][3] == 't300_temp_wasser':
            value = value - 100
            logger.debug("Value: "+str(value))

        client.publish(mqtt_state_topic,str(value))

        logger.info(str(reg[i][5]).ljust(35)+": "+str(value)+" "+str(reg[i][4]))
        point = {
            "measurement": str(reg[i][3]),
            "tags": {
                "instance": influxDB_tag_instance,
                "source": influxDB_tag_source
            },
            #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
        "fields": {
                str(reg[i][4]): value
                }
            }
        logger.debug(str(point))
        points.append(point)

    ##### influxDB section
    clientInfluxDB = InfluxDBClient(influxDB_ip, influxDB_port, influxDB_user, influxDB_passwd, influxDB_db)
    clientInfluxDB.write_points(points)

except Exception as e:
    logger.error(e)
    sys.exit(2)