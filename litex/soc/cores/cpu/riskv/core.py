#
# This file is part of LiteX.
#
# Copyright (c) 2021 Yann Sionneau <yann@sionneau.net>
# SPDX-License-Identifier: BSD-2-Clause

import os

from litex import get_data_mod

from migen import *

from litex.soc.cores.cpu import CPU, CPU_GCC_TRIPLE_RISCV32
from litex.soc.interconnect import wishbone

# Variants -----------------------------------------------------------------------------------------

CPU_VARIANTS = {
    "standard": "riskv_standard_wb"
}

SOURCES = [
    "cpu.v",
    "decode.v"
]

class Riskv(CPU):
    family               = "riscv"
    name                 = "riskv"
    human_name           = "Risk.v"
    variants             = CPU_VARIANTS
    data_width           = 32
    endianness           = "little"
    gcc_triple           = CPU_GCC_TRIPLE_RISCV32
    linker_output_format = "elf32-littleriscv"
    nop                  = "nop"
    io_regions           = {0x80000000: 0x80000000} # Origin, Length.

    def __init__(self, platform, variant="standard"):
        self.platform         = platform
        self.variant          = variant
        self.human_name       = "Risk.v"
        self.reset            = Signal()
        self.ibus             = ibus = wishbone.Interface()
        self.dbus             = dbus = wishbone.Interface()
        self.periph_buses     = [ibus, dbus] # Peripheral buses (Connected to main SoC's bus).
        self.memory_buses     = []           # Memory buses (Connected directly to LiteDRAM).

        # CPU Instance.
        self.cpu_params = dict(
            i_clk=ClockSignal("sys"),
            i_reset=ResetSignal("sys") | self.reset,

            o_iBusWishbone_ADR=ibus.adr,
            o_iBusWishbone_SEL=ibus.sel,
            o_iBusWishbone_CYC=ibus.cyc,
            o_iBusWishbone_STB=ibus.stb,
            i_iBusWishbone_DAT_MISO=ibus.dat_r,
            i_iBusWishbone_ACK=ibus.ack,
            i_iBusWishbone_ERR=ibus.err,

            o_dBusWishbone_ADR=dbus.adr,
            o_dBusWishbone_DAT_MOSI=dbus.dat_w,
            o_dBusWishbone_SEL=dbus.sel,
            o_dBusWishbone_CYC=dbus.cyc,
            o_dBusWishbone_STB=dbus.stb,
            o_dBusWishbone_WE=dbus.we,
            i_dBusWishbone_DAT_MISO=dbus.dat_r,
            i_dBusWishbone_ACK=dbus.ack,
            i_dBusWishbone_ERR=dbus.err
        )

    # GCC Flags.
    @property
    def gcc_flags(self):
        flags =  "-march=rv32i "
        flags += "-mabi=ilp32 "
        flags += "-D__riskv__ "
        return flags

    @staticmethod
    def add_sources(platform, variant="standard"):
        global SOURCES
        SOURCES += [CPU_VARIANTS[variant] + ".v"]
        vdir = get_data_mod("cpu", "riskv").data_location
        for source in SOURCES:
            platform.add_source(os.path.join(vdir, source))
        platform.add_verilog_include_path(vdir)

    def set_reset_address(self, reset_address):
        assert not hasattr(self, "reset_address")
        self.reset_address = reset_address
        self.cpu_params.update(i_externalResetVector=Signal(32, reset=reset_address))

    def do_finalize(self):
        self.add_sources(self.platform, self.variant)
        self.specials += Instance("Riskv", **self.cpu_params)