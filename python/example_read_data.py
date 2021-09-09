#!/usr/bin/env python3


import minimalmodbus
import serial


############### init section ###############

instr = minimalmodbus.Instrument("/dev/ttyUSB0", 41)
instr.serial.baudrate = 19200 
instr.serial.bytesize = 8
instr.serial.parity   = minimalmodbus.serial.PARITY_EVEN
instr.serial.stopbits = 1
instr.serial.timeout  = 0.05

#Read Holding Register # FC4 = 3
print("-- Holding Register")
print("Betriebsart:       "+str(instr.read_register(16,0,3,True))) #ok
print("Kühlung:           "+str(instr.read_register(62,0,3,True))) #ok
print("Soll Temp Zone EG: "+str(instr.read_register(70,2,3,True))) #ok, aber Abweichung um -0,5 Grad
print("Soll Temp Zone KG: "+str(instr.read_register(75,2,3,True))) # !!!
print("Rel. Luftfeuchte:  "+str(instr.read_register(118,0,3,True))) #ok
print("Intensivlüftung:   "+str(instr.read_register(133,0,3,True))) #ok in Minuten
print("Stunden FWT an:    "+str(instr.read_register(467,0,3,True))) #ok, aber erhöht sich alle 2 Stunden um 1 (muss als mit 2 multipliziert werden)
print("Gerätefilter standzeit: "+str(instr.read_register(460,0,3,True))) #ok
print("Gerätefilter Stunden:   "+str(instr.read_register(469,0,3,True))) #ok, aber erhöht sich alle 2 Stunden um 1 (muss als mit 2 multipliziert werden)
print("Lüfterstufe in ECOSommer, ECOWinter: "+str(instr.read_register(22,0,3,True))) #ok
print("Wärmepumpe kühlung schwelle: "+str(instr.read_register(41,2,3,True))) #ok
print("Wärmepumpe einschalt schwelle: "+str(instr.read_register(42,2,3,True))) #ok
print("Wärmepumpe Betriebsart: "+str(instr.read_register(69,0,3,True))) #vllt. ok
print("CO2 Schwelle: "+str(instr.read_register(117,0,3,True))) #ok

#print("T300 Warmwasser: "+str(instr.read_register(2001,1,3,True)))
#print("T300 Heizstab: "+str(instr.read_register(2002,0,3,True)))
#print("T300 Heizstab Soll: "+str(instr.read_register(2004,1,3,True)))
#print("T300 Heizstab Schwelle: "+str(instr.read_register(2003,0,3,True)))

#Read Input Register   # FC3 = 4
print("")
print("-- Input Register")
print("Power Total:                 "+str(instr.read_register(25,0,4,True))) #vllt. ok
print("Temperatur Wohnen   (Zone1): "+str(instr.read_register(41,2,4,True))) #ok EG (wohnen)
print("Temperatur Keller 1 (Zone2): "+str(instr.read_register(40,2,4,True))) #ok KG (Keller 1)
print("Temperatur Kochen:           "+str(instr.read_register(593,1,4,True))) #ok kochen
print("Temperatur Diele:            "+str(instr.read_register(596,1,4,True))) #ok diele
print("Temperatur Büro EG:          "+str(instr.read_register(599,1,4,True))) #ok Büro EG
print("Temperatur Schlafen:         "+str(instr.read_register(602,1,4,True))) #ok Schlafen
print("Temperatur Martha:           "+str(instr.read_register(605,1,4,True))) #ok martha
print("Temperatur Marlene:          "+str(instr.read_register(608,1,4,True))) #ok marlene
print("Temperatur Keller 2:         "+str(instr.read_register(614,1,4,True))) #ok Keller 2
print("Temperatur Keller 3:         "+str(instr.read_register(617,1,4,True))) #ok Keller 3
print("Störung:                     "+str(instr.read_register(47,2,4,True))) #vllt. ok

#print("T300 Warmwasser:             "+str(instr.read_register(815,1,4,True)))