from queue import Queue

from Event import Event
from NIC import NIC
from Packet import Packet
from PacketType import PacketType
from ReliabilityMode import ReliabilityMode
from SimulatedEntity import SimulatedEntity
from Simulator import Simulator


class Host(SimulatedEntity):
    def __init__(self, sim: Simulator, name: str, mode: ReliabilityMode):
        super().__init__(sim,name)
        self.mode=mode
        self.TIMEOUT_DELAY=5
        self._nic=None
        self.received_data={}
        self.total_retransmissions=0
        self.window={}
        self.ACK_expected=0
        self.packets_to_send=Queue()
        self.seq_to_use=0
        self.seq_expected=0
        self.window_size= 100
    
    
    def add_nic(self, nic: NIC) :
        if self._nic is None:
            self._nic=nic
            self._nic.set_host(self)

    def send_data(self, data:str) :
        self.seq_to_use=0
        self.seq_expected=0
        self.total_retransmissions=0
        self.ACK_expected=0
        if self.mode ==ReliabilityMode.NO_RELIABILITY :
            for c in data:
                pkt = Packet(self.seq_to_use, payload=c)
                self._nic.send(pkt)
                self.seq_to_use+=1
        if self.mode ==ReliabilityMode.ACKNOWLEDGES :
            for c in data:
                self.packets_to_send.put(c)
            pkt = Packet(self.seq_to_use, payload=self.packets_to_send.get())
            self._nic.send(pkt)
            self.seq_to_use+=1
        if self.mode ==ReliabilityMode.ACKNOWLEDGES_WITH_RETRANSMISSION :
            for c in data:
                self.packets_to_send.put(c)
            pkt = Packet(self.seq_to_use, payload=self.packets_to_send.get())
            timeOut_evt= Event(ctx=pkt, callback=self.check_retransmission)
            self._sim.add_event(timeOut_evt,self.TIMEOUT_DELAY)
            self._nic.send(pkt)
            self.seq_to_use+=1
        if self.mode == ReliabilityMode.PIPELINING_FIXED_WINDOW:
            for c in data:
                self.packets_to_send.put(c)
            while self.get_current_window_size() < self.window_size and not self.packets_to_send.empty():
                payload_ = self.packets_to_send.get()
                pkt_ = Packet(self.seq_to_use, payload=payload_)
                self.window[self.seq_to_use] = pkt_
                self.seq_to_use += 1
                timeOut_evt = Event(ctx=pkt_, callback=self.check_retransmission_cumul)
                self._sim.add_event(timeOut_evt, self.TIMEOUT_DELAY)
                self._nic.send(pkt_)
        
    def check_retransmission(self,pkt: Packet):
        if pkt.seq_num>=self.ACK_expected:
            timeOut_evt= Event(ctx=pkt, callback=self.check_retransmission)
            self._sim.add_event(timeOut_evt,self.TIMEOUT_DELAY)
            self._nic.send(pkt)
            self.total_retransmissions+=1
    
    def check_retransmission_cumul(self, pkt: Packet):
        if len(self.window)==0:
            return
        oldest_seq = min(self.window.keys())
        if pkt.seq_num == oldest_seq:
                self._nic.send(pkt)
                timeOut_evt = Event(ctx=pkt, callback=self.check_retransmission_cumul)
                self._sim.add_event(timeOut_evt, self.TIMEOUT_DELAY)
                self.total_retransmissions += 1

    def receive(self, nic:NIC,pkt: Packet):
        if self.mode ==ReliabilityMode.NO_RELIABILITY:
                self.received_data[pkt.seq_num]=pkt.payload

        if self.mode==ReliabilityMode.ACKNOWLEDGES :
            if pkt.is_ack==True:
                if not self.packets_to_send.empty():
                    pkt_ = Packet(self.seq_to_use, payload=self.packets_to_send.get())   
                    self.seq_to_use+=1     
                    nic.send(pkt_)
            else:
                self.received_data[pkt.seq_num]=pkt.payload
                ack = Packet(pkt.seq_num, type=PacketType.ACK)
                nic.send(ack)
                
        if self.mode==ReliabilityMode.ACKNOWLEDGES_WITH_RETRANSMISSION :
            if pkt.is_ack==True:
                if pkt.seq_num==self.ACK_expected:
                    self.ACK_expected+=1
                    if not self.packets_to_send.empty():
                        pkt_ = Packet(self.seq_to_use, payload=self.packets_to_send.get())   
                        self.seq_to_use+=1
                        timeOut_evt= Event(ctx=pkt_, callback=self.check_retransmission)
                        self._sim.add_event(timeOut_evt,self.TIMEOUT_DELAY)    
                        nic.send(pkt_)
            else:
                self.received_data[pkt.seq_num]=pkt.payload
                ack = Packet(pkt.seq_num, type=PacketType.ACK)
                nic.send(ack)
        
        if self.mode == ReliabilityMode.PIPELINING_FIXED_WINDOW:
            if pkt.is_ack == True:
                seq_to_remove = []
                if pkt.seq_num>=self.ACK_expected:
                    self.ACK_expected=pkt.seq_num+1
                    for seq in self.window.keys():
                        if seq <= pkt.seq_num:
                            seq_to_remove.append(seq)
                    for seq in seq_to_remove:
                        del self.window[seq]
                    while self.get_current_window_size() < self.window_size and not self.packets_to_send.empty():
                        pkt_ = Packet(self.seq_to_use, payload=self.packets_to_send.get())
                        self.window[self.seq_to_use] = pkt_
                        self.seq_to_use += 1
                        timeOut_evt = Event(ctx=pkt_, callback=self.check_retransmission_cumul)
                        self._sim.add_event(timeOut_evt, self.TIMEOUT_DELAY)
                        nic.send(pkt_)
            else:
                self.received_data[pkt.seq_num] = pkt.payload
                while self.seq_expected in self.received_data:
                    self.seq_expected += 1
                ack = Packet(self.seq_expected - 1, type=PacketType.ACK)
                nic.send(ack)




    def get_received_data(self) -> str:
        msg = ""
        if self.mode!=ReliabilityMode.PIPELINING_FIXED_WINDOW :
            for i in self.received_data.keys():
                msg += self.received_data[i]
            self.received_data={}
            return msg
        else:
            seq_to_take=0
            while seq_to_take in self.received_data:
                msg += self.received_data[seq_to_take]
                del self.received_data[seq_to_take]
                seq_to_take+= 1  
            return msg
    
    def get_current_window_size(self) -> int :
        return len(self.window)
    
    def get_total_retransmissions(self) -> int :
        return self.total_retransmissions