"""
projectExceptions.py

This file contains the definitions for different 
types of exceptions that are raised across the
project
"""

class IncompTransmissionError(Exception):
    """IncompTransmissionError is raised when attempting to perform certain
    operations on a packet that usually require the packet to have already 
    reached its destination

    example: trying to calculate the overall delay taken by the packet

    Attributes:
        pktId   -- id of the packet on which the operation was performed
        message -- error message to be paired with the exception
    """

    def __init__(self, pktId, message):
        self.pktId = pktId
        self.message = message
