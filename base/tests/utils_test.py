from Host import Host, ReliabilityMode
from Router import Router
from Link import Link
from NIC import NIC

def setup_topology(sim, 
                   mode=ReliabilityMode.NO_RELIABILITY,
                   host_a_class=Host, host_b_class=Host,
                   nic_a_class=NIC, nic_b_class=NIC,
                   link1_class=Link, link2_class=Link):
    """
    Creates a standard A -> R1 -> B topology.
    Allows injecting custom classes for testing purposes.
    """
    host_a = host_a_class(sim, 'A', mode=mode)
    host_b = host_b_class(sim, 'B', mode=mode)
    router = Router(sim, 'R1')

    nic_a = nic_a_class(sim, name='eth0', rate=1e6)
    nic_b = nic_b_class(sim, name='eth0', rate=1e6)
    nic_r1_a = NIC(sim, name='eth0', rate=5e5)
    nic_r1_b = NIC(sim, name='eth1', rate=5e5)

    host_a.add_nic(nic_a)
    host_b.add_nic(nic_b)
    router.add_nic(nic_r1_a)
    router.add_nic(nic_r1_b)

    link_a_r1 = link1_class('L1', distance=1000, speed=2e8)
    link_r1_b = link2_class('L2', distance=1000, speed=2e8)

    link_a_r1.attach(nic_a)
    link_a_r1.attach(nic_r1_a)
    link_r1_b.attach(nic_r1_b)
    link_r1_b.attach(nic_b)

    return host_a, host_b, router, link_a_r1, link_r1_b