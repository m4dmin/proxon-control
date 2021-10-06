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


############### init section ###############

##### config section
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
mqtt_client_name = str(socket.gethostname()+"."str(sys.argv[0]))
mqtt_topic_prefix = "/proxon

print("mqtt_client_name: "+str(mqtt_client_name)) #!!!!! löschen

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
    sys.exit(1)

##### Array with JSON data for influxDB write
points = []

##### Array with Modbus registers
reg =  [[  16, 0, True, 'wp_modus_betriebsart', 'mode', 'Betriebsart'], # 0=Aus, 1=EcoSommer, 2=EcoWinter, 3=Komfort
        [  62, 0, '', 'wp_on-off_kuehlung', 'switch', 'Kühlung an/aus'], # 0=Aus, 1=An
        [  70, 1, True, 'wp_soll-temp_zone1', 'C', 'Wohnen  (Zone1) Soll-Temperatur'], # 100 - 295  ##-0,5 Abweichung zur Anzeige in der Anlage
        [  75, 1, True, 'wp_soll-temp_zone2', 'C', 'Büro KG (Zone2) Soll-Temperatur'], # 100 - 295
        [ 133, 0, True, 'wp_restzeit_intensivlueftung', 'min', 'Intensivlüftung Restzeit'], # 0 - 1440
        [2001, 0, True, 't300_on-off_heizstab', 'switch', 'Heizstab an/aus'], # 0=Aus, 1=An
        [2000, 1, True, 't300_soll-temp_wasser', 'C', 'Wasser Soll-Temperatur'], #450 - 600
        [2003, 1, True, 't300_schwelle-temp_wasser', 'C', 'Wasser Temperatur-Schwelle Heizstab']] #400 - 500


############### MQTT section ##################

# when connecting to mqtt do this;
def on_connect(client, userdata, flags, rc):
    logger.info("Connected with result code "+str(rc))
    client.publish(topic_debug,"Devive "+str(client_name)+" connected")
    i = 1
    while i <= anzSwitch:
        client.subscribe(topic_command[i])
        client.publish(topic_availability[i],"online",qos=0,retain=True)
        i = i + 1


# when receiving a mqtt message do this;
def on_message(client, userdata, message):
    logger.info("Message received="+str(message.payload.decode("utf-8")))
    logger.info("Message topic="+str(message.topic))
    logger.info("Message qos="+str(message.qos))
    logger.info("Message retain flag="+str(message.retain))
    
    a,b,c,switch,d = str(message.topic).split("/")
    instruction  = str(message.payload.decode("utf-8"))

    # 433MHz
    if instruction == "ON":
        client.publish(topic_state[int(switch)],"ON",qos=0,retain=True)
        rfdevice.tx_code(switchcode[int(switch)][0], 1, 500)
        time.sleep(1)
        rfdevice.tx_code(switchcode[int(switch)][0], 1, 500)
        logger.info("Switch"+switch+" ON")
    if instruction == "OFF":
        client.publish(topic_state[int(switch)],"OFF",qos=0,retain=True)
        rfdevice.tx_code(switchcode[int(switch)][1], 1, 500)
        time.sleep(1)
        rfdevice.tx_code(switchcode[int(switch)][1], 1, 500)
        logger.info("Switch"+switch+" OFF")




instr.write_register(75, 190, 1, 6, True)
print("Soll Temp Zone KG: "+str(instr.read_register(75,2,3,True)))



############### logging section ###############
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


############### Runtime section ##################


logger.info("Creating new instance")
client = mqtt.Client(client_name)
client.on_connect = on_connect
client.on_message = on_message
logger.info("Connection to broker")
client.connect(broker_address)
logger.info("Starting loop forever")
client.loop_forever()


##### Proxon section
try:
    logger.debug("0000 - Starte Lesevorgang")

    for i in range(len(reg)):
        logger.debug("Register Array - "+str(reg[i]))

        value = instr.read_register(reg[i][0],reg[i][1],reg[i][2],True)
        logger.debug("Value: "+str(value))

        if reg[i][3] == 'wp_soll-temp_zone1':
            value = value + 0.5
            logger.debug("Value: "+str(value))

        if reg[i][3] == 't300_temp_wasser':
            value = value - 100
            logger.debug("Value: "+str(value))

        

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

except Exception as e:
    logger.error(e)
    sys.exit(1)


##### influxDB section
try:
    clientInfluxDB = InfluxDBClient(influxDB_ip, influxDB_port, influxDB_user, influxDB_passwd, influxDB_db)
    clientInfluxDB.write_points(points)
except Exception as e:
    logger.error(e)
    sys.exit(1)