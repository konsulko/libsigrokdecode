##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2014 Torsten Duwe <duwe@suse.de>
## Copyright (C) 2014 Sebastien Bourdelin <sebastien.bourdelin@savoirfairelinux.com>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
##

import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 2
    id = 'pwm'
    name = 'PWM'
    longname = 'Pulse-width modulation'
    desc = 'Analog level encoded in duty cycle percentage.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = ['pwm']
    channels = (
        {'id': 'data', 'name': 'Data', 'desc': 'Data line'},
    )
    options = (
        {'id': 'polarity', 'desc': 'Polarity', 'default': 'active-high',
            'values': ('active-low', 'active-high')},
    )
    annotations = (
        ('duty-cycle', 'Duty cycle'),
    )
    binary = (
        ('raw', 'RAW file'),
    )

    def __init__(self, **kwargs):
        self.ss = self.es = None
        self.first_transition = True
        self.first_samplenum = None
        self.start_samplenum = None
        self.end_samplenum = None
        self.oldpin = None
        self.num_cycles = 0
        self.average = 0

    def start(self):
        self.startedge = 0 if self.options['polarity'] == 'active-low' else 1
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.out_bin = self.register(srd.OUTPUT_BINARY)
        self.out_average = \
            self.register(srd.OUTPUT_META,
                          meta=(float, 'Average', 'PWM base (cycle) frequency'))

    def putx(self, data):
        self.put(self.ss, self.es, self.out_ann, data)

    def putb(self, data):
        self.put(self.num_cycles, self.num_cycles, self.out_bin, data)

    def decode(self, ss, es, data):

        for (self.samplenum, pins) in data:
            # Ignore identical samples early on (for performance reasons).
            if self.oldpin == pins[0]:
                continue

            # Initialize self.oldpins with the first sample value.
            if self.oldpin is None:
                self.oldpin = pins[0]
                continue

            if self.first_transition:
                # First rising edge
                if self.oldpin != self.startedge:
                    self.first_samplenum = self.samplenum
                    self.start_samplenum = self.samplenum
                    self.first_transition = False
            else:
                if self.oldpin != self.startedge:
                    # Rising edge
                    # We are on a full cycle we can calculate
                    # the period, the duty cycle and its ratio.
                    period = self.samplenum - self.start_samplenum
                    duty = self.end_samplenum - self.start_samplenum
                    ratio = float(duty / period)

                    # This interval starts at this edge.
                    self.ss = self.start_samplenum
                    # Store the new rising edge position and the ending
                    # edge interval.
                    self.start_samplenum = self.es = self.samplenum

                    # Report the duty cycle in percent.
                    percent = float(ratio * 100)
                    self.putx([0, ["%f%%" % percent]])

                    # Report the duty cycle in the binary output.
                    self.putb((0, bytes([int(ratio * 256)])))

                    # Update and report the new duty cycle average.
                    self.num_cycles += 1
                    self.average += percent
                    self.put(self.first_samplenum, self.es, self.out_average,
                             float(self.average / self.num_cycles))
                else:
                    # Falling edge
                    self.end_samplenum = self.ss = self.samplenum

            self.oldpin = pins[0]
