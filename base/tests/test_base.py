import pytest
from Simulator import Simulator
from Host import Host, ReliabilityMode
from Router import Router
from Link import Link
from NIC import NIC
from Packet import Packet
from utils_test import setup_topology
    
def test_api_presence_and_types():
    """
    Verifies that the required API methods and attributes exist on all classes 
    used in the tests (Packet, Link, NIC, Router, Host) and return the expected types.
    """
    sim = Simulator()

    pkt = Packet(seq_num=1, payload="A")
    for attr in ['seq_num', 'is_ack', 'payload', 'size']:
        assert hasattr(pkt, attr), f"Missing attribute '{attr}' in Packet."

    link = Link('L1', distance=1000, speed=2e8)
    for method in ['should_lose', 'attach', 'other']:
        assert hasattr(link, method), f"Missing method '{method}' in Link."

    nic = NIC(sim, name='eth0', rate=1e6)
    for method in ['send', 'receive', 'attach', 'set_host', 'get_host', 'queue_depth']:
        assert hasattr(nic, method), f"Missing method '{method}' in NIC."

    router = Router(sim, 'R1')
    for method in ['add_nic', 'receive']:
        assert hasattr(router, method), f"Missing method '{method}' in Router."

    host = Host(sim, 'TestHost', mode=ReliabilityMode.NO_RELIABILITY)
    for method in ['TIMEOUT_DELAY', 'add_nic', 'send_data', 'receive', 'get_received_data', 'get_current_window_size', 'get_total_retransmissions']:
        assert hasattr(host, method), f"Missing method '{method}' in Host."
    assert isinstance(host.get_received_data(), str), "get_received_data must return a string."
    assert isinstance(host.get_current_window_size(), int), "get_current_window_size must return an int."
    assert isinstance(host.get_total_retransmissions(), int), "get_total_retransmissions must return an int."

def test_delay_simulation():
    """
    Verifies that the sending of a packet is simulated, i.e., the receiver's reception
    occurs after the correct amount of time (delay of the packet).
    """
    sim = Simulator()
    nic_a = NIC(sim, 'eth0', rate=1e6)
    
    class DummyHost(Host):
        def __init__(self):
            super().__init__(sim, 'Dummy')
            self.reception_time = 0
        def receive(self, nic, pkt):
            self.reception_time = sim.now()

    class ReceiverNIC(NIC):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.reception_time = 0
        def receive(self, pkt):
            self.reception_time = sim.now()
            
    nic_b = ReceiverNIC(sim, 'eth1', rate=1e6)
    
    link = Link('L1', distance=50e3, speed=2e8)
    link.attach(nic_a)
    link.attach(nic_b)

    pkt = Packet(seq_num=1, payload="A")
    pkt.size = 850e3  # Override size to 5000 bytes for testing
    expected_delay = 6.80025
    
    nic_a.send(pkt)
    sim.run()

    assert nic_b.reception_time == (expected_delay), \
        "Reception time does not match expected delay."

def test_should_lose_hook():
    """
    Verifies that the should_lose hook correctly intercepts and drops 
    a specifically targeted packet based on its payload.
    """
    sim = Simulator()
    nic_a = NIC(sim, 'eth0', rate=1e6)
    
    class ReceiverNIC(NIC):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.received_chars = ""
        def receive(self, pkt):
            self.received_chars += pkt.payload

    class SpecificLossLink(Link):
        def should_lose(self, pkt):
            # We drop the packet containing the letter 'C'
            if not pkt.is_ack and pkt.payload == "C":
                return True
            return False

    nic_b = ReceiverNIC(sim, 'eth1', rate=1e6)

    det_link = SpecificLossLink('L', 100, 2e8)
    det_link.attach(nic_a)
    det_link.attach(nic_b)

    for i, char in enumerate(["A", "B", "C", "D", "E"]):
        nic_a.send(Packet(seq_num=i, payload=char))
    sim.run()

    assert nic_b.received_chars == "ABDE", "The should_lose hook failed to drop exactly payload 'C'."

def test_router_forwarding():
    """
    Verifies that a router successfully forwards a packet from one 
    interface to the other.
    """
    sim = Simulator()
    router = Router(sim, 'R1')
    nic_in = NIC(sim, 'eth0', rate=1e6)
    nic_out = NIC(sim, 'eth1', rate=1e6)
    router.add_nic(nic_in)
    router.add_nic(nic_out)

    class ReceiverNIC(NIC):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.received = False
        def receive(self, pkt):
            self.received = True

    end_nic = ReceiverNIC(sim, 'eth2', rate=1e6)
    link = Link('L1', 10, 2e8)
    link.attach(nic_out)
    link.attach(end_nic)

    router.receive(nic_in, Packet(seq_num=1, payload="X"))
    sim.run()

    assert end_nic.received, "Router failed to forward the packet to the outgoing interface."

def test_queue_saturation():
    """
    Verifies that a NIC with a limited queue correctly drops packets 
    when its capacity is exceeded.
    """
    sim = Simulator()
    nic_out = NIC(sim, 'nic-out', rate=1000, queue_size=5)
    
    for i in range(10):
        nic_out.send(Packet(seq_num=i, payload="X"))
    
    assert nic_out.queue_depth() <= 5, "NIC queue exceeded its maximum defined capacity."

def test_simple_topology_integration():
    """
    Verifies basic end-to-end connectivity.
    """
    sim = Simulator()

    class AssertHost(Host):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.has_received = False
        def receive(self, nic, pkt):
            self.has_received = True

    host_a, host_b, _, _, _ = setup_topology(
        sim, 
        host_b_class=AssertHost
    )
    
    host_a._nic.send(Packet(seq_num=1, payload="Z"))
    sim.run()

    assert host_b.has_received is True, "Packet failed to get through the topology."