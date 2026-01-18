'''
The SinoWealth-ICP (In-Circuit Programming) protocol decoder supports the
JTAG-like programming interface used by SinoWealth 8051 microcontrollers.

- Uses 9 clock pulses per byte (8 data bits + 1 sync clock)
- Four-wire interface: TCK (clock), TDI (data in), TDO (data out), TMS (mode)
- Supports ICP mode (programming) and JTAG mode (debugging)

The decoder recognizes ICP commands and displays transmitted/received data.
'''

from .pd import Decoder
