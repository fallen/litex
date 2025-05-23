#
# This file is part of LiteX.
#
# Copyright (c) 2024 Yann Sionneau <yann@sionneau.net>
# SPDX-License-Identifier: BSD-2-Clause

import usb.core
import time

from litex.tools.remote.comm_uart import CMD_READ_BURST_FIXED, CMD_WRITE_BURST_FIXED
from litex.tools.remote.csr_builder import CSRBuilder

# CommHydraUSB ------------------------------------------------------------------------------------------


class CommHydraUSB(CSRBuilder):
    def __init__(self, vid=None, pid=None, ep=1, max_retries=10, csr_csv=None, debug=False):
        CSRBuilder.__init__(self, comm=self, csr_csv=csr_csv)
        self.vid         = vid
        self.pid         = pid
        self.ep          = ep
        self.debug       = debug
        self.max_retries = max_retries

    def open(self):
        if hasattr(self, "dev"):
            return
        for t in range(self.max_retries):
            args = {}
            if self.vid is not None:
                args['idVendor'] = self.vid
            if self.pid is not None:
                args['idProduct'] = self.pid
            self.dev = usb.core.find(**args)
            if self.dev is not None:
                if self.debug:
                    print("device connected after {} tries".format(t+1))
                return True
            del self.dev
            time.sleep(0.2 * t)
        print("unable to find usb device after {} tries".format(self.max_retries))
        return False


    def close(self):
        if not hasattr(self, "dev"):
            return
        del self.dev

    def read(self, addr, length=None, burst="incr"):
        assert burst == "incr"
        data = []
        #print("length: {}".format(length))
        length_int = 1 if length is None else length
        for i in range(length_int):
            read_addr = (addr + 4*i) >> 2
            uartbone_buffer = bytearray([CMD_READ_BURST_FIXED, 1])
            uartbone_buffer.extend(read_addr.to_bytes(4, byteorder="big"))
            usb_buffer = bytearray(b'Uw')
            usb_buffer.append(len(uartbone_buffer))
            usb_buffer.extend(uartbone_buffer)
            self.usb_write(usb_buffer)
            usb_buffer = bytearray(b'Ur')
            usb_buffer.append(4)
            self.usb_write(usb_buffer)
            data = self.usb_read(4)
            if data is None:
                print("au secours usb_read a retourné None!")
                return
            #print("received data: {}".format(data))
            value = int.from_bytes(data, byteorder="big")
            #print("value: {}".format(value))
            # Note that sometimes, the value ends up as None when the device
            # disconnects during a transaction.  Paper over this fact by
            # replacing it with a sentinal.
            if value is None:
                value = 0xffffffff
            if self.debug:
                print("read 0x{:08x} @ 0x{:08x}".format(value, addr + 4*i))
            if length_int == 1:
                return [value]
            data.append(value)
        return data

    def usb_read(self, len):
        for i in range(self.max_retries):
            try:
                #print("Sending EP1 OUT {}".format(len))
                data = self.dev.read(self.ep | 0x80, len)
                if data is None:
                    print("Oops data is None")
                    raise TypeError
                return data
            except usb.core.USBError as e:
                if e.errno == 13:
                    print("Access Denied. Maybe try using sudo?")
                print("usb_read error: {}".format(e))
                print("oops !!!")
                #time.sleep(0.1)
                #self.close()
                #self.open()
            except TypeError:
                print("Type error!!")
                self.close()
                self.open()

    def write(self, addr, data):
        data = data if isinstance(data, list) else [data]
        for i, value in enumerate(data):
            uartbone_buffer = bytearray()
            uartbone_buffer.extend([CMD_WRITE_BURST_FIXED, 1])
            uartbone_buffer.extend((addr >> 2).to_bytes(4, byteorder="big"))
            uartbone_buffer.extend(value.to_bytes(4, byteorder="big"))
            usb_buffer = bytearray(b'Uw')
            usb_buffer.append(len(uartbone_buffer))
            usb_buffer.extend(uartbone_buffer)
            self.usb_write(usb_buffer)
            if self.debug:
                print("write 0x{:08x} @ 0x{:08x}".format(value, addr + 4*i))

    def usb_write(self, data):
        for i in range(self.max_retries):
            #print("Sending data to EP1 OUT: {}".format(data))
            try:
                self.dev.write(self.ep, data, timeout=None)
                return
            except usb.core.USBError as e:
                if e.errno == 13:
                    print("Access Denied. Maybe try using sudo?")
                #print("usb_write error: {}".format(e))
                #time.sleep(0.1)
                #self.close()
                #self.open()
