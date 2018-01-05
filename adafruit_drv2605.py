# The MIT License (MIT)
#
# Copyright (c) 2017 Tony DiCola for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`Adafruit_DRV2605`
====================================================

CircuitPython module for the DRV2605 haptic feedback motor driver.  See
examples/simpletest.py for a demo of the usage.

* Author(s): Tony DiCola
"""
from micropython import const

from adafruit_bus_device.i2c_device import I2CDevice

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_DRV2605.git"


# pylint: disable=bad-whitespace
# Internal constants:
_DRV2605_ADDR              = const(0x5A)
_DRV2605_REG_STATUS        = const(0x00)
_DRV2605_REG_MODE          = const(0x01)
_DRV2605_REG_RTPIN         = const(0x02)
_DRV2605_REG_LIBRARY       = const(0x03)
_DRV2605_REG_WAVESEQ1      = const(0x04)
_DRV2605_REG_WAVESEQ2      = const(0x05)
_DRV2605_REG_WAVESEQ3      = const(0x06)
_DRV2605_REG_WAVESEQ4      = const(0x07)
_DRV2605_REG_WAVESEQ5      = const(0x08)
_DRV2605_REG_WAVESEQ6      = const(0x09)
_DRV2605_REG_WAVESEQ7      = const(0x0A)
_DRV2605_REG_WAVESEQ8      = const(0x0B)
_DRV2605_REG_GO            = const(0x0C)
_DRV2605_REG_OVERDRIVE     = const(0x0D)
_DRV2605_REG_SUSTAINPOS    = const(0x0E)
_DRV2605_REG_SUSTAINNEG    = const(0x0F)
_DRV2605_REG_BREAK         = const(0x10)
_DRV2605_REG_AUDIOCTRL     = const(0x11)
_DRV2605_REG_AUDIOLVL      = const(0x12)
_DRV2605_REG_AUDIOMAX      = const(0x13)
_DRV2605_REG_RATEDV        = const(0x16)
_DRV2605_REG_CLAMPV        = const(0x17)
_DRV2605_REG_AUTOCALCOMP   = const(0x18)
_DRV2605_REG_AUTOCALEMP    = const(0x19)
_DRV2605_REG_FEEDBACK      = const(0x1A)
_DRV2605_REG_CONTROL1      = const(0x1B)
_DRV2605_REG_CONTROL2      = const(0x1C)
_DRV2605_REG_CONTROL3      = const(0x1D)
_DRV2605_REG_CONTROL4      = const(0x1E)
_DRV2605_REG_VBAT          = const(0x21)
_DRV2605_REG_LRARESON      = const(0x22)

# User-facing mode value constants:
MODE_INTTRIG      = 0x00
MODE_EXTTRIGEDGE  = 0x01
MODE_EXTTRIGLVL   = 0x02
MODE_PWMANALOG    = 0x03
MODE_AUDIOVIBE    = 0x04
MODE_REALTIME     = 0x05
MODE_DIAGNOS      = 0x06
MODE_AUTOCAL      = 0x07
LIBRARY_EMPTY     = 0x00
LIBRARY_TS2200A   = 0x01
LIBRARY_TS2200B   = 0x02
LIBRARY_TS2200C   = 0x03
LIBRARY_TS2200D   = 0x04
LIBRARY_TS2200E   = 0x05
LIBRARY_LRA       = 0x06
# pylint: enable=bad-whitespace

class DRV2605:
    """TI DRV2605 haptic feedback motor driver module."""

    # Class-level buffer for reading and writing data with the sensor.
    # This reduces memory allocations but means the code is not re-entrant or
    # thread safe!
    _BUFFER = bytearray(2)

    def __init__(self, i2c, address=_DRV2605_ADDR):
        self._device = I2CDevice(i2c, address)
        # Check chip ID is 3 or 7 (DRV2605 or DRV2605L).
        status = self._read_u8(_DRV2605_REG_STATUS)
        device_id = (status >> 5) & 0x07
        if device_id not in (3, 7):
            raise RuntimeError('Failed to find DRV2605, check wiring!')
        # Configure registers to initialize chip.
        self._write_u8(_DRV2605_REG_MODE, 0x00)     # out of standby
        self._write_u8(_DRV2605_REG_RTPIN, 0x00)    # no real-time-playback
        self._write_u8(_DRV2605_REG_WAVESEQ1, 1)    # strong click
        self._write_u8(_DRV2605_REG_WAVESEQ2, 0)
        self._write_u8(_DRV2605_REG_OVERDRIVE, 0)   # no overdrive
        self._write_u8(_DRV2605_REG_SUSTAINPOS, 0)
        self._write_u8(_DRV2605_REG_SUSTAINNEG, 0)
        self._write_u8(_DRV2605_REG_BREAK, 0)
        self._write_u8(_DRV2605_REG_AUDIOMAX, 0x64)
        # Set ERM open-loop mode.
        self.use_ERM()
        # turn on ERM_OPEN_LOOP
        control3 = self._read_u8(_DRV2605_REG_CONTROL3)
        self._write_u8(_DRV2605_REG_CONTROL3, control3 | 0x20)
        # Default to internal trigger mode and TS2200 A library.
        self.mode = MODE_INTTRIG
        self.library = LIBRARY_TS2200A

    def _read_u8(self, address):
        # Read an 8-bit unsigned value from the specified 8-bit address.
        with self._device as i2c:
            self._BUFFER[0] = address & 0xFF
            i2c.write(self._BUFFER, end=1, stop=False)
            i2c.readinto(self._BUFFER, end=1)
        return self._BUFFER[0]

    def _write_u8(self, address, val):
        # Write an 8-bit unsigned value to the specified 8-bit address.
        with self._device as i2c:
            self._BUFFER[0] = address & 0xFF
            self._BUFFER[1] = val & 0xFF
            i2c.write(self._BUFFER, end=2)

    def play(self):
        """Play back the select effect(s) on the motor."""
        self._write_u8(_DRV2605_REG_GO, 1)

    def stop(self):
        """Stop vibrating the motor."""
        self._write_u8(_DRV2605_REG_GO, 0)

    @property
    def mode(self):
        """Get and set the mode of the chip.  Should be a value of:
          - MODE_INTTRIG: Internal triggering, vibrates as soon as you call
            play().  Default mode.
          - MODE_EXTTRIGEDGE: External triggering, edge mode.
          - MODE_EXTTRIGLVL: External triggering, level mode.
          - MODE_PWMANALOG: PWM/analog input mode.
          - MODE_AUDIOVIBE: Audio-to-vibration mode.
          - MODE_REALTIME: Real-time playback mode.
          - MODE_DIAGNOS: Diagnostics mode.
          - MODE_AUTOCAL: Auto-calibration mode.
        See the datasheet for the meaning of modes beyond MODE_INTTRIG.
        """
        return self._read_u8(_DRV2605_REG_MODE)

    @mode.setter
    def mode(self, val):
        assert 0 <= val <= 7
        self._write_u8(_DRV2605_REG_MODE, val)

    @property
    def library(self):
        """Get and set the library selected for waveform playback.  Should be
        a value of:
        - LIBRARY_EMPTY: Empty
        - LIBRARY_TS2200A: TS2200 library A  (the default)
        - LIBRARY_TS2200B: TS2200 library B
        - LIBRARY_TS2200C: TS2200 library C
        - LIBRARY_TS2200D: TS2200 library D
        - LIBRARY_TS2200E: TS2200 library E
        - LIBRARY_LRA: LRA library
        See the datasheet for the meaning and description of effects in each
        library.
        """
        return self._read_u8(_DRV2605_REG_LIBRARY) & 0x07

    @library.setter
    def library(self, val):
        assert 0 <= val <= 6
        self._write_u8(_DRV2605_REG_LIBRARY, val)

    def set_waveform(self, effect_id, slot=0):
        """Select an effect waveform for the specified slot (default is slot 0,
        but up to 7 effects can be combined with slot values 0 to 6).  See the
        datasheet for a complete table of effect ID values and the associated
        waveform / effect.
        """
        assert 0 <= effect_id <= 123
        assert 0 <= slot <= 6
        self._write_u8(_DRV2605_REG_WAVESEQ1 + slot, effect_id)

    # pylint: disable=invalid-name
    def use_ERM(self):
        """Use an eccentric rotating mass motor (the default)."""
        feedback = self._read_u8(_DRV2605_REG_FEEDBACK)
        self._write_u8(_DRV2605_REG_FEEDBACK, feedback & 0x7F)

    # pylint: disable=invalid-name
    def use_LRM(self):
        """Use a linear resonance actuator motor."""
        feedback = self._read_u8(_DRV2605_REG_FEEDBACK)
        self._write_u8(_DRV2605_REG_FEEDBACK, feedback | 0x80)
