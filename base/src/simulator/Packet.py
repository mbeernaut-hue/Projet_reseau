from PacketType import PacketType


class Packet:
    def __init__(self, seq_num: int, type: PacketType = PacketType.DATA, payload:str = "") :
        self.seq_num=seq_num
        self.is_ack=(type == PacketType.ACK)
        self.type=type
        self.payload=payload
        self.size=len(payload)#a modifier plus tard

    def __repr__(self):
        return f"Pkt({self.seq_num})"
