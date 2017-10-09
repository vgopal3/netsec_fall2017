""""Packets"""

import zlib
import struct
import asyncio
import logging
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT32, UINT8, UINT16, STRING, BUFFER, BOOL
from playground.network.packet.fieldtypes.attributes import Optional

# Comment out this block when you don't want to be distracted by logs
# loop = asyncio.get_event_loop()
# loop.set_debug(enabled=True)
# logging.getLogger().setLevel(logging.NOTSET)  # this logs everything going on
# logging.getLogger().addHandler(logging.StreamHandler())


class CheckUsername(PacketType):
    DEFINITION_IDENTIFIER = "CheckUsername Packet"
    DEFINITION_VERSION = "1.0"
    FIELDS = [("username", STRING)]


class UsernameAvailability(PacketType):
    DEFINITION_IDENTIFIER = "UsernameAvailability Packet"
    DEFINITION_VERSION = "1.0"
    FIELDS = [("username_availability", BOOL)]


class SignUpRequest(PacketType):
    DEFINITION_IDENTIFIER = "SignUpRequest Packet"
    DEFINITION_VERSION = "1.0"
    FIELDS = [("username", STRING), ("password", STRING), ("email", STRING)]


class SignUpResult(PacketType):
    DEFINITION_IDENTIFIER = "SignUpResult Packet"
    DEFINITION_VERSION = "1.0"
    FIELDS = [("result", BOOL), ("user_id", UINT32)]


class PEEPPacket(PacketType):
    DEFINITION_IDENTIFIER = "PEEP.Packet"
    DEFINITION_VERSION = "1.0"
    
    FIELDS = [
        ("Type", UINT8),
        ("SequenceNumber", UINT32({Optional: True})),
        ("Checksum", UINT16),
        ("Acknowledgement", UINT32({Optional: True})),
        ("Data", BUFFER({Optional: True}))
    ]

    def to_string(self):
        seqNum = self.SequenceNumber
        if seqNum == self.UNSET:
            seqNum = "-"

        ackNum = self.Acknowledgement
        if ackNum == self.UNSET:
            ackNum = "-"

        dataLen = self.dataoffset()
        return "(): SEQ({}), ACK({}), Checksum({}), Data Length({})".format(self.packetType(), seqNum, ackNum, self.Checksum, dataLen)
    
    def calculateChecksum(self):
        oldChecksum = self.Checksum
        self.Checksum = 0
        bytes = self.__serialize__()
        self.Checksum = oldChecksum
        return zlib.adler32(bytes) & 0xffff
    
    def updateChecksum(self):
        self.Checksum = self.calculateChecksum()
    
    def verifyChecksum(self):
        return self.Checksum == self.calculateChecksum()

# PEEP Protocol Types
# -------------------
# SYN -      TYPE 0
# SYN-ACK -  TYPE 1
# ACK -      TYPE 2
# RIP -      TYPE 3
# RIP-ACK -  TYPE 4
# DATA -     TYPE 5



