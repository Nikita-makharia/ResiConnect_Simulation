"""
controller.py

This file contains definitions for the Space Switch Class
used for the simulator
"""

import core.matcher as mtchr
import random
from core.packet import generate_hello_packet

# Standard Logging
from core.logger import logger


# T_Cap = Max_Transmission * N
MAX_TRANSMISSION_COUNT = 1
# Value of m, previous time slots to examine
PREV_EXAMINE_SLOTS = 10

RECEIVE_THRESHOLD = 10
ANOMALY_THRESHOLD = 10

class LinkTracking:
    """Sets of Space Switch Links used for Fault Tracking

    Args:
        n (int): The n parameter of the network
    """

    def __init__(self, n):
        self.stageOneLinks = [set() for i in range(n)]
        self.stageThreeLinks = [set() for i in range(n)]

class Controller:
    """Definition for the main controller component of the network. Main jobs 
    include scheduling transmissions and also monitoring network faults.

    Args:
        n (int): The n parameter of the network.
        slot (int): Slot duration
        hello_int (int): Hello Interval 
    """

    def __init__(self, n, slot, hello_int, network=None):
        self.n = n
        self.slot = slot
        # Tracks the current time slot running
        self.current_slot = None
        # Set of failed links of the form (1, awgr, spaceSwitch) or (3, spaceSwitch, awgr)
        self.failed_links = set()
        # Used to track calculated ratios 
        self.alternate_routes = {}
        # List of pending Hello Packets yet to be received
        self.pending_hello_pkts = {}
        # Tracks the number of anomalies per link, dictionary of the form "link: anomalyCount"
        self.anomaly_count = {}
        # Counter to track no.of Hello Packets, and also assign them ids
        self.hello_ctr = 1
        self.hello_interval =  hello_int
        # Track links and their hello frequencies as the controller modifies them
        self.fault_freq = {}
        # Track what Stage 1-2 and Stage 2-3 link pairs were made and ensure they're not repeated 
        # consecutively
        self.previous_link_pair = []
        for i in range(self.hello_interval + 1):
            self.fault_freq[i] = LinkTracking(n)
        init = self.fault_freq[self.hello_interval] 
        for i in range(self.n):
            init.stageOneLinks[i].update([i for i in range(n)])
            init.stageThreeLinks[i].update([i for i in range(n)])

        # Initialize previous link pairs to -1, updates as the simulation goes
        for i in range(self.n):
            x = []
            for j in range(self.n):
                x.append(-1)
            self.previous_link_pair.append(x)


        # 0 - for ResiConnect and 1 - for NNT, set to ResiConnect by default
        self.reroute_flag = 0
        if network is not None:
            self.network = network

    def event_trigger(self, ev):
        """ Response function to handle special trigger events. Initiates the proper
        response depending on the event.

        Args:
            ev(Event): the special trigger event
        """
        if ev.category == "timeslot-end":
            logger.info(f"[Timeslot {ev.slot_no}] : Timeslot ENDING....")
            self.fault_tracking(self.current_slot)
            self.allotSlots(ev.slot_no)
            logger.info(f"[Timeslot {ev.slot_no}] : Timeslot ENDED, Next Timeslot STARTING...")
        elif ev.category == "eventset-end":
            self.clearQueue(self.current_slot)

    def register_link_failure(self, link):
        """ Add an entry to the set of failed links in the network

        Args:
            link (tuple): tuple of the form (awgrId, failed_port) of the failed link
        """
        self.failed_links.add(link)

    def compute_routes(self, awgr_id):
        """ Compute the Average activities for all transmitters linked to an AWGR

        Args:
            awgr_id (int): ID of the AWGR

        Returns:
            int[] : average activity of all transmitters connected to awgr
        """
        ret = []
        trns_data = []
        for alt in range(self.n):
            trnsmtr = self.network.transmitters[awgr_id * self.n + alt]
            avg_data = trnsmtr.pairwiseTransmissionCount(self.current_slot, PREV_EXAMINE_SLOTS)
            trns_data.append(avg_data)
            avg_usage = avg_data['count'] / PREV_EXAMINE_SLOTS
            ret.append(MAX_TRANSMISSION_COUNT * self.n - avg_usage)
        self.alternate_routes[awgr_id] = {}
        self.alternate_routes[awgr_id]["last_update"] = self.failed_links
        self.alternate_routes[awgr_id]["routes"] = ret
        self.alternate_routes[awgr_id]["data"] = trns_data

        return ret


    def get_alternate_transmitter(self, pkt):
        """ Return an alternate src that can be used to re-route traffic

        Args:
            pkt (Packet): packet that needs an alternate transmitter
        """
        # Convert Transmitter IDs to 0 to n-1 form
        fail = pkt.failed_transmitters.copy()
        for i in range(len(fail)):
            fail[i] = fail[i] % self.n
        # valid choices for re-routing
        choices = [i for i in range(self.n) if i not in fail and i != (pkt.src % self.n)]
        # check if ratios are already calculated, otherwise calculate them
        if (pkt.src // self.n) in self.alternate_routes:
            last_upd = self.alternate_routes[(pkt.src // self.n)]["last_update"]
            alts = self.alternate_routes[(pkt.src // self.n)]["routes"]
            if last_upd != self.failed_links:
                alts = self.compute_routes((pkt.src // self.n))
        else:
            alts = self.compute_routes((pkt.src // self.n))
        r = []
        sum_ctr = 0
        for i in range(self.n):
            if i not in choices:
                r.append(0)
            else:
                r.append(alts[i])
                sum_ctr += alts[i]
        if sum_ctr == 0:
            for i in range(self.n):
                if i in choices:
                    r[i] = 1 / len(choices)
        else:
            for i in range(len(r)):
                r[i] = r[i] / sum_ctr
        p = random.uniform(0, 1)
        prob_ctr = 0
        for i in range(len(r)):
            if r[i] == 0:
                continue
            elif prob_ctr + r[i] > p:
                ret = i
                break
            else:
                prob_ctr += r[i]

        ret = ret + self.n * (pkt.src // self.n )
        return ret

    def adj_alternate_transmitter(self, pkt):
        """ NNT approach to redirecting. Redirects the traffic to transmitters adjacent to it.

        Args:
            pkt (Packet): packet that needs an alternate transmitter
        """
        s = pkt.src
        if s % self.n == 0:
            ret = s + 1
        elif s % self.n == self.n - 1:
            ret = s - 1
        else:
            ret = random.choice([s - 1, s + 1])

        return ret

    def resi_redirect(self, pkt):
        """ ResiConnect Packet redirection by applying both transmitter and receiver 
        vertical connections.

        Args:
            pkt (Packet): packet that needs alternate transmitter/receiver
        """
        # Convert Transmitter IDs to 0 to n-1 form
        fail = pkt.failed_transmitters.copy()
        for i in range(len(fail)):
            fail[i] = fail[i] % self.n
        # valid choices for re-routing
        trnsmtr_choices = [i for i in range(self.n) if i not in fail and i != (pkt.src % self.n)]
        recv_choices = [i for i in range(self.n) if i != (pkt.dest % self.n)]
        # check if ratios are already calculated, otherwise calculate them
        if (pkt.src // self.n) in self.alternate_routes:
            last_upd = self.alternate_routes[(pkt.src // self.n)]["last_update"]
            alts = self.alternate_routes[(pkt.src // self.n)]["routes"]
            if last_upd != self.failed_links:
                alts = self.compute_routes((pkt.src // self.n))
        else:
            alts = self.compute_routes((pkt.src // self.n))

        # For Transmitter T(i, j), do:
        dest_awgr_id = pkt.dest // self.n
        # contains count of all packets sent to each receiver
        pairwise_data = self.alternate_routes[(pkt.src // self.n)]["data"][(pkt.src % self.n)]
        # cover all receivers connected to dest recv awgr
        recv_free = []
        for i in range(dest_awgr_id * self.n, (dest_awgr_id + 1) * self.n):
            if i == pkt.dest:
                recv_free.append(0)
            elif i in pairwise_data.keys():
                avg_free = MAX_TRANSMISSION_COUNT - (pairwise_data[i] / PREV_EXAMINE_SLOTS)
                recv_free.append(avg_free)
            else:
                recv_free.append(0)
        # summation
        recv_free_sum = 0
        for i in range(len(recv_free)):
            recv_free_sum += recv_free[i] # End of First Part

        # Second Part : For each Transmitter other than T(i, j) we calculate T_free values, already done above ('alts' array)
        # Third Part : If > any T_free[k]

        # check to use alt trnsmtr, or rcvr
        recvRedirection = False
        for i in range(len(alts)):
            if i != (pkt.src % self.n): #other than T(i, j)
                if recv_free_sum > alts[i]:
                    recvRedirection = True
                    break

        # Redirection part, just spilts traffic, same as old algo
        if recvRedirection:
            free_arr = recv_free
            choices = recv_choices
        else:
            free_arr = alts
            choices = trnsmtr_choices

        r = []
        sum_ctr = 0
        for i in range(self.n):
            if i not in choices:
                r.append(0)
            else:
                r.append(free_arr[i])
                sum_ctr += free_arr[i]
        if sum_ctr == 0:
            for i in range(self.n):
                if i in choices:
                    r[i] = 1 / len(choices)
        else:
            for i in range(len(r)):
                r[i] = r[i] / sum_ctr
        p = random.uniform(0, 1)
        prob_ctr = 0
        for i in range(len(r)):
            if r[i] == 0:
                continue
            elif prob_ctr + r[i] > p:
                ret = i
                break
            else:
                prob_ctr += r[i]

        if recvRedirection:
            pkt.dest = ret + self.n * (pkt.dest // self.n )
        else:
            pkt.src = ret + self.n * (pkt.src // self.n )

        return pkt

    def get_permutations(self, sId, a, b):
        """ Generate pairs of Stage 1-2, and Stage 2-3 links at each space switch
        sharing the same hello interval to traverse both links with one hello packet.
        If no combination is possible, or pairing is the same as previous iteration
        then pair with a random link.

        Args: 
            sId (int): Space Switch ID
            a (int[]): Incoming Space Switch port numbers connected to Stage 1-2 links
            b (int[]): Outgoing Space Switch port numbers connected to Stage 2-3 links

        Returns:
            int[], int[] : arrays a and b, where a[i] and b[i] are a pair
        """
        random.shuffle(a)
        random.shuffle(b)
        n_arr = [i for i in range(self.n)]
        a_choices = [i for i in n_arr if i not in list(self.fault_freq[0].stageOneLinks[sId])]
        b_choices = [i for i in n_arr if i not in list(self.fault_freq[0].stageThreeLinks[sId])]
        while len(a) != len(b):
            if len(a) < len(b):
                a.append(random.choice(a_choices))
            else:
                b.append(random.choice(b_choices))

        for i in range(len(a)):
            in_link = a[i]
            out_link = b[i]
            if self.previous_link_pair[sId][in_link] == b[i]:
                rep_in_choices = [j for j in a_choices if j != a[i]]
                rep_out_choices = [j for j in b_choices if j != b[i]]
                b[i] = random.choice(rep_out_choices)
                a.append(random.choice(rep_in_choices))
                b.append(out_link)
            else:
                self.previous_link_pair[sId][in_link] = b[i]


        return a, b


    def fault_tracking(self, current_slot):
        """ The main fault tracking module. At the end of every time-slot it checks for Hello Packet timeouts,
        records anomalies and determines faults. It also checks the Hello Packet frequencies and generates &
        dispatches any Hello Packets as necessary/

        Args:
            current_slot (int): The value of the current time-slot.
        """
        for pkt in list(self.pending_hello_pkts):
            pkt_info = self.pending_hello_pkts[pkt]
            freq = pkt_info["freq"]
            fault_declared = False
            pre_failed_link = False
            # Check if Hello Packet expired
            if current_slot > pkt_info["dispatch_slot"] + RECEIVE_THRESHOLD:
                freqLinks = self.fault_freq[freq]
                sId = pkt_info["space_switch_id"]
                fault_links = [(1, pkt_info["in_link"], pkt_info["space_switch_id"]), (3, pkt_info["space_switch_id"], pkt_info["out_link"])]
                # Check if this link has already been declared faulty
                for link in fault_links:
                    if link in self.failed_links:
                        pre_failed_link = True
                if not pre_failed_link:
                    # Record as an anomaly
                    for link in fault_links:
                        if link in self.anomaly_count:
                            self.anomaly_count[link] += 1
                            # If above anomaly threshold, then mark as link fault
                            if self.anomaly_count[link] >= ANOMALY_THRESHOLD:
                                fault_decalred = True
                                self.fault_found_at = self.slot * current_slot
                                failedLinks = self.fault_freq[0]
                                if link[0] == 1:
                                    freqLinks.stageOneLinks[sId].discard(pkt_info["in_link"])
                                    failedLinks.stageOneLinks[sId].add(pkt_info["in_link"])
                                elif link[0] == 3:
                                    freqLinks.stageThreeLinks[sId].discard(pkt_info["out_link"])
                                    failedLinks.stageThreeLinks[sId].add(pkt_info["out_link"])
                                self.register_link_failure(link)
                                if len(self.failed_links) > self.network.event_generator.link_fail_count:
                                    raise Exception("Detected additional link faults")
                        else:
                            self.anomaly_count[link] = 1
                    if freq > 1 and not fault_declared:
                        # If anomaly, but not above Anomaly Threshold, then 
                        # increase freq of Hello Packets
                        freqLinks.stageOneLinks[sId].discard(pkt_info["in_link"])
                        freqLinks.stageThreeLinks[sId].discard(pkt_info["out_link"])
                        incFreq = freq - 1
                        incFreqLinks  = self.fault_freq[incFreq]
                        incFreqLinks.stageOneLinks[sId].add(pkt_info["in_link"])
                        incFreqLinks.stageThreeLinks[sId].add(pkt_info["out_link"])

                del self.pending_hello_pkts[pkt]

        # Schedule Hello Packets
        for freq in self.fault_freq.keys():
            if freq > 0 and current_slot % freq == 0:
                links = self.fault_freq[freq]
                # At every space swtich, generate pairs of links and send a hello packet
                # along that pair of links
                for i in range(self.n):
                    in_links, out_links = self.get_permutations(i, list(links.stageOneLinks[i]), list(links.stageThreeLinks[i]))
                    for j in range(len(in_links)):
                        in_link = in_links[j]
                        out_link = out_links[j]
                        src_member_id = random.randrange(self.n)
                        src = self.n * in_link + src_member_id 
                        if i < src_member_id:
                            wv = self.n + i - src_member_id
                        else:
                            wv = i - src_member_id
                        dest = self.n * out_link + ((src_member_id + 2 * wv) % self.n)
                        hpkt = generate_hello_packet(self.hello_ctr, src, wv, dest, self.slot * current_slot)
                        self.hello_ctr += 1
                        self.pending_hello_pkts[hpkt.pktId] = {"freq": freq, "space_switch_id": i, "in_link": in_link, "out_link": out_link, "dispatch_slot": current_slot}
                        self.network.spaceSwitches[i].queue.insert(0, hpkt)

    def received_hello(self, hello_id):
        """ Registers the receival of a hello packet by one of the receivers.
        If the link is anomalous, then decrease its frequency again.

        Args:
            hello_id (int): the id of the hello packet
        """
        logger.debug(f"Received Hello Packet : {hello_id}")
        if hello_id in list(self.pending_hello_pkts):
            pkt_info = self.pending_hello_pkts[hello_id]
            freq = pkt_info["freq"]
            # if hello freq was increased, decrease it after anomalous behavior is no longer observed
            if freq < self.hello_interval:
                freqLinks = self.fault_freq[freq]
                sId = pkt_info["space_switch_id"]
                freqLinks.stageOneLinks[sId].discard(pkt_info["in_link"])
                freqLinks.stageThreeLinks[sId].discard(pkt_info["out_link"])
                decFreq = freq + 1
                decFreqLinks  = self.fault_freq[decFreq]
                decFreqLinks.stageOneLinks[sId].add(pkt_info["in_link"])
                decFreqLinks.stageThreeLinks[sId].add(pkt_info["in_link"])
            del self.pending_hello_pkts[hello_id]
            fault_links = [(1, pkt_info["in_link"], pkt_info["space_switch_id"]), (3, pkt_info["space_switch_id"], pkt_info["out_link"])]
            # Reset anomaly counter for the link
            for link in fault_links:
                if link in self.anomaly_count:
                    del self.anomaly_count[link]
        else:
            logger.info(f"Past threshold arrival of Hello Packet : {hello_id}")
            pass


    def enqueue_scheduler(self, pkt):
        """Schedules the transmission of a packet by assinging a suitable
        timeslot and wavelength.

        Args:
            pkt (Packet): The packet to be scheduled.
        """

        pktSlot = pkt.arrivalTime // self.slot

        self.current_slot = pktSlot

        mSrc = pkt.src % self.n
        mDest = pkt.dest % self.n

        if (mDest - mSrc) % 2 == 0:
            pkt.wavelength = ((mDest - mSrc) / 2) % self.n
        else:
            pkt.wavelength = ((self.n + mDest - mSrc) / 2 ) % self.n

        if (mDest + mSrc) % 2 == 0:
            sSwitchId = ((mDest + mSrc) / 2) % self.n
        else:
            sSwitchId = ((mDest + mSrc + self.n) / 2) % self.n

        sSwitch = self.network.spaceSwitches[int(sSwitchId)]
        if tuple([1, (pkt.src // self.n), sSwitchId]) in self.failed_links or tuple([3, sSwitchId,(pkt.dest // self.n)]) in self.failed_links:
            pkt.failed_transmitters.append(pkt.src)
            # old_src = pkt.src
            # old_dest = pkt.dest
            pkt = self.resi_redirect(pkt)
            # new_src = pkt.src
            # new_dest = pkt.dest

            # print(old_src, old_dest, new_src, new_dest)

            pkt.miscDelay += 1200
            self.network.transmitters[pkt.src].receive(pkt)
            logger.info(f"[Packet {pkt.pktId}] : Being re-routed through Transmitter {pkt.src}....")
        else:
            sSwitch.queue.append(pkt)

    def allotSlots(self, slotNumber):
        """When a time slot expires, send dispatch messages for all 
        scheduled packets.

        Args:
            slotNumber (int): The time slot for which dispatching
                is being done
        """
        for i in range(self.n):
            # for each space switch in the given slot
            sSwitch = self.network.spaceSwitches[i]
            data = sSwitch.getSlotData(slotNumber)
            finalQueue = sSwitch.queue

            # generate a traffic matrix and get the best bipartite matching
            for pkt in sSwitch.queue:
                gSrc = pkt.src // self.n
                gDest = pkt.dest // self.n
                data.reqMat[gSrc][gDest] += 1
            val, matching = mtchr.Matcher(data.reqMat).solve()
            data.finalState = matching

            # for each packet in the queue, check if it can be scheduled
            for pkt in sSwitch.queue:
                # check if packet src/dest matches space switch's config for this timeslot
                if pkt.dest // self.n == matching[pkt.src // self.n]:
                    if pkt.src in data.transmissions.keys():
                        if pkt.wavelength in data.transmissions[pkt.src].keys():
                            trnsmsnCount = data.transmissions[pkt.src][pkt.wavelength]
                        else:
                            data.transmissions[pkt.src][pkt.wavelength] = 0
                        trnsmsnCount = data.transmissions[pkt.src][pkt.wavelength]
                    else:
                        data.transmissions[pkt.src] = {}
                        data.transmissions[pkt.src]['count'] = 0
                        data.transmissions[pkt.src][pkt.wavelength] = 0
                        trnsmsnCount = data.transmissions[pkt.src][pkt.wavelength]
                    if trnsmsnCount < MAX_TRANSMISSION_COUNT:
                        src = self.network.transmitters[pkt.src]
                        pkt.dispatchSlot = slotNumber
                        pkt.schedulingDelay = ((pkt.dispatchSlot + 1) * self.slot) - pkt.arrivalTime
                        logger.debug(f"[Packet {pkt.pktId}] : Wavelength Assigned = {pkt.wavelength}")
                        logger.debug(f"[Packet {pkt.pktId}] : Space Switch Assigned = {i}")
                        logger.debug(f"[Packet {pkt.pktId}] : Time Slot Assigned = {slotNumber}")
                        data.transmissions[pkt.src][pkt.wavelength] += 1
                        data.transmissions[pkt.src]['count'] += 1
                        src.onSchedule(pkt)
                        finalQueue.remove(pkt)

            # queue with after removing scheduled packets
            sSwitch.queue = finalQueue
    
    def checkEmptyQueues(self):
        """Check if all the Queues at the space switches are empty
        and no packets are pending for scheduling.

        Returns:
            bool: if all the queues are empty or not
        """
        ret = True
        for i in range(self.n):
            if len(self.network.spaceSwitches[i].queue) != 0:
                ret = False
                break
        return ret

    def clearQueue(self, slotNumber):
        """ If end of packet set is reached, then continue scheduling
        until all packets are scheduled.

        Args:
            slotNumber (int): the slot number when end of packet
                set is reached
        """
        while not self.checkEmptyQueues():
            self.allotSlots(slotNumber)
            slotNumber += 1

