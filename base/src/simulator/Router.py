from NIC import NIC
from Packet import Packet
from SimulatedEntity import SimulatedEntity
from Simulator import Simulator


class Router(SimulatedEntity):
    def __init__(self, sim: Simulator, name: str):
        super().__init__(sim,name)
        self._nics=[]
    
    def add_nic(self, nic: NIC):
        if nic not in self._nics:
            self._nics.append(nic)
            nic.set_host(self)
    
    def receive(self, nic: NIC, pkt: Packet) :
        for n in self._nics:
            if n!=nic:
                n.send(pkt)