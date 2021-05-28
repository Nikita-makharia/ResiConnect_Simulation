"""
main.py
"""

import components.transmitter as trnsmt
import components.receiver as rcvr
import components.event_generator as ev_gen
import components.spaceSwitch as spcSwtch
import components.awgr as awgr
import components.controller as cntrlr
import logging
from core.logger import logger, LogName

import sys

class ASA:
    """Class definition for an entire ASA Network with all of it's components

    Args:
        n (int): The n parameter of the network.
        rate (float): lambda for packet arrival rate, poission process
        slot (int): slot duration
        hello_int (int): Hello Interval
        runtime (int): duration for packet arrival
    """

    def __init__(self, n, rate, slot, hello_int, runtime):
        self.n = n
        self.rate = rate
        self.slot = slot
        self.runtime= runtime

        self.event_generator = ev_gen.EventGenerator(self.n,
                            self.rate, self.runtime, self.slot, network=self)
        self.controller = cntrlr.Controller(self.n, slot, hello_int, network=self)

        self.transmitters = []
        self.receivers = []
        self.stageOneAWGRs = []
        self.stageThreeAWGRs = []
        self.spaceSwitches = []

        self.overflowDrop = 0
        self.linkDrop = 0
        self.generatedPkts = 0
        self.receivedPkts = 0

        # Generate Space Switches and Transcievers, link them with each other
        for i in range(self.n):
            self.spaceSwitches.append(spcSwtch.SpaceSwitch(self.n, i, 
                self.slot, network=self))
            self.stageOneAWGRs.append(awgr.AWGR(self.n, i, 1, self.spaceSwitches, network=self))
            self.stageThreeAWGRs.append(awgr.AWGR(self.n, i, 3, self.spaceSwitches, network=self))
            for j in range(self.n):
                self.transmitters.append(trnsmt.Transmitter((i * self.n + j),
                                        self.stageOneAWGRs[i], j, network=self))
                self.receivers.append(rcvr.Receiver((i * self.n + j),
                                    self.stageThreeAWGRs[i], j, network=self))

        for i in range(self.n):
            t = [self.transmitters[j] for j in range(self.n * i, self.n * (i + 1))]
            r = [self.receivers[j] for j in range(self.n * i, self.n * (i + 1))]
            self.stageOneAWGRs[i].linkTransceivers(t)
            self.stageThreeAWGRs[i].linkTransceivers(r)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        N = int(sys.argv[1])
    else:
        N = 11
    # 0.00041666666 -- 0.625 Packets per second, per transmitter
    # 0.0008333333333 -- 1.25 Packet per second, per transmitter
    RATE = 0.003333333333 * N * N # 5Gbps per transmitter
    SLOT_DUR = 1200
    RUNTIME = 10000000
    HELLO_INTERVAL = 3

    if len(sys.argv) > 2:
        HELLO_INTERVAL = int(sys.argv[2])
    net = ASA(N, RATE, SLOT_DUR, HELLO_INTERVAL, RUNTIME)

    # Change this flag to use NNT Approach
    # net.controller.reroute_flag = 1

    logger.info("Intialized ASA Network with N = %s, Arrival Rate = %s, Slot Duration = %s, Runtime = %s",
                N, RATE, SLOT_DUR, RUNTIME)

    net.event_generator.on_demand_dispatch()

    logger.info(f"Generated Packets {net.generatedPkts}")
    logger.info(f"Received Packets {net.receivedPkts}")
    logger.info(f"Overflow Drops {net.overflowDrop}")
    logger.info(f"Link Drops {net.linkDrop}")

    print(LogName)
