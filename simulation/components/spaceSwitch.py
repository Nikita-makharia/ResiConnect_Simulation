"""
spaceSwitch.py

This file contains definitions for the Space Switch Class
used for the simulator
"""

from core.logger import logger

class StateData:
    """StateData holds the data regarding the state of a space switch
    in a given time slot.

    Args:
        n (int): The n parameter of the network.
    """

    def __init__(self, n):
        self.n = n
        self.reqMat = [[0 for i in range(self.n)] for j in range(self.n)]
        self.finalState = None
        self.transmissions = {}

class SpaceSwitch:
    """Definition for the space switches in the network. These contain
    information regarding the space switch state in each timeslot.

    Args:
        n (int): The n parameter of the network.
        slot (int):  Time slot duration in nanoseconds
    """

    def __init__(self, n, spaceSwitchId, slot, network=None):
        self.n =  n
        self.spaceSwitchId = spaceSwitchId
        self.slot = slot
        self.queue = []
        self.state = {}
        if network is not None:
            self.network = network

    def getSlotData(self, slot):
        """Returns the state data for a specific time slot.

        State Data contains the request matrix where the element (i, j)
        represents the number of requested connections between AWGR i 
        and AWGR j. It also contains the final state of the Space Switch
        for that slot, if decided.

        Args:
            slot (int): The starting time of the slot in nanoseconds.
        """
        slot = str(slot)
        if slot not in self.state.keys():
            self.state[slot] = StateData(self.n)
        ret = self.state[slot]
        return ret

    def receive(self, inPort, pkt):
        """Receive scheduled packets from the Stage One AWGRs and pass them to 
        Stage Three AWGRs

        Args:
            inPort (int): the port on which packet is being received
            pkt (Packet): the packet to be received
        """
        logger.info(f"[Packet {pkt.pktId}] : Reached Space Switch {self.spaceSwitchId}")
        slotData = self.getSlotData(pkt.dispatchSlot)
        outPort = slotData.finalState[inPort]
        self.sendPacket(outPort, pkt)

    def sendPacket(self, outPort, pkt):
        """Forward the packet to the its respective output 

        Args:
            outPort (int): the output port packet is being sent through
            pkt (Packet): the packet to be forwarded
        """
        logger.info(f"[Packet {pkt.pktId}] : Sent from Space Switch {self.spaceSwitchId}")
        outSwitch = self.network.stageThreeAWGRs[outPort]
        outSwitch.receive(self.spaceSwitchId, pkt)
