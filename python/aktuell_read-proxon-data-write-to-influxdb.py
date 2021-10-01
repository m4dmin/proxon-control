#!/usr/bin/env python3

import time
import datetime
import configparser
import logging
from logging.handlers import RotatingFileHandler
import minimalmodbus
import serial
#import requests
#import sys
import json
from influxdb import InfluxDBClient


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

serial_port = config['serial']['port']

##### Proxon section
try:
    instr = minimalmodbus.Instrument("/dev/ttyUSB0", 41)
    instr.serial.baudrate = 19200 
    instr.serial.bytesize = 8
    instr.serial.parity   = minimalmodbus.serial.PARITY_EVEN
    instr.serial.stopbits = 1
    instr.serial.timeout  = 0.05
except Exception as e:
    logger.debug(e)

##### Array with JSON data for influxDB write
points = []

##### Array with Modbus registers
        #Read Holding Register # FC4 = 3
reg =  [[  16, 0, 3, 'wp_modus_betriebsart' ,'Betriebsart'],
        [  62, 0, 3, 'wp_on-off_kuehlung' ,'Kühlung an/aus'],
        [  70, 2, 3, 'wp_soll-temp_zone1' ,'Wohnen  (Zone1) Soll-Temperatur'],
        [  75, 2, 3, 'wp_soll-temp_zone2' ,'Büro KG (Zone2) Soll-Temperatur'],
        [ 133, 0, 3, 'wp_restzeit_intensivlueftung' ,'Intensivlüftung Restzeit'],
        [2001, 0, 3, 't300_on-off_heizstab' ,'Heizstab an/aus'],
        [2000, 1, 3, 't300_soll-temp_wasser' ,'Wasser Soll-Temperatur'],
        [2003, 1, 3, 't300_schwelle-temp_wasser' ,'Wasser Temperatur-Schwelle Heizstab'],
        #Read Input Register   # FC3 = 4
        [ 814, 1, 4, 't300_temp_wasser' ,'Wasser Temperatur'],
        [  41, 2, 4, 'wp_temp_zone1' ,'Wohnen  (Zone1) Temperatur'],
        [  40, 2, 4, 'wp_temp_zone2' ,'Büro KG (Zone2) Temperatur'],
        [ 593, 1, 4, 'wp_temp_kochen' ,'Kochen Temperatur'],
        [ 596, 1, 4, 'wp_temp_diele' ,'Diele Temperatur'],
        [ 599, 1, 4, 'wp_temp_buero-eg' ,'Büro EG Temperatur'],
        [ 602, 1, 4, 'wp_temp_schalfen' ,'Schlafen Temperatur'],
        [ 605, 1, 4, 'wp_temp_martha' ,'Martha Temperatur'],
        [ 608, 1, 4, 'wp_temp_marlene' ,'Marlene Temperatur'],
        [ 614, 1, 4, 'wp_temp_keller2' ,'Keller 2 Temperatur'],
        [ 617, 1, 4, 'wp_temp_keller3' ,'Keller 3 Temperatur'],
        [ 154, 0, 4, 'wp_stufe_ventilator-zuluft' ,'Ventilator Zuluft Lüftungsstufe']]    


############### logging section ###############
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# create a file handler
handler = RotatingFileHandler('../log/aktuell_read-proxon-data-write-to-influxdb.log', maxBytes=10*1024*1024, backupCount=2)
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

##### Proxon section
try:
    logger.debug("0000 - Starte Lesevorgang")

    for i in range(len(reg)):



        logger.debug("Register "+str(i)+" einlesen")
        sz_responseByte = ser.readline()
        logger.debug(sz_responseByte)
        sz_responseString = sz_responseByte.decode("utf-8").rstrip('\r\n')

        # sz_leistung_aktuell
        if sz_responseString[0:len(sz_leistung_aktuell)] == sz_leistung_aktuell:
            sz_responseStripped = sz_responseString.replace(sz_leistung_aktuell,"")
            sz_responseStripped = sz_responseStripped.replace("(","")
            sz_responseStripped = sz_responseStripped.replace("*kW)","")
            sz_responseStrippedW = float(sz_responseStripped)*1000
            sz_actW = sz_responseStrippedW
            logger.info("SZ Leistung aktuell: "+str(sz_actW))
            point = {
                "measurement": 'sz_leistung_aktuell',
                "tags": {
                    "instance": influxDB_tag_instance,
                    "source": influxDB_tag_source
                },
                #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
                "fields": {
                    "W": sz_responseStrippedW
                    }
                }
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