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
import ast


##### init section ------------------------------------------------------------------------------------------------------------------------------------------

##### logging section
try:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # create a file handler
    handler = RotatingFileHandler('../log/mqtt_write_to_proxon_and_db.log', maxBytes=10*1024*1024, backupCount=2)
    handler.setLevel(logging.DEBUG)

    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(handler)

    # logging examples
    # logger.debug("Debug Log")
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
    # - write_register(registeraddress: int, value: Union[int, float], number_of_decimals: int = 0, functioncode: int = 16, signed: bool = False)
    # - read_register(registeraddress: int, number_of_decimals: int = 0, functioncode: int = 3, signed: bool = False)
    reg_list = ast.literal_eval(config.get('modbus', 'register'))
    reg = []
    for i in range(len(reg_list)):
        if reg_list[i][3] == 3:
            reg.append(reg_list[i])

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
    sys.exit(2)


##### MQTT section ------------------------------------------------------------------------------------------------------------------------------------------

# handling disconnects
def on_disconnect(client, userdata, rc):
    logging.debug("MQTT on_disconnect - DISCONNECT REASON: "+str(rc))
    mqttc.connected_flag=False
    mqttc.disconnect_flag=True

# when connecting to mqtt do this;
def on_connect(client, userdata, flags, rc):
    logger.debug("MQTT on_connect - CONNECT")
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
        mqttc.publish(mqtt_topic_debug,"Devive "+str(mqtt_client_name)+" connected with result code "+str(rc))

        points = []

        for i in range(len(reg)):
            if reg[i][2] != '':
                # subscribe to command topic
                mqtt_command_topic = mqtt_topic_prefix+"/"+str(reg[i][6])+"/"+str(reg[i][5])+"/command"
                mqttc.subscribe(mqtt_command_topic)
                mqttc.publish(mqtt_topic_debug,"Subscribed to topic: "+str(mqtt_command_topic))
                logger.info("Subscribed to command-topic: "+str(mqtt_command_topic))

                # update availability topic
                mqtt_availability_topic = mqtt_topic_prefix+"/"+str(reg[i][6])+"/"+str(reg[i][5])+"/availability"
                mqttc.publish(mqtt_availability_topic,"online",qos=2,retain=True)
                logger.info("Upated availability-topic: "+str(mqtt_availability_topic))


        clientInfluxDB.write_points(points)

        logger.info("Closed running processes")
        lock.close()

    except Exception as e:
        logger.debug(e)
        sys.exit(2)


# when receiving a mqtt message do this;
def on_message(client, userdata, message):
    logger.debug("MQTT on_message - MESSAGE")
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
        logger.debug("Message received="+str(message.payload.decode("utf-8")))
        logger.debug("Message topic="+str(message.topic))
        logger.debug("Message qos="+str(message.qos))
        logger.debug("Message retain flag="+str(message.retain))
    
        a,b,device,sub_topic = str(message.topic).split("/")
        value  = float(message.payload.decode("utf-8"))
        points = []

        # Home Assistant  -> MQTT-Topic
        # MQTT Select     -> mode
        # MQTT Switch     -> switch
        # MQTT Number     -> temp, min

        for i in range(len(reg)):
            if device == reg[i][5]:
                if reg[i][5] == 'wp_soll-temp_zone1':
                    value = (value - 0.5)
                
                if reg[i][6] == 'temp':
                    valueDB = float(value)
                    value = value * 10

                if reg[i][6] == 'mode' or reg[i][6] == 'switch' or reg[i][6] == 'level' or reg[i][6] == 'min':
                    valueDB = int(value)
                
                if reg[i][0] == 62:
                    if value == 1:
                        instr.write_register(reg[i][0], int(value), reg[i][2], 6, True)
                    if value == 0:
                        instr.write_register(reg[i][0], int(value), reg[i][2], 6, False)
                else:
                    instr.write_register(reg[i][0], int(value), reg[i][2], 6, reg[i][3])

                logger.info("Write register="+str(reg[i][0])+" Value="+str(value))

                mqttc.publish(mqtt_topic_prefix+"/"+reg[i][6]+"/"+reg[i][5]+"/state",str(valueDB),qos=2,retain=True)
            
                logger.info(str(reg[i][7]).ljust(35)+": "+str(valueDB)+" "+str(reg[i][6]))
                point = {
                    "measurement": str(reg[i][5]),
                    "tags": {
                        "instance": influxDB_tag_instance,
                        "source": influxDB_tag_source
                    },
                    #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
                    "fields": {
                        str(reg[i][6]): valueDB
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
    clientInfluxDB = InfluxDBClient(influxDB_ip, influxDB_port, influxDB_user, influxDB_passwd, influxDB_db)
    logger.info("Created new influxDB client")

    ##### MQTT section
    mqttc = mqtt.Client(mqtt_client_name, True, None, mqtt.MQTTv31)
    mqttc.enable_logger(logger)
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect
    mqttc.on_message = on_message
    logger.info("Created new MQTT client: "+mqtt_client_name)

    mqttc.connect(mqtt_broker_address)
    logger.info("Connected to MQTT broker: "+mqtt_broker_address)

    logger.info("Starting MQTT loop forever")
    mqttc.loop_forever()

except Exception as e:
    logger.error(e)
    sys.exit(2)