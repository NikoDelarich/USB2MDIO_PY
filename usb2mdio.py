#!/usr/bin/env python3

# MIT License

# Copyright (c) 2022 Wesley Becker

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Ideas/TODO:
# Use files for verbose dump of registers: represent as class/structure like Basic_Control_Reg.Master_!Slave
#     Maybe we could use the format/code from Unix drivers...?
#     Maybe the same as for C?
# 0. Accept commands and parse them (COM connect)
# 1. COM connect and RW COM port
# 2. Get USB2MDIO sequences for write/read

import sys
import serial
import re


help_str = """
Connect to serial invoking the script like so (baudrate = 9600):
    python3 usb2mdio.py <com_port>
or, make the file executable (chmod +x usb2mdio.py) and use
    ./usb2mdio.py <com_port>

After connected:
Configure PHY access:
    Show current config:
        config
    PHY address chosen with:
        config phy <phy_address>
    Extended register mode chosen with:
        config ext <yes/no, y/n, Y/N, YES/NO>

Write register:
    <reg> <value>
Only HEX values for now...

Read register with:
    <reg>
Only HEX values for now...

Show board verbose:
    info

Dump registers with (WIP):
    dump <start_reg> <end_reg>

Execute a script (either in TI's of usb2mdio_py's own format) with:
    script <path>

For more information check https://github.com/AvatarBecker/USB2MDIO_PY
"""

# ---------- Function definitions ----------

# TODO: make it a config class, with description, name, and value. Easens pretty print and feedback on change.
phy_addr = 0x01
ext = '*'  # extended registers. Yes: '*', No: '='
ext_dict = {
    '*': 'yes',
    '=': 'no'
}

# ---------- Function definitions ----------

def GetFirstString(str_list):
    if(str_list):
        return str_list[0]
    else:
        return ''

def PrintRaw(str):
    for char in str:
        print(hex(ord(char)), end=' ')
    print()

def ReadBackReg(addr):
    pkt_reply = com_port.read(5)  # 4 value chars + 0x0a as delimiter character
    #PrintRaw(pkt_reply.decode('utf-8'))
    if(pkt_reply[4] == 0x0a):
        data_str = pkt_reply[0:4].decode('utf-8')
        if(data_str):
            print('0x', data_str, sep='')
            #PrintRaw(data_str)
            #data = int(pkt_reply[0:4], 16)
        else:
            print("No reply...")
    else:
        print("Invalid reply...")

def WriteReg(com_port, phy_addr, addr, value, ext):
    # flush input (board keeps seding verbose)
    #com_port.reset_input_buffer() # too slow

    # assemble COM message
    pkt_request = f'{phy_addr:02x}{addr:04x}{value:04x}'+ext+'/'
    #print(pkt_request+': ', end='')
    #PrintRaw(pkt_request)
    pkt_request = pkt_request.encode('utf-8')

    # write it
    com_port.write(pkt_request)

    # read back value and print it
    print("wr reg 0x", f'{addr:04x}', ": ",  sep='', end='')
    ReadBackReg(addr)

def ReadReg(com_port, phy_addr, addr, ext):
    
    # flush input (board keeps seding verbose)
    #com_port.reset_input_buffer() # too slow

    # assemble COM message
    pkt_request = f'{phy_addr:02x}{addr:04x}'+ext+'/'
    #print(pkt_request+': ', end='')
    #PrintRaw(pkt_request)
    pkt_request = pkt_request.encode('utf-8')

    # write it
    com_port.write(pkt_request)

    print("rd reg 0x", f'{addr:04x}', ": ", sep='', end='')
    ReadBackReg(addr)

def ReadCleanLine(file):
    line = file.readline()
    line = GetFirstString(line.split('//',1))
    cmd = line.split()
    repr(cmd)

    return cmd

def RwRegs(cmd, len_cmd):
    # Get ADDR
    try:
        addr = int(cmd[0], 16)
    except ValueError:
        print("Invalid command...")
        return

    # Get VALUE (if any)
    if(len_cmd == 2):
        try:
            value = int(cmd[1], 16)
            WriteReg(com_port, phy_addr, addr, value, ext)
        except ValueError:
            print("Invalid value...")
            return
    elif(len_cmd == 1):
        ReadReg(com_port, phy_addr, addr, ext)
    else:
        print('Wrong number of args...')

def Config(usr_data, len_usr_data):

    global phy_addr
    global ext
    global ext_dict

    if(len_usr_data == 3):
        if(usr_data[1] == "phy"):
            try:
                phy_addr = int(usr_data[2], 16)
                print("PHY addr = 0x"+f'{phy_addr:02x}')
            except ValueError:
                print("Invalid PHY address...")
                return
        elif(usr_data[1] == "ext"):
            try:
                if(usr_data[2] in ('yes', 'y', 'YES', 'Y')):
                    ext = '*'
                elif(usr_data[2] in ('no', 'n', 'NO', 'n')):
                    ext = '='
                print("Extended register mode: "+ext_dict[ext])
            except ValueError:
                print("Invalid Ext mode...")
                return
    else:
        print("MDIO PHY addr = 0x"+f'{phy_addr:02x}')
        print("Extended register mode: "+ext_dict[ext])

def ExecScriptTi(file):   # file: file handler of the opened file

    bad_fmt_str = 'Bad file format. '

    conts = file.read()
    conts = re.split('\n|\r|\n\r|\r\n', conts)

    cmds = []

    for i in range(0,len(conts)):
        temp = conts[i].split('//',1)[0]
        if(temp != ''):
            cmds.append(temp)


    if('begin' in cmds[:1] and 'end' in cmds[-1:]):
        # All good, treat commands
        
        # strip 'begin' and 'end'
        del cmds[:1]
        del cmds[-1:]

        for cmd in cmds:
            cmd = cmd.split()
            len_cmd = len(cmd)

            if(cmd[0] == "config"):
                Config(cmd, len_cmd)

            elif(cmd[0] == "script"):
                try:
                    path = cmd[1]
                    print("Reading file:" + path )

                    other_file = open(path, 'r')
                    ExecScriptTi(other_file)
                    other_file.close()
                except FileNotFoundError:
                    print("Invalid file or file path...")
                    return
            else:
                RwRegs(cmd, len_cmd)

    else:
        # Wrong format, abort
        print(bad_fmt_str)
        return

# ---------- Check arguments ----------
if(len(sys.argv)==1):
    print(help_str)
    quit()
elif(sys.argv[1] == "--help" or sys.argv[1] == "-h"):
    print(help_str)
    quit()
elif(len(sys.argv)==2):
    # ---------- Open COM Port ----------
    com_port = serial.Serial(sys.argv[1], 9600, timeout=1)

    # ---------- Read board verbose ----------
    board_verbose = bytearray(b'')
    while(1):
        temp_data = com_port.read(350)
        board_verbose.extend(temp_data)
        if(not temp_data):
            break

    # ---------- Parse user inputs ----------
    while(1):
        usr_data_raw = input("> ")

        usr_data = usr_data_raw.split()
        len_usr_data = len(usr_data)

        if(len_usr_data==0):
            continue

        elif(usr_data[0] == "script"):
            try:
                path = usr_data[1]
                print("read file (WIP):" + path )
            except FileNotFoundError:
                print("Invalid file or file path...")
                continue
        elif(usr_data[0] == "script_ti"):
            try:
                path = usr_data[1]
                print("Reading file:" + path )

                file = open(path, 'r')
                ExecScriptTi(file)
                file.close()
            except FileNotFoundError:
                print("Invalid file or file path...")
                continue
        elif(usr_data[0] == "info"):
            if(board_verbose):
                print(board_verbose.decode('utf-8'))
            else:
                print("Board didn't send any info (verbose)...")
        elif(usr_data[0] == "config"):
            Config(usr_data, len_usr_data)

        elif(usr_data[0] in ("exit", "exit()", "quit", "quit()")):
            com_port.close()
            quit()
        elif(usr_data[0] in ("help", "--help", "h", "-h", "?")):
            print(help_str)

        # ---------- R/W Registers ----------
        else:
            RwRegs(usr_data, len_usr_data)
            