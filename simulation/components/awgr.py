"""
awgr.py

This file contains definitions for the AWGR Class
used for the simulator
"""

# from core.logger import logger

class AWGR:
    """Definition of the AWGR class which plays the role of a AWGR
    switch in the network. It communicates with the transcievers and
    Space Switches for forwarding.

    Args:
        n (int): the n parameter of the network
        awgrId (int): the ID of the AWGR
        stage (int): if it is a stage 1 or a stage 3 awgr, corressponding values
           taken are 1 and 3
        spaceSwitches (SpaceSwitch[]): the list of Space Switches (len < n) it is connected 
           to in order of port, defaults to None
        transcievers (Transmitter[] or Receiver[]): the list of Transmitters/Receivers 
            (len < n) it is connected to in order of port (depending on Stage 1/3), defaults to None
    """
    def __init__(self, n, awgrId, stage, spaceSwitches=None, transcievers=None, network=None):
        self.n = n
        self.awgrId = awgrId
        self.stage = stage
        self.spaceSwitches = spaceSwitches
        # an array containing the list failed outgoing ports
        self.link_failure_ports = set()
        if network is not None:
            self.network = network
        if self.stage == 1:
            self.transmitters = transcievers
            self.receivers = None
        elif self.stage == 3:
            self.transmitters = None
            self.receivers = transcievers
        else:
            # TODO: Throw exception
            pass

    def linkSpaceSwitches(self, spaceSwitches):
        """ Links the AWGR to its Space Switches

        Args:
            spaceSwitches (SpaceSwitch[]): the list of Space Switches (len < n) it is 
                connected to in order of port, defaults to None
        """
        self.spaceSwitches = spaceSwitches

    def linkTransceivers(self, transcievers):
        """Links the AWGR to its Transmitters/Receivers

        Args:
            transcievers (Transmitter[] or Receiver[]): the list of Transmitters/Receivers (len < n) 
                it is connected to in order of port (depending on Stage 1/3), defaults to None
        """
        if self.stage == 1:
            self.transmitters = transcievers
            self.receivers = None
        elif self.stage == 3:
            self.transmitters = None
            self.receivers = transcievers
        else:
            # TODO: Throw exception
            pass

    def receive(self, inPort, pkt):
        """Receive scheduled packets from the Transmitters/SpaceSwitches

        Args:
            inPort (int): the port on which packet is being received
            pkt (Packet): the packet to be received
        """
        logger.info(f"[Packet {pkt.pktId}] : Reached Stage {self.stage} AWGR with ID = {self.awgrId}")
        outPort = int((inPort + pkt.wavelength) % self.n)

        if self.link_status(outPort):
            self.sendPacket(outPort, pkt)
        else:
            logger.info(f"[Packet {pkt.pktId}] : Being dropped at Stage {self.stage} AWGR with ID = {self.awgrId}")
            self.network.linkDrop += 1
            pass

    def sendPacket(self, outPort, pkt):
        """Forward the packet to the its respective output 

        Args:
            outPort (int): the output port packet is being sent through
            pkt (Packet): the packet to be forwarded
        """
        if self.stage == 1:
            spcSwitch = self.spaceSwitches[outPort]
            if pkt.propagationDelay is None:
                pkt.propagationDelay = 600.0
            else:
                pkt.propagationDelay += 600.0
            spcSwitch.receive(self.awgrId, pkt)
        if self.stage == 3:
            out = self.receivers[outPort]
            if pkt.propagationDelay is None:
                pkt.propagationDelay = 600.0
            else:
                pkt.propagationDelay += 600.0
            out.receive(pkt)

    def link_failure(self, lf):
        """Register a link failure

        Args:
            lf (LinkFailure): the link failure event
        """
        self.link_failure_ports.add(lf.failed_port)

    def link_status(self, port):
        """Check if port is active or not

        Args:
            port (int): the port to check

        Returns:
            bool : if the link is active
        """
        if port in self.link_failure_ports:
            return False
        else:
            return True
