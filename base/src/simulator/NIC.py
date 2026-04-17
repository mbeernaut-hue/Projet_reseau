from Event import Event
from Packet import Packet
from PacketType import PacketType
from SimulatedEntity import SimulatedEntity
from queue import Queue

from Simulator import Simulator
from SimulatorEvent import SimulatorEvent

class NIC(SimulatedEntity):
    def __init__(self, sim: 'Simulator', name: str, rate: float, queue_size: int = 100):
        super().__init__(sim,name)
        self._rate=rate
        self._queue_size=queue_size
        self.queue_send= Queue(maxsize=self._queue_size)
        self.link=None
        self.host=None
        self.busy=False
    

    def send(self,pkt: 'Packet') :
        if self.link!=None :
            if self.link.should_lose(pkt):
                self.info(f"le paquet doit etre perdu")
                return
            if self.queue_depth()<self._queue_size:
                self.info(f"envoi du paquet dans la file")
                self.queue_send.put(pkt)
                self.info(f"Paquet mis en file d'attente")
                if self.busy==False:
                    self.info("Lien accessible, envoie du paquet immédiat")
                    self.send_packet_list()
            else:
                self.info(f"Paquet perdu : file d'attente pleine")

    def send_packet_list(self) :
        if self.link!=None :
            if not self.queue_send.empty():
                paquet=self.queue_send.get()
                self.info(f"on récupère le premier paquet de la file et on l'envoi sur le lien")
                self.busy=True
                self.info(f"transmission d'un paquet")
                if paquet.type == PacketType.DATA :
                    liberation_evt = Event(ctx=None, callback=self.end_tx)
                    t_tx = (paquet.size * 8) / self._rate
                    self._sim.add_event(liberation_evt, t_tx)
                    self.transmit(paquet)
                else:
                    self.info(f"transmission de l'ack a l'hote")
                    end_propa_evt = Event(ctx=paquet, callback=self.end_propa)
                    t_prop = self.link.distance / self.link.speed
                    self._sim.add_event(end_propa_evt,t_prop)


    def transmit(self,pkt:'Packet') :
        self.info(f'transmission du paquet le long du lien')
        end_propa_evt= Event(ctx=pkt, callback=self.end_propa)
        t_prop = self.link.distance / self.link.speed
        t_tx = (pkt.size * 8) / self.link.other(self)._rate
        self._sim.add_event(end_propa_evt,t_prop + t_tx)
    
    def end_propa(self,pkt:'Packet') :
        self.info(f"Propagation du paquet terminé et arrivé du dernier bit sur l'interface réseau destinataire")
        self.link.other(self).receive(pkt)

    def end_tx(self, ctx):
        self.busy = False
        self.info("Transmission finie, NIC libre.")
        self.send_packet_list()
        
    
    def receive(self,pkt: 'Packet') :
        self.host.receive(self, pkt)

    def attach(self, link: 'Link') :
        if self.link==None:
            self.link=link
    
    def set_host(self, host) :
        if self.host==None:
            self.host=host
    

    def get_host(self): 
        return self.host

    def queue_depth(self) -> int :
        return self.queue_send.qsize()