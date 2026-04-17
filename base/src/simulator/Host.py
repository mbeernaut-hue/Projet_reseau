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
        self.TIMEOUT_DELAY=5 #en attendant
        self._nic=None
        self.received_data={}
        self.total_retransmissions=0
        self.window={}
        self.ACK_expected=0
        self.packets_to_send=Queue()
        self.seq_to_use=0
    


    def add_nic(self, nic: NIC) :
        if self._nic is None:
            self._nic=nic
            self._nic.set_host(self)

    def send_data(self, data:str) :
        self.seq_to_use=0
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
        if self.mode ==ReliabilityMode.PIPELINING_FIXED_WINDOW :
            pass   
        
    def check_retransmission(self,pkt: Packet):
        if pkt.seq_num<=self.ACK_expected:
            self._nic.send(pkt)
            self.total_retransmissions+=1

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
                if not self.packets_to_send.empty():
                    if pkt.seq_num==self.ACK_expected:
                        self.ACK_expected+=1
                        pkt_ = Packet(self.seq_to_use, payload=self.packets_to_send.get())   
                        self.seq_to_use+=1    
                        nic.send(pkt_)
            else:
                self.received_data[pkt.seq_num]=pkt.payload
                ack = Packet(pkt.seq_num, type=PacketType.ACK)
                nic.send(ack)






    def get_received_data(self) -> str:
        msg = ""
        for i in self.received_data.keys():
            msg += self.received_data[i]
        self.received_data={}
        return msg
    
    def get_current_window_size(self) -> int :
        return len(self.window)
    
    def get_total_retransmissions(self) -> int :
        return self.total_retransmissions