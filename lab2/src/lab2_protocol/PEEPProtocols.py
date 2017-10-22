"""Protocols"""

import random, threading, time
from . import Transport
from .Packets import PEEPPacket
from playground.network.packet import PacketType
from playground.network.common import StackingProtocol


class resendThread(threading.Thread):
    def __init__(self, threadID, name, func):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.func = func

    def run(self):
        print("Starting " + self.name)
        self.func()
        print("Exiting " + self.name)


class terminationThread(threading.Thread):
    def __init__(self, threadID, name, func):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.counter = 5
        self.name = name
        self.func = func

    def run(self):
        print("Starting " + self.name)
        self.func()
        print("Exiting " + self.name)


class PEEPProtocol(StackingProtocol):
    def __init__(self):
        self.deserializer = PacketType.Deserializer()
        self.state = 0
        self.counter = 5
        random.seed()
        self.valid_sent = random.randrange(0, 4294967295)
        self.valid_received = 0
        self.thread1 = resendThread(1, "Thread-1", self.resend)
        self.thread2 = terminationThread(1, "Thread-2", self.termination)
        super().__init__()

    def termination(self):
        while self.counter:
            print("Session ends in ", self.counter, " sec.")
            self.counter = self.counter - 1
            time.sleep(1)
        self.state = 5

    def resend(self):
        while self.state!=5:
            print("Resend checking")
            time.sleep(1)

    def connection_lost(self, exc):
        print("PEEPServer: Lost connection to client. Cleaning up.")
        self.transport = None
        self.higherProtocol().connection_lost()


class PEEPServerProtocol(PEEPProtocol):

    def connection_made(self, transport):
        print("PEEPServer: Received a connection from {}".format(transport.get_extra_info("peername")))
        self.transport = transport
        self.thread1.start()
        self.thread2.start()

    def data_received(self, data):
        self.counter = 5
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, PEEPPacket) and pkt.validate_checksum():
                print("PEEPServer: Received PEEP packet.", pkt.to_string())
                if pkt.get_type_string() == "SYN" and self.state == 0:
                    self.state = 1
                    packet_response = PEEPPacket.set_synack(self.valid_sent, pkt.SequenceNumber + 1)
                    packet_response_bytes = packet_response.__serialize__()
                    self.valid_sent = self.valid_sent + 1
                    print("PEEPServer: Sending PEEP packet.", packet_response.to_string())
                    self.transport.write(packet_response_bytes)
                elif pkt.get_type_string() == "ACK" and self.state == 1:
                    self.state = 2
                    # Only when handshake is completed should we call higher protocol's connection_made
                    print("PEEPServer: Handshake is completed.")
                    higher_transport = Transport.MyProtocolTransport(self.transport)
                    higher_transport.seq_start(self.valid_sent)
                    higher_transport.reset_all()
                    self.higherProtocol().connection_made(higher_transport)
                elif pkt.get_type_string() == "DATA" and self.state == 2:
                    # Only when handshake is completed should we call higher protocol's data_received
                    packet_response = PEEPPacket.set_ack(pkt.SequenceNumber + len(pkt.Data))
                    packet_response_bytes = packet_response.__serialize__()
                    print("PEEPServer: Sending PEEP packet.", packet_response.to_string())
                    self.transport.write(packet_response_bytes)
                    print("PEEPServer: Data passes up PEEPServerProtocol.")
                    self.higherProtocol().data_received(pkt.Data)
                elif pkt.get_type_string() == "ACK" and self.state == 2:
                    if pkt.Acknowledgement > self.valid_sent:
                        self.valid_sent = pkt.Acknowledgement
                elif pkt.get_type_string() == "RIP":
                    packet_response = PEEPPacket.set_ripack(pkt.SequenceNumber + 1)
                    packet_response_bytes = packet_response.__serialize__()
                    self.transport.write(packet_response_bytes)
                    print("PEEPServer: Lost connection to PEEPClient. Cleaning up.")
                    self.state = 4
                    self.transport = None
                else:
                    self.state = 0
                    self.transport = None
                    break


class PEEPClientProtocol(PEEPProtocol):

    def connection_made(self, transport):
        print("PEEPClient: Connection established with server")
        self.transport = transport
        self.thread1.start()
        self.thread2.start()
        self.handshake()

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, PEEPPacket) and pkt.validate_checksum():
                print("PEEPClient: Received PEEP packet.", pkt.to_string())
                if pkt.get_type_string() == "SYN-ACK" and self.state == 1:
                    packet_response = PEEPPacket.set_ack(pkt.SequenceNumber + 1)
                    response_bytes = packet_response.__serialize__()
                    self.expecting_receive = pkt.SequenceNumber + 1
                    self.valid_sent = pkt.Acknowledgement
                    print("PEEPClient: Sending PEEP packet.", packet_response.to_string())
                    self.transport.write(response_bytes)
                    self.state = 2
                    # Only when handshake is completed should we call higher protocol's connection_made
                    print("PEEPClient: Handshake is completed.")
                    higher_transport = Transport.MyProtocolTransport(self.transport)
                    higher_transport.seq_start(self.valid_sent)
                    higher_transport.reset_all()
                    self.higherProtocol().connection_made(higher_transport)
                elif pkt.get_type_string() == "DATA" and self.state == 2:
                    # Only when handshake is completed should we call higher protocol's data_received
                    packet_response = PEEPPacket.set_ack(pkt.SequenceNumber + len(pkt.Data))
                    packet_response_bytes = packet_response.__serialize__()
                    print("PEEPClient: Sending PEEP packet.", packet_response.to_string())
                    self.transport.write(packet_response_bytes)
                    print("PEEPClient: Data passes up PEEPClientProtocol.")
                    self.higherProtocol().data_received(pkt.Data)
                elif pkt.get_type_string() == "ACK" and self.state == 2:
                    if pkt.Acknowledgement > self.valid_sent:
                        self.valid_sent = pkt.Acknowledgement
                elif pkt.get_type_string() == "RIP":
                    packet_response = PEEPPacket.set_ripack(pkt.SequenceNumber + 1)
                    packet_response_bytes = packet_response.__serialize__()
                    self.transport.write(packet_response_bytes)
                    print("PEEPClient: Lost connection to PEEPServer. Cleaning up.")
                    self.state = 4
                    self.transport = None
                else:
                    self.state = 0
                    self.transport = None
                    break


    def handshake(self):
        packet_response = PEEPPacket.set_syn(self.valid_sent)
        response_bytes = packet_response.__serialize__()
        print("PEEPClient: Starting handshake. Sending PEEP packet.", packet_response.to_string())
        self.transport.write(response_bytes)
        self.state = 1
