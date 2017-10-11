"""Protocols"""

import random
from . import Transport
from .Packets import PEEPPacket
from playground.network.packet import PacketType
from playground.network.common import StackingProtocol


class PEEPServerProtocol(StackingProtocol):
    def __init__(self):
        self.deserializer = PacketType.Deserializer()
        self.state = 0
        random.seed()
        self.valid_sent = random.randrange(0, 4294967295)
        self.valid_received = 0
        super().__init__()

    def connection_made(self, transport):
        print("PEEPServer: Received a connection from {}".format(transport.get_extra_info("peername")))
        self.transport = transport

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, PEEPPacket) and pkt.is_checksum_legit():
                print("PEEPServer: Received PEEP packet.", pkt.to_string())
                if pkt.get_type_string() == "SYN" and self.state == 0:
                    self.state = 1
                    packet_response = PEEPPacket.set_synack(self.valid_sent, pkt.SequenceNumber + 1)
                    packet_response.Type = 1  # SYN-ACK
                    #packet_response.SequenceNumber = self.valid_sent
                    #packet_response.Acknowledgement = pkt.SequenceNumber + 1
                    #packet_response.Checksum = packet_response.calculateChecksum()
                    packet_response_bytes = packet_response.__serialize__()
                    print("PEEPServer: Sending PEEP packet.", packet_response.to_string())
                    self.transport.write(packet_response_bytes)
                elif pkt.get_type_string() == "ACK" and self.state == 1:
                    self.state = 2
                    # Only when handshake is completed should we call higher protocol's connection_made
                    print("PEEPServer: Handshake is completed.")
                    higher_transport = Transport.MyProtocolTransport(self.transport)
                    higher_transport.seq_start(self.valid_sent)
                    self.higherProtocol().connection_made(higher_transport)
                elif pkt.get_type_string() == "DATA" and self.state == 2:
                    # Only when handshake is completed should we call higher protocol's data_received
                    packet_response = PEEPPacket.set_ack(pkt.SequenceNumber + len(pkt.Data))
                    #packet_response.Type = 2  # ACK
                    #packet_response.Acknowledgement = pkt.SequenceNumber + len(pkt.Data)
                    #packet_response.Checksum = packet_response.calculateChecksum()
                    packet_response_bytes = packet_response.__serialize__()
                    print("PEEPServer: Sending PEEP packet.", packet_response.to_string())
                    self.transport.write(packet_response_bytes)
                    print("PEEPServer: Data passes up PEEPServerProtocol.")
                    self.higherProtocol().data_received(pkt.Data)
                elif pkt.get_type_string() == "ACK" and self.state == 2:
                    if pkt.Acknowledgement > self.valid_sent:
                        self.valid_sent = pkt.Acknowledgement
                elif pkt.get_type_string() == "RIP":
                    packet_response = PEEPPacket.set_ripack(pkt.SequenceNumber+1)
                    #packet_response.Type = 4  # RIP-ACK
                    #packet_response.SequenceNumber = 0
                    #packet_response.Acknowledgement = 0
                    #packet_response.Checksum = packet_response.calculateChecksum()
                    packet_response_bytes = packet_response.__serialize__()
                    self.transport.write(packet_response_bytes)
                    print("PEEPServer: Lost connection to PEEPClient. Cleaning up.")
                    self.state = 0
                    self.transport = None
                else:
                    self.state = 0
                    self.transport = None
                    break

    def connection_lost(self, exc):
        print("PEEPServer: Lost connection to client. Cleaning up.")
        self.transport = None
        self.higherProtocol().connection_lost()


class PEEPClientProtocol(StackingProtocol):
    def __init__(self):
        self.deserializer = PacketType.Deserializer()
        self.state = 0
        random.seed()
        self.valid_sent = random.randrange(0, 4294967295)
        self.expecting_receive = 0
        super().__init__()

    def connection_made(self, transport):
        print("PEEPClient: Connection established with server")
        self.transport = transport
        self.handshake()

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, PEEPPacket) and pkt.is_checksum_legit():
                print("PEEPClient: Received PEEP packet.", pkt.to_string())
                if pkt.get_type_string() == "SYN-ACK" and self.state == 1:
                    packet_response = PEEPPacket.set_ack(pkt.SequenceNumber + 1)
                    #packet_response.Acknowledgement = pkt.SequenceNumber + 1
                    #packet_response.Checksum = packet_response.calculateChecksum()
                    response_bytes = packet_response.__serialize__()
                    self.expecting_receive = pkt.SequenceNumber + 1
                    print("PEEPClient: Sending PEEP packet.", packet_response.to_string())
                    self.transport.write(response_bytes)
                    self.state = 2
                    # Only when handshake is completed should we call higher protocol's connection_made
                    print("PEEPClient: Handshake is completed.")
                    higher_transport = Transport.MyProtocolTransport(self.transport)
                    higher_transport.seq_start(self.valid_sent)
                    self.higherProtocol().connection_made(higher_transport)
                elif pkt.get_type_string() == "DATA" and self.state == 2:
                    # Only when handshake is completed should we call higher protocol's data_received
                    packet_response = PEEPPacket.set_ack(pkt.SequenceNumber + len(pkt.Data))
                    #packet_response.Type = 2  # ACK
                    #packet_response.Acknowledgement = pkt.SequenceNumber + len(pkt.Data)
                    #packet_response.Checksum = packet_response.calculateChecksum()
                    packet_response_bytes = packet_response.__serialize__()
                    print("PEEPServer: Sending PEEP packet.", packet_response.to_string())
                    self.transport.write(packet_response_bytes)
                    print("PEEPClient: Data passes up PEEPClientProtocol.")
                    self.higherProtocol().data_received(pkt.Data)
                elif pkt.get_type_string() == "ACK" and self.state == 2:
                    if pkt.Acknowledgement > self.valid_sent:
                        self.valid_sent = pkt.Acknowledgement
                elif pkt.get_type_string() == "RIP":
                    packet_response = PEEPPacket.set_ripack(pkt.SequenceNumber+1)
                    #packet_response.Type = 4  # RIP-ACK
                    #packet_response.SequenceNumber = 0  # why SequenceNumber = 0
                    #packet_response.Acknowledgement = 0  # why AcknowledgementNumber = 0
                    #packet_response.Checksum = packet_response.calculateChecksum()
                    packet_response_bytes = packet_response.__serialize__()
                    self.transport.write(packet_response_bytes)
                    print("PEEPClient: Lost connection to PEEPServer. Cleaning up.")
                    self.state = 0
                    self.transport = None
                else:
                    self.state = 0
                    self.transport = None
                    break

    def connection_lost(self, exc):
        print("PEEPClient: Connection lost in PEEPClientProtocol")
        self.transport = None
        self.higherProtocol().connection_lost()

    def handshake(self):
        packet_response = PEEPPacket.set_syn(self.valid_sent)
        #packet_response.Type = 0  # SYN
        #packet_response.SequenceNumber = self.valid_sent
        #packet_response.Checksum = packet_response.calculateChecksum()
        response_bytes = packet_response.__serialize__()
        print("PEEPClient: Starting handshake. Sending PEEP packet.", packet_response.to_string())
        self.transport.write(response_bytes)
        self.state = 1