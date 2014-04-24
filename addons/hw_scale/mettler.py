#!/usr/bin/python
import serial
import time
import sys
from bitstring import BitArray

path = "/dev/serial/by-id/usb-METTLER_TOLEDO_15_kg_DI_Firmware_CKOR_F_Ser_CDC-if00"

device = serial.Serial(path,
        baudrate = 9600, 
        bytesize = serial.SEVENBITS, 
        stopbits = serial.STOPBITS_ONE, 
        parity   = serial.PARITY_EVEN, 
        #xonxoff  = serial.XON,
        timeout  = 0.1, 
        writeTimeout= 0.1)

if len(sys.argv) == 1:
    cmd = 'weight'
else:
    cmd = sys.argv[1]

def write(stuff):
    print stuff
    device.write(stuff)

def read_answer():
    answer = []
    while True:
        char = device.read(1)
        if not char:
            return answer
        else:
            answer.append(char)

def print_answer(answer):
    print answer
    if '?' in answer:
        status = answer[answer.index('?')+1]
        print 'status_bits: '+BitArray(int=ord(status),length=8).bin
    

if cmd == 'weight':
    while True:
        time.sleep(0.25)
        write('W')
        time.sleep(0.25)
        print_answer(read_answer())

if cmd == 'interactive':
    weight = 0
    status = ''
    while True:
        time.sleep(0.25)
        device.write('W')
        answer = read_answer()
        if '?' in answer:
            oldstatus = status
            b = answer[answer.index('?')+1]
            if b == '\x00' or b == ' ':
                pass # ignore status
            elif b == 'B':
                status = 'too_heavy'
            elif b == 'D':
                status = 'negative'
            elif b == 'A' or b == 'Q' or b == '\x01':
                status = 'moving'
            else:
                status = 'unknown'
                print b.__repr__(), BitArray(int=ord(b),length=8).bin
            if oldstatus != status:
                print status
        else:
            oldweight = weight
            answer = answer[1:-1]
            if 'N' in answer:
                answer = answer[0:-1]
            weight = float(''.join(answer))
            if oldweight != weight:
                print weight


elif cmd == 'zero':
    time.sleep(1)
    write('Z')
    time.sleep(1)
    print_answer(read_answer())

elif cmd == 'test':
    time.sleep(1)
    write('A')
    time.sleep(1)
    write('B')
    time.sleep(1)
    answer = read_answer()
    if '@' in answer:
        print 'all test passed'
    else:
        print_answer(answer)
    
