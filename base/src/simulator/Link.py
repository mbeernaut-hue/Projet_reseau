from Packet import Packet
from SimulatorEvent import SimulatorEvent


class Link:
    def __init__(self, name: str, distance: float, speed: float):
        self.name=name
        self.distance=distance
        self.speed=speed
        self._nic1 = None
        self._nic2=None

    def attach(self,nic: 'NIC'):
        if self._nic1==None:
            self._nic1=nic
            self._nic1.attach(self)
        elif self._nic2==None:
            self._nic2=nic
            self._nic2.attach(self)    


    def other(self,nic: 'NIC'):
        if nic == self._nic1:
            return self._nic2
        elif nic == self._nic2:
            return self._nic1
        else:
            return None
        
    def should_lose(self, pkt: Packet) -> bool :
        return False
    #a modifier plus tard