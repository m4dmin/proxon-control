#!/usr/bin/env python3
import minimalmodbus
import serial

instr = minimalmodbus.Instrument("/dev/ttyUSB0", 41)
instr.serial.baudrate = 19200 
instr.serial.bytesize = 8
instr.serial.parity   = minimalmodbus.serial.PARITY_EVEN
instr.serial.stopbits = 1
instr.serial.timeout  = 0.05

#Read Holding Register # FC4 = 3
print(instr.read_register(62,0,3,True))  # < bevorzugt
print(instr.read_registers(62,1,3)) 

#Read Input Register   # FC3 = 4
print(instr.read_register(23,0,4,True))  # < bevorzugt
print(instr.read_registers(23,1,4)) 

#Write Holding Register
instr.write_register(62, 0, 0, 6, True)