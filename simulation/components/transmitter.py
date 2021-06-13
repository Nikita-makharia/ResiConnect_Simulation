"""
transmitter.py

This file contains definitions for the Transmitter Class
used for the simulator
"""

from core.logger import logger

class Transmitter:
    """Definition of the Transmitter class which plays the role of a ToR
    transmitter in the network. It communicates with the controller for
    scheduling and also the AWGR for forwarding.

    Args:
        transmitterId (int): the ID of the transmitter
        parentAWGR (AWGR): the parent AWGR to which transmitter is connected to,
            defaults to None
        port (int): the port of the AWGR it is connected to, defaults to None
    """

    def __init__(self, transmitterId, parentAWGR=None, port=None, network=None):
        self.transmitterId = transmitterId
        self.parentAWGR = parentAWGR
        self.awgrPort = port
        self.transmissions = {}
        self.bufferCount = 0
        self.buffer_MAX = 5000
        self.dispatch_count = 0
        if network is not None:
            self.network = network

    def linkAWGR(self, parentAWGR, port):
        """Links the Transmitter to its parent AWGR

        Args:
            parentAWGR (AWGR): the parent AWGR to which transmitter is connected to
            port (int): the port of the AWGR it is connected to
        """
        self.parentAWGR = parentAWGR
        self.awgrPort = port

    def receive(self, pkt):
        """Recieve scheduled packets from the PacketGenerator and do further 
        processing

        Args:
            pkt (Packet): the incoming packet
        """
        if self.bufferCount < self.buffer_MAX:
            self.bufferCount += 1
            self.onPacketArrival(pkt)
        else:
            self.network.overflowDrop += 1

    def onPacketArrival(self, pkt):
        """Communicate with the controller and schedule the packet

        Args:
            pkt (Packet): the incoming packet
        """
        logger.info(f"[Packet {pkt.pktId}] : Arrived at Transmitter {self.transmitterId}")
        self.network.controller.enqueue_scheduler(pkt)

    def onSchedule(self, pkt):
        """Recieve scheduled packets from the Controller and do further 
        processing

        Args:
            pkt (Packet): the incoming packet
        """
        logger.info(f"[Packet {pkt.pktId}] : Scheduled for dispatch from Transmitter {self.transmitterId}")
        if pkt.dispatchSlot in self.transmissions.keys():
            if pkt.dest in self.transmissions[pkt.dispatchSlot]:
                self.transmissions[pkt.dispatchSlot][pkt.dest] += 1
            else:
                self.transmissions[pkt.dispatchSlot][pkt.dest] = 1
            self.transmissions[pkt.dispatchSlot]['count'] += 1
        else:
            self.transmissions[pkt.dispatchSlot] = {}
            self.transmissions[pkt.dispatchSlot]['count'] = 1
            self.transmissions[pkt.dispatchSlot][pkt.dest] = 1
        self.sendPacket(pkt)

    def sendPacket(self, pkt):
        """Forward the packet to the parent AWGR
        
        Args:
            pkt (Packet): the incoming packet
        """
        self.parentAWGR.receive(self.awgrPort, pkt)
        self.dispatch_count += 1
        if self.bufferCount > 0:
            self.bufferCount -= 1
        else:
            self.bufferCount = 0

    def transmissionCount(self, current_slot, k):
        """ Return the count of packets transmitted in the last k
        timeslots.

        Args:
            current_slot (int): the current timeslot that is running
            k (int): the number of latest timeslots to examine
        """
        iter_ctr = 0
        ret = 0
        for slot in reversed(self.transmissions.keys()):
            if slot < current_slot - k:
                break
            ret += self.transmissions[slot]['count']
            iter_ctr += 1
            if iter_ctr == k:
                break

        return ret

    def pairwiseTransmissionCount(self, current_slot, k):
        """ Return the count of packets transmitted in the last k
        timeslots, paired by the destination receiver.

        Args:
            current_slot (int): the current timeslot that is running
            k (int): the number of latest timeslots to examine
        """
        iter_ctr = 0
        ret = {}
        ret['count'] = 0
        for slot in reversed(self.transmissions.keys()):
            if slot < current_slot - k:
                break
            for k in self.transmissions[slot].keys():
                if k == 'count':
                    ret['count'] += self.transmissions[slot][k]
                elif k in ret.keys():
                    ret[k] += self.transmissions[slot][k]
                else:
                    ret[k] = self.transmissions[slot][k]
            iter_ctr += 1
            if iter_ctr == k:
                break

        return ret
