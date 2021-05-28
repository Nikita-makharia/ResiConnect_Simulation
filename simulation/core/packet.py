"""
packet.py

This file contains definitions for the Packet Class
used for the simulator
"""

from core.projectExceptions import IncompTransmissionError

class Packet:
    """Definition of the packet class for all packets/cells that will
    be transmitted in the simulated network.

    Args:
        pktId (int): unique ID of the genrated packet
        src (int): source node of the packet
        dest (int): destination node of the packet
        arrivalTime (float): timestamp of the packets arrival

    schedulingDelay and propagationDelay are set my other objects and are
    assigned values through the course of transmission, hence they are 
    initilized to 'None'
    """

    def __init__(self, pktId, src, dest, arrivalTime):
        self.pktId = pktId
        self.src = src
        self.dest = dest
        self.arrivalTime = arrivalTime
        # time slot when the packet is dispatched
        self.dispatchSlot = None
        # wavelength assigned to packet
        self.wavelength = None
        self.schedulingDelay = None
        self.propagationDelay = None
        self.miscDelay = 0
        # if the packet has been received
        self.received = False
        self.failed_transmitters = []

    def totalDelay(self):
        """Returns the total delay taken by the packet to reach its destination

        Returns:
            float: total delay in milliseconds
        """

        if not self.received:
            raise IncompTransmissionError(self.pktId, "Attempting to calculate " 
                  "the delay of a packet that has not reached its destination.")
        else:
            return (self.schedulingDelay + self.propagationDelay 
                   + self.miscDelay)

def generate_hello_packet(pktId, src, wavelength, dest, t):
    hello_id = "hello-" + str(pktId)
    hello_pkt = Packet(hello_id, src, dest, t)
    hello_pkt.wavelength = wavelength

    return hello_pkt
