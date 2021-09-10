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


#instr.write_register(16, 3, 0, 6, True) # 0 - 3 #ok
#print("Betriebsart:       "+str(instr.read_register(16,0,3,True)))

#instr.write_register(62, 1, 0, 6, True) # 0, 1 #ok
#instr.write_register(62, 0, 0, 6, False) # 0, 1 #ok
#print("Kühlung:           "+str(instr.read_register(62,0,3,True)))

#instr.write_register(70, 195, 1, 6, True) # 100 - 295 #ok
#print("Soll Temp Zone EG: "+str(instr.read_register(70,2,3,True)))

instr.write_register(75, 190, 1, 6, True)
print("Soll Temp Zone KG: "+str(instr.read_register(75,2,3,True)))

#instr.write_register(118, 30, 0, 6, True) # 0 - 95 #ok
#print("Rel. Luftfeuchte:  "+str(instr.read_register(118,0,3,True))) 

#instr.write_register(133, 0, 0, 6, True) # 0 - 1440 #ok
#print("Intensivlüftung:   "+str(instr.read_register(133,0,3,True)))

#instr.write_register(22, 1, 0, 6, False) # 1 - 4 #ok
#print("Lüfterstufe in ECOSommer, ECOWinter: "+str(instr.read_register(22,0,3,True)))

#instr.write_register(117, 1200, 0, 6, True) #401 - 1500 #ok
#print("CO2 Schwelle: "+str(instr.read_register(117,0,3,True)))

#instr.write_register(2000, 480, 0, 6, True) #450 - 600 #ok
#print("T300 Heizstab Soll: "+str(instr.read_register(2000,1,3,True)))

#instr.write_register(2001, 0, 0, 6, True) #0 - 1 #ok
#print("T300 Heizstab an/aus: "+str(instr.read_register(2001,0,3,True)))

#instr.write_register(2003, 440, 0, 6, True) #400 - 500 #ok
#print("T300 Heizstab Schwelle: "+str(instr.read_register(2003,1,3,True)))

#instr.write_register(256, 0, 0, 6, True) #0 - 1
#print("256:        "+str(instr.read_register(256,0,3,True)))