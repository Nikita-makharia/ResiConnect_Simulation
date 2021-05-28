"""
receiver.py

This file contains definitions for the Receiver Class
used for the simulator
"""

from core.logger import logger, latency_logger, receive_logger

class Receiver:
    """Definition of the Receiver class which plays the role of a ToR
    receiver in the network. It communicates with the controller for
    scheduling and also the AWGR for forwarding.

    Args:
        receiverId (int): the ID of the receiver
        parentAWGR (AWGR): the parent AWGR to which transmitter is connected to,
           defaults to None
        port (int): the port of the AWGR it is connected to, defaults to None
    """

    def __init__(self, receiverId, parentAWGR=None, port=None, network=None):
        self.receiverId = receiverId
        self.parentAWGR = parentAWGR
        self.awgrPort = port
        if network is not None:
            self.network = network

    def linkAWGR(self, parentAWGR, port):
        """Links the Receiver to its parent AWGR

        Args:
            parentAWGR (AWGR): the parent AWGR to which transmitter is connected to
            port (int): the port of the AWGR it is connected to
        """
        self.parentAWGR = parentAWGR
        self.awgrPort = port

    def receive(self, pkt):
        """Recieve packets from the AWGR and process them further

        pkt (Packet): the received packet
        """
        pkt.received = True
        logger.info(f"[Packet {pkt.pktId}] : Received at Receiver {self.receiverId}")
        if isinstance(pkt.pktId, str):
            self.network.controller.received_hello(pkt.pktId)
        else:
            self.network.receivedPkts += 1
            # Enable these loggers if needed. Latency logger generates an additional '--Latency.log' containing
            # packet id and the latency for the packet
            # receive_logger creates addition '--Throughput.log' showing packet and the timeslot in which it was received
            # self.network.last_received_slot = (pkt.arrivalTime + pkt.schedulingDelay + pkt.propagationDelay) / 1200
            # latency_logger.info(f"[Packet {pkt.pktId}], {pkt.totalDelay()}")
            # receive_logger.info(f"{pkt.dest}, {(pkt.arrivalTime + pkt.schedulingDelay + pkt.propagationDelay) / 1200}")
        pass
