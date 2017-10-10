"""Transport"""

from playground.network.common import StackingTransport
from . import Packets


class MyProtocolTransport(StackingTransport):
    def write(self, data):
        # this will be the data from the upper layer
        chunk_size = 1024
        counter = 0
        my_protocol_packets = []
        while len(data) > 0:
            pkt = Packets.PEEPPacket()
            pkt.Type = 5
            pkt.SequenceNumber = counter
            pkt.Acknowledgement = 0
            if len(data) > chunk_size:
                pkt.Data = data[:chunk_size]
                data = data[chunk_size:]
            else:
                pkt.Data = data[:len(data)]
                data = data[len(data):]
            pkt.Checksum = pkt.calculateChecksum()
            counter = counter + 1
            my_protocol_packets.append(pkt)

        # Create MyProtocolPackets
        for pkt in my_protocol_packets:
            self.lowerTransport().write(pkt.__serialize__())

