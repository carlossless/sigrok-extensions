import sigrokdecode as srd

# ICP command definitions
ICP_COMMANDS = {
    0x40: 'SET_OFFSET_L',
    0x41: 'SET_OFFSET_H',
    0x42: 'SET_DATA',
    0x43: 'GET_OFFSET',
    0x44: 'READ_FLASH',
    0x49: 'PING',
    0x4A: 'READ_CUSTOM',
    0x4C: 'SET_XPAGE',
    0x6E: 'WRITE_FLASH',
    0xA5: 'WRITE_CUSTOM',
}

# Mode byte definitions
MODE_ICP = 150
MODE_JTAG = 165

class ChannelError(Exception):
    pass

class Decoder(srd.Decoder):
    api_version = 3
    id = 'sinowealth-icp'
    name = 'SinoWealth-ICP'
    longname = 'SinoWealth In-Circuit Programming'
    desc = 'SinoWealth 8051 ICP protocol (9-clock per byte).'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = ['sinowealth-icp']
    tags = ['Embedded/industrial']
    channels = (
        {'id': 'tck', 'type': 0, 'name': 'TCK', 'desc': 'Test Clock', 'idn':'dec_sinowealth_icp_chan_tck'},
        {'id': 'tdi', 'type': -1, 'name': 'TDI', 'desc': 'Test Data In (to target)', 'idn':'dec_sinowealth_icp_chan_tdi'},
    )
    optional_channels = (
        {'id': 'tdo', 'type': -1, 'name': 'TDO', 'desc': 'Test Data Out (from target)', 'idn':'dec_sinowealth_icp_opt_chan_tdo'},
        {'id': 'tms', 'type': -1, 'name': 'TMS', 'desc': 'Test Mode Select', 'idn':'dec_sinowealth_icp_opt_chan_tms'},
    )
    annotations = (
        ('108', 'tdi-data', 'TDI data'),
        ('106', 'tdo-data', 'TDO data'),
        ('110', 'tdi-cmd', 'TDI command'),
        ('1000', 'warning', 'Warning'),
        ('7', 'sync', 'Sync clock'),
    )
    annotation_rows = (
        ('tdi-data', 'TDI data', (0,)),
        ('tdi-cmds', 'TDI commands', (2,)),
        ('tdo-data', 'TDO data', (1,)),
        ('sync', 'Sync', (4,)),
        ('warnings', 'Warnings', (3,)),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.samplerate = None
        self.bitcount = 0
        self.tdi_data = 0
        self.tdo_data = 0
        self.ss_byte = -1
        self.samplenum = -1
        self.have_tdo = None
        self.have_tms = None
        self.in_sync = False
        self.last_tck_sample = -1

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value

    def put_tdi(self, ss, es, data):
        self.put(ss, es, self.out_ann, [0, ['@%02X' % data]])

    def put_tdo(self, ss, es, data):
        self.put(ss, es, self.out_ann, [1, ['@%02X' % data]])

    def put_cmd(self, ss, es, cmd_byte):
        cmd_name = ICP_COMMANDS.get(cmd_byte, None)
        if cmd_name:
            self.put(ss, es, self.out_ann, [2, ['%s (0x%02X)' % (cmd_name, cmd_byte), cmd_name, cmd_name[:3]]])

    def put_sync(self, ss, es):
        self.put(ss, es, self.out_ann, [4, ['SYNC', 'S']])

    def put_warning(self, ss, es, msg):
        self.put(ss, es, self.out_ann, [3, [msg]])

    def handle_bit(self, tdi, tdo, tck):
        # First 8 clock pulses: data bits (MSB first)
        if self.bitcount < 8:
            if self.bitcount == 0:
                self.ss_byte = self.samplenum
                self.tdi_data = 0
                self.tdo_data = 0

            # TDI: MSB first
            self.tdi_data = (self.tdi_data << 1) | tdi

            # TDO: sample if available (LSB first based on firmware)
            if self.have_tdo:
                self.tdo_data = self.tdo_data | (tdo << self.bitcount)

            self.bitcount += 1

        # 9th clock pulse: sync clock
        elif self.bitcount == 8:
            es = self.samplenum

            # Output the byte annotations
            self.put_tdi(self.ss_byte, es, self.tdi_data)

            # Check if this is a command byte
            self.put_cmd(self.ss_byte, es, self.tdi_data)

            if self.have_tdo:
                self.put_tdo(self.ss_byte, es, self.tdo_data)

            # Mark sync pulse
            self.put_sync(self.samplenum, self.samplenum)

            # Reset for next byte
            self.bitcount = 0
            self.tdi_data = 0
            self.tdo_data = 0

    def decode(self):
        if not self.has_channel(0):
            raise ChannelError('TCK pin required.')
        if not self.has_channel(1):
            raise ChannelError('TDI pin required.')

        self.have_tdo = self.has_channel(2)
        self.have_tms = self.has_channel(3)

        wait_cond = [{0: 'f'}]  # Falling edge

        while True:
            (tck, tdi, tdo, tms) = self.wait(wait_cond)

            # Handle the bit/sync clock
            self.handle_bit(tdi, tdo if self.have_tdo else 0, tck)
