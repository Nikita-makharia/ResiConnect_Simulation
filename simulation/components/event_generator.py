"""
event_generator.py

This file contains definitions for the EventGenerator Class
used for the simulator
"""

import core.packet as pkt
import random as rand
from core.logger import logger

class Event:
    """Base Event Class

    Args:
        category (string): the type of event
        t (int): timestamp of the occurence of the event in nanoseconds
    """

    def __init__(self, category, t):
        self.category = category
        self.t = t

class PacketArrival(Event):
    """A Packet arrival event

    Args:
        pkt (Packet): the arriving packet
    """

    def __init__(self, t, pkt):
        Event.__init__(self, "packet-arrival", t)
        self.pkt = pkt

class TimeSlotEnd(Event):
    """Event marking the end of a time slot

    Args:
        slot_no (int): the number of the time slot that has just ended
    """

    def __init__(self, t, slot_no):
        Event.__init__(self, "timeslot-end", t)
        self.slot_no = slot_no

class EventSetEnd(Event):
    """Event marking the end of simulation events
    """

    def __init__(self):
        Event.__init__(self, "eventset-end", -1)

class LinkFailure(Event):
    """Event marking the failure of a link.

    Args:
        awgr_id (int): the awgr_id which has a link failure
        failed_port (int): the port id which the failed link is attached to
    """

    def __init__(self, t, awgr_id, failed_port):
        Event.__init__(self, "link-failure", t)
        self.awgr_id = awgr_id
        self.failed_port = failed_port

class EventGenerator:
    """Definition of the EventGenerator class which generates random
    traffic whose arrivals follow the Poission Distribution.

    Args:
        n (int): the n parameter of the network
        rate (int): arrival rate of packets (relative to nanoseconds)
        runtime (int): duration of the simulation (in nanoseconds)
        time_slot (int): duration of the time slot (in nanoseconds)
    """

    def __init__(self, n, rate, runtime, time_slot, network=None):
        self.n = n
        self.rate = rate
        self.runtime = runtime
        self.time_slot = time_slot
        # Stores the list of all events
        self.event_set = []
        # Count of each type of event
        self.event_count = {}
        # fault occurs at random time
        # self.fault_at = rand.randrange(runtime)
        # Link failures in the form of (time of fault, awgr_id, spaceSwitch_id)
        self.link_failures = []
        # self.link_failures = [(0, 0, 0)]
        # self.link_failures = [(0, 0, 0), (0, 1, 1)]
        # self.link_failures = [(0, 0, 0), (0, 1, 1), (0, 2, 2)]
        # self.link_failures = [(self.fault_at, 0, 0)]
        # self.link_failures = [(50000, 0, 0)]
        self.link_fail_count = len(self.link_failures)
        if network is not None:
            self.network = network

    def insert_event(self, ev):
        """ Inserts an event into the event_set and increments its related
        counter

        Args:
            ev (Event): the event you wish to enter into the event_set
        """
        if ev.category not in self.event_count.keys():
            self.event_count[ev.category] = 1
        else:
            self.event_count[ev.category] += 1
        self.event_set.append(ev)

    def generate_event_set(self, override=False):
        """Generates a packet set on the basis of the given parameters.

        Args:
            override (bool): if the existing packetSet should be overridden,defaults
            to False

        Returns:
            Packet[]: Populates the packetSet
        """
        if len(self.event_set) == 0 or override:
            time_ctr = rand.expovariate(1) / self.rate
            idCtr = 1
            slot_ctr = time_ctr // self.time_slot
            fail_ev = self.link_failures.pop(0)
            while time_ctr < self.runtime:
                eo = self.earliest_occurence(time_ctr, (slot_ctr + 1) * self.time_slot, fail_ev[0])
                if eo == 1:
                    src, dest = rand.sample(range(self.n ** 2), 2)
                    p = pkt.Packet(idCtr, src, dest, time_ctr)
                    self.insert_event(PacketArrival(time_ctr, p))
                    time_ctr += rand.expovariate(1) / self.rate
                    idCtr += 1
                elif eo == 2:
                    self.insert_event(TimeSlotEnd((slot_ctr + 1) * self.time_slot, slot_ctr))
                    slot_ctr = time_ctr // self.time_slot
                elif eo == 3:
                    self.insert_event(LinkFailure(fail_ev[0], fail_ev[1], fail_ev[2]))
                    if len(self.link_failures) > 0:
                        fail_ev = self.link_failures.pop(0)
                    else:
                        fail_ev = (None, None, None)
            self.insert_event(EventSetEnd())

    def on_demand_dispatch(self, override=False):
        """An on demand event dispatcher that generates events and immediately dispatches
        them. These events are not enumerated in a list

        Args:
            override (bool): if the existing packetSet should be overridden,defaults
            to False
        """
        if len(self.event_set) == 0 or override:
            time_ctr = rand.expovariate(1) / self.rate
            idCtr = 1
            slot_ctr = time_ctr // self.time_slot
            fail_ev = self.get_next_failure()
            while time_ctr < self.runtime:
                eo = self.earliest_occurence(time_ctr, (slot_ctr + 1) * self.time_slot, fail_ev[0])
                if eo == 1:
                    src, dest = rand.sample(range(self.n ** 2), 2)
                    # Use in case generating biased traffic for N = 11
                    # src = rand.choice(range(self.n ** 2))
                    # if src == 5:
                    #     dest = rand.choice(range(self.n)) * self.n + 6 (For N = 5, change to self.n + 3)
                    # else:
                    #     dest = rand.choice(range(self.n ** 2))
                    p = pkt.Packet(idCtr, src, dest, time_ctr)
                    self.dispatch_event(PacketArrival(time_ctr, p))
                    time_ctr += rand.expovariate(1) / self.rate
                    idCtr += 1
                    self.network.generatedPkts += 1
                elif eo == 2:
                    self.dispatch_event(TimeSlotEnd((slot_ctr + 1) * self.time_slot, slot_ctr))
                    slot_ctr = time_ctr // self.time_slot
                elif eo == 3:
                    self.dispatch_event(LinkFailure(fail_ev[0], fail_ev[1], fail_ev[2]))
                    logger.info(f"Failure at {fail_ev[0]}.")
                    fail_ev = self.get_next_failure()
            self.dispatch_event(EventSetEnd())

    def get_next_failure(self):
        """ Utility function that fetches the next link failure event
        defined by the user
        """
        if len(self.link_failures) > 0:
            ret = self.link_failures.pop(0)
        else:
            ret = (None, None, None)

        return ret

    def earliest_occurence(self, pkt_arrival, slot_end, link_failure):
        """ Utility function which determines which event among packet_arrival,
        time slot end, and link failure occurs first
        """
        if link_failure is not None:
            r = [pkt_arrival, slot_end, link_failure]
        else: 
            r = [pkt_arrival, slot_end]
        return (r.index(min(r)) + 1)

    def dispatch_event(self, ev):
        """ Dispatches generated events according to the next action to be taken.
        
        Args:
            ev (event): the event to be dispatched.
        """
        if ev.category == "packet-arrival":
            src = self.network.transmitters[ev.pkt.src]
            src.receive(ev.pkt)
        elif ev.category == "timeslot-end" or ev.category == "eventset-end":
            self.network.controller.event_trigger(ev)
        elif ev.category == "link-failure":
            awgr = self.network.stageOneAWGRs[ev.awgr_id]
            awgr.link_failure(ev)

    def dispatch_events(self):
        """ Dispatch all events in the generated event set
        """
        for ev in self.event_set:
            self.dispatch_event(ev)

