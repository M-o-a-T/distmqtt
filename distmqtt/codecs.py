# Copyright (c) 2015 Nicolas JOUANIN
#
# See the file license.txt for copying permission.
import anyio
from struct import pack, unpack
from distmqtt.errors import NoDataException

# Collection of basic codecs for the messages' payload

import msgpack

def bytes_to_hex_str(data):
    """
    converts a sequence of bytes into its displayable hex representation, ie: 0x??????
    :param data: byte sequence
    :return: Hexadecimal displayable representation
    """
    return '0x' + ''.join(format(b, '02x') for b in data)


def bytes_to_int(data):
    """
    convert a sequence of bytes to an integer using big endian byte ordering
    :param data: byte sequence
    :return: integer value
    """
    return int.from_bytes(data, byteorder='big')


def int_to_bytes(int_value: int, length: int) -> bytes:
    """
    convert an integer to a sequence of bytes using big endian byte ordering
    :param int_value: integer value to convert
    :param length: (optional) byte length
    :return: byte sequence
    """
    if length == 1:
        fmt = "!B"
    elif length == 2:
        fmt = "!H"
    return pack(fmt, int_value)


async def read_or_raise(reader, n=-1):
    """
    Read a given byte number from Stream. NoDataException is raised if read gives no data
    :param reader: reader adapter
    :param n: number of bytes to read
    :return: bytes read
    """
    try:
        data = await reader.read(n)
    except (anyio.exceptions.IncompleteRead, ConnectionResetError):
        data = None
    if not data:
        raise NoDataException("No more data")
    return data


async def decode_string(reader) -> bytes:
    """
    Read a string from a reader and decode it according to MQTT string specification
    :param reader: Stream reader
    :return: UTF-8 string read from stream
    """
    return (await decode_data_with_length(reader)).decode("utf-8")


async def decode_data_with_length(reader) -> bytes:
    """
    Read data from a reader. Data is prefixed with 2 bytes length
    :param reader: Stream reader
    :return: bytes read from stream (without length)
    """
    length_bytes = await read_or_raise(reader, 2)
    bytes_length = unpack("!H", length_bytes)
    data = await read_or_raise(reader, bytes_length[0])
    return data


def encode_string(string: str) -> bytes:
    return encode_data_with_length(string.encode("utf-8"))


def encode_data_with_length(data: bytes) -> bytes:
    data_length = len(data)
    return int_to_bytes(data_length, 2) + data


async def decode_packet_id(reader) -> int:
    """
    Read a packet ID as 2-bytes int from stream according to MQTT specification (2.3.1)
    :param reader: Stream reader
    :return: Packet ID
    """
    packet_id_bytes = await read_or_raise(reader, 2)
    packet_id = unpack("!H", packet_id_bytes)
    return packet_id[0]


def int_to_bytes_str(value: int) -> bytes:
    """
    Converts a int value to a bytes array containing the numeric character.
    Ex: 123 -> b'123'
    :param value: int value to convert
    :return: bytes array
    """
    return str(value).encode('utf-8')



class NoopCodec:
    """A codec that does nothing.

    Your payload needs to consist of bytes.
    """

    @staticmethod
    def encode(data):
        assert isinstance(data, bytes)
        return data

    @staticmethod
    def decode(data):
        return data


class UTF8Codec:
    """A codec that translates to UTF-8 strings.

    Your payload needs to be a single string.

    This codec will *not* stringify other data types for you.
    """

    @staticmethod
    def encode(data):
        return data.encode("utf-8")

    @staticmethod
    def decode(data):
        return data.decode("utf-8")


class MsgPackCodec:
    """A codec that encodes to "msgpack"-encoded bytestring.

    Your payload must consist of whatever "msgpack" accepts.

    Args:
      ``use_bin_type``: Bytestrings are encoded as byte arrays.
                        Defaults to ``True``. If ``False``,
                        bytes are transmitted as string types and input
                        strings are not UTF8-decoded. Use this if your
                        network contains clients which use
                        non-UTF8-encoded strings (this violates the
                        MsgPack specification).
      ``use_list``: if ``True``, lists and tuples are returned as lists
                    (i.e. modifyable). Defaults to ``False``, which uses
                    immutable tuples (this is faster).
    """

    use_bin_type = True
    use_list = False

    def __init__(self, use_bin_type=None, use_list=None):
        if use_bin_type is not None:
            self.use_bin_type = use_bin_type
        if use_list is not None:
            self.use_list = use_list

    def encode(self, data):
        return msgpack.packb(data, use_bin_type=self.use_bin_type)

    def decode(self, data):
        return msgpack.unpackb(data, raw=not self.use_bin_type, use_list=self.use_list)
        # raw=False would try to decode input bytes, which is not what you
        # want when the input is a bytestring. So we only use that if
        # bytestring input has been marked as such.

