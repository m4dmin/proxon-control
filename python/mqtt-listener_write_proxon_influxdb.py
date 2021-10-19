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

    mqtt_broker_address = config['mqtt']['broker_address']
    mqtt_client_name = str(socket.gethostname()+sys.argv[0])
    mqtt_topic_prefix = "/proxon"
    mqtt_topic_debug = mqtt_topic_prefix+"/debug"

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
    sys.exit(2)

##### Array section
try:
    # JSON data for influxDB write
    points = []

    # Modbus registers
    # - write_register(registeraddress: int, value: Union[int, float], number_of_decimals: int = 0, functioncode: int = 16, signed: bool = False)
    # - read_register(registeraddress: int, number_of_decimals: int = 0, functioncode: int = 3, signed: bool = False)
    #        reg-nr, nr-decimals-read, nr-decimals-write, functioncode, signed,             device/measurement, type (HA), comment
    reg =  [[    16,                0,                 0,            3,   True,         'wp_modus_betriebsart',    'mode', 'Betriebsart'],                         # 0=Aus, 1=EcoSommer, 2=EcoWinter, 3=Komfort
            [    62,                0,                 0,            3,     '',           'wp_on-off_kuehlung',  'switch', 'Kühlung an/aus'],                      # 0=Aus, 1=An
            [  2001,                0,                 0,            3,   True,         't300_on-off_heizstab',  'switch', 'Heizstab an/aus'],                     # 0=Aus, 1=An
            [    70,                2,                 1,            3,   True,           'wp_soll-temp_zone1',    'temp', 'Wohnen  (Zone1) Soll-Temperatur'],     # 100 - 295  ##-0,5 Abweichung zur Anzeige in der Anlage
            [    75,                2,                 1,            3,   True,           'wp_soll-temp_zone2',    'temp', 'Büro KG (Zone2) Soll-Temperatur'],     # 100 - 295
            [  2000,                1,                 1,            3,   True,        't300_soll-temp_wasser',    'temp', 'Wasser Soll-Temperatur'],              # 450 - 600
            [  2003,                1,                 1,            3,   True,    't300_schwelle-temp_wasser',    'temp', 'Wasser Temperatur-Schwelle Heizstab'], # 400 - 500
            [   133,                0,                 0,            3,   True, 'wp_restzeit_intensivlueftung',     'min', 'Intensivlüftung Restzeit']]            # 0 - 1440

except Exception as e:
    logger.debug(e)
    sys.exit(2)


##### MQTT section ------------------------------------------------------------------------------------------------------------------------------------------

# when connecting to mqtt do this;
def on_connect(client, userdata, flags, rc):
    logger.debug("TEST CONNECT")
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

    try:
        logger.info("Connected with result code "+str(rc))
        client.publish(mqtt_topic_debug,"Devive "+str(mqtt_client_name)+" connected with result code "+str(rc))

        points = []

        for i in range(len(reg)):
            # subscribe to command topic
            mqtt_command_topic = mqtt_topic_prefix+"/"+str(reg[i][6])+"/"+str(reg[i][5])+"/command"
            client.subscribe(mqtt_command_topic)

            # update state topic
            mqtt_state_topic = mqtt_topic_prefix+"/"+str(reg[i][6])+"/"+str(reg[i][5])+"/state"
            logger.debug("state_topic - "+mqtt_state_topic)
            logger.debug("Register Array - "+str(reg[i]))
            value = instr.read_register(reg[i][0],reg[i][1],reg[i][3],True)
            logger.debug("Value: "+str(value))

            if reg[i][5] == 'wp_soll-temp_zone1':
                value = value + 0.5
                logger.debug("Value: "+str(value))

            client.publish(mqtt_state_topic,str(value),qos=0,retain=True)

            logger.info(str(reg[i][7]).ljust(35)+": "+str(value)+" "+str(reg[i][6]))
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

            # update availability topic
            mqtt_availability_topic = mqtt_topic_prefix+"/"+str(reg[i][6])+"/"+str(reg[i][5])+"/availability"
            client.publish(mqtt_availability_topic,"online",qos=0,retain=True)

            client.publish(mqtt_topic_debug,"Subscribed to topic: "+str(mqtt_availability_topic))

        clientInfluxDB.write_points(points)

        logger.info("Closed running processes")
        lock.close()

    except Exception as e:
        logger.debug(e)
        sys.exit(2)


# when receiving a mqtt message do this;
def on_message(client, userdata, message):
    logger.debug("TEST MESSAGE")
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

    try:
        logger.info("Message received="+str(message.payload.decode("utf-8")))
        logger.info("Message topic="+str(message.topic))
        logger.info("Message qos="+str(message.qos))
        logger.info("Message retain flag="+str(message.retain))
    
        a,b,device,sub_topic = str(message.topic).split("/")
        value  = int(message.payload.decode("utf-8"))
        points = []

        # Home Assistant  -> MQTT-Topic
        # MQTT Select     -> mode
        # MQTT Switch     -> switch
        # MQTT Number     -> temp, time

        for i in range(len(reg)):
            if device == reg[i][5]:
                if reg[i][0] == 62:
                    if value == 1:
                        logger.info("Write register="+str(reg[i][0])+" Value="+str(value))
                        instr.write_register(reg[i][0], 1, reg[i][2], 6, True)
                        
                    if value == 0:
                        logger.info("Write register="+str(reg[i][0])+" Value="+str(value))
                        instr.write_register(reg[i][0], 0, reg[i][2], 6, False)
                
                else:
                    logger.info("Write register="+str(reg[i][0])+" Value="+str(value))
                    instr.write_register(reg[i][0], value, reg[i][2], 6, reg[i][3])

                client.publish(mqtt_topic_prefix+"/"+reg[i][6]+"/"+reg[i][5]+"/state",str(value),qos=0,retain=True)
            
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

        logger.info("Closed running processes")
        lock.close()

    except Exception as e:
        logger.debug(e)
        sys.exit(2)


##### Runtime section ------------------------------------------------------------------------------------------------------------------------------------------
try:
    ##### influxDB section
    logger.info("Creating new influxDB client")
    clientInfluxDB = InfluxDBClient(influxDB_ip, influxDB_port, influxDB_user, influxDB_passwd, influxDB_db)

    ##### MQTT section
    logger.info("Creating new MQTT instance")
    client = mqtt.Client(mqtt_client_name)
    client.on_connect = on_connect
    client.on_message = on_message
    logger.info("Connection to MQTT broker")
    client.connect(mqtt_broker_address)
    logger.info("Starting loop MQTT forever")
    client.loop_forever()

except Exception as e:
    logger.error(e)
    sys.exit(2)