# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
    Italian E-invoice signed files content extraction.

    There are two methods: OpenSSL and Fallback.
    Sometimes OpenSSL fail in reading signed invoices for some error in the signature itself.
    The Fallback method only has minimal code to extract the invoices' content without verifying the signature itself.
    It's only to be used as a no-requirements fallback for OpenSSL.
"""

import logging
import struct
import warnings
from contextlib import suppress

from OpenSSL import crypto as ssl_crypto
import OpenSSL._util as ssl_util

_logger = logging.getLogger(__name__)


def remove_signature(content, target=None):
    """ Takes a bytestring supposedly PKCS7 signed and returns its PKCS7-data only """
    for removal_strategy in (remove_signature_openssl, remove_signature_fallback):
        if target:
            target.remove_signature_method = removal_strategy.__name__
        with suppress(Exception):
            return removal_strategy(content)

# --------------------------------------------------------------------------------
# UTILS
# --------------------------------------------------------------------------------


def byte_to_bit_array(val):
    """ Convert a byte to an array of zeros and ones """
    return [((val & (1 << pos)) and 1) or 0 for pos in range(7, -1, -1)]


def bit_array_to_byte(val):
    """ Convert an array of zeros and ones to byte """
    value = 0
    max_idx = len(val) - 1
    for i in range(max_idx, -1, -1):
        value += val[i] << max_idx - i
    return value


# --------------------------------------------------------------------------------
# OPENSSL
# --------------------------------------------------------------------------------
def remove_signature_openssl(content):
    """ Remove the PKCS#7 envelope from given content, making a '.xml.p7m' file content readable as it was '.xml'.
        As OpenSSL may not be installed, in that case a warning is issued and None is returned. """

    # Load some tools from the library
    null = ssl_util.ffi.NULL
    verify = ssl_util.lib.PKCS7_verify

    # By default ignore the validity of the certificates, just validate the structure
    flags = ssl_util.lib.PKCS7_NOVERIFY | ssl_util.lib.PKCS7_NOSIGS

    # Read the signed data fron the content
    out_buffer = ssl_crypto._new_mem_buf()

    # This method is deprecated, but there are actually no alternatives
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        loaded_data = ssl_crypto.load_pkcs7_data(ssl_crypto.FILETYPE_ASN1, content)

    # Verify the signature
    if verify(loaded_data._pkcs7, null, null, null, out_buffer, flags) != 1:
        ssl_crypto._raise_current_error()

    # Get the content as a byte-string
    return ssl_crypto._bio_to_string(out_buffer)

# --------------------------------------------------------------------------------
# FALLBACK REMOVE SIGNATURE (ASN1 parse)
# --------------------------------------------------------------------------------


def remove_signature_fallback(content):
    """ The invoice content is inside an ASN1 node identified by PKCS7_DATA_OID (pkcs7-data).
        The node is defined as an OctectString, which can be composed of an arbitrary
        sequence of octects of string data.
        We visit in-order the ASN1 tree nodes until we find the pkcs7-data, then we look for content.
        Once we found it, we read all OctectString that get yielded by the in-order visit..
        When there are no more OctectStrings, then another object will follow
        with its header and identifier, so we stop exploring and just return the content.

        See also:
        https://datatracker.ietf.org/doc/html/rfc2315
        https://www.oss.com/asn1/resources/asn1-made-simple/asn1-quick-reference/octetstring.html
    """
    PKCS7_DATA_OID = '1.2.840.113549.1.7.1'
    result, header_found, data_found = None, False, False
    for node in Reader().build_from_stream(content):
        if node.kind == 'ObjectIdentifier' and node.content == PKCS7_DATA_OID:
            header_found = True
        if header_found and node.kind == 'OctetString':
            data_found = True
            result = (result or b'') + node.content
        elif data_found:
            break

    if not header_found:
        raise Exception("ASN1 Header not found")
    if not data_found:
        raise Exception("ASN1 Content not found")
    return result

# --------------------------------------------------------------------------------
# ASN1 DATA
# --------------------------------------------------------------------------------


universal_tags = {
    0: 'Zero',
    1: 'Boolean',
    2: 'Integer',
    3: 'BitString',
    4: 'OctetString',
    5: 'Null',
    6: 'ObjectIdentifier',
    7: 'ObjectDescriptor',
    8: 'External',
    9: 'Real',
    10: 'Enumerated',
    11: 'EmbeddedPDV',
    12: 'UTF8String',
    13: 'RelativeOid',
    16: 'Sequence',
    17: 'Set',
    18: 'NumericString',
    19: 'PrintableString',
    20: 'TeletexString',
    21: 'VideotexString',
    22: 'IA5String',
    23: 'UTCTime',
    24: 'GeneralizedTime',
    25: 'GraphicString',
    26: 'VisibleString',
    27: 'GeneralString',
    28: 'UniversalString',
    29: 'CharacterString',
    30: 'BMPString',
}

# --------------------------------------------------------------------------------
# NODES (ASN1 parse)
# --------------------------------------------------------------------------------


class Asn1Node:
    """ Base class for Asn1 nodes """
    _content = None

    def __init__(self, kind, start_offset, node_len, cls, parent=None):
        """ Initialization of the Asn1 node """

        if not (parent is None or issubclass(Asn1Node, parent.__class__)):
            raise TypeError("parent must be an Asn1Node or None")

        # Register to parent
        self.parent = parent
        if parent:
            parent.children.append(self)

        self.kind = kind
        self.start_offset = start_offset
        self.children = []
        self.cls = cls
        self.finalized = False
        self.name = self.__class__.__name__.replace('Node', '')
        self.length = node_len

    def finalize(self, end_offset, content=None):
        """ Closes the initialization of the Asn1 node, giving it content and finished length """
        self.content = content
        self.length = end_offset - self.start_offset
        self.end_offset = end_offset
        self.finalized = True

    def total_length(self):
        """ Get the total length of the node if defined. The definition and length bytes must be considered. """
        return self.length + 2 if self.length != "?" else "?"

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, content):
        if content is not None and not isinstance(content, bytes):
            raise TypeError("content must be bytes or None")
        self._content = content


class PrimitiveNode(Asn1Node):
    """ Primitive Asn1 nodes contain pure data """
    pass


class OctetStringNode(PrimitiveNode):
    """ Octet String Asn1 node """
    pass


class ObjectIdentifierNode(PrimitiveNode):
    """ Asn1 Object Identifier, i.e. 1.3.6.1.5.5.7.48.1 """
    @Asn1Node.content.setter
    def content(self, content):
        # Run through the content's bytes
        calc = 0
        result = ''
        for idx, octet in enumerate(content):
            # The first position is treated differently
            if idx == 0:
                result += "%s.%s" % (octet // 40, octet % 40)
                continue

            # Other positions value the less significant 7 bits,
            # but the most significant bit is only negative when there's a break
            calc = (calc << 7) + (octet % 0x80)
            break_it = not bool(octet // 0x80)
            if break_it:
                result += ".%s" % calc
                calc = 0

        self._content = result

# --------------------------------------------------------------------------------
# READER (ASN1 parse)
# --------------------------------------------------------------------------------


class Reader:

    def __init__(self, *args, **kwargs):
        self.clear()

    def clear(self):
        self.offset = 0
        self.root = None
        self.current_node = None
        self.parent_node = None
        self.open_nodes_stack = []
        self.last_open_node = None

    def finalize_last_open_node(self):
        """ Whenever a node is complete, it is finalized, and the references are updated """
        self.last_open_node = self.open_nodes_stack.pop()
        self.last_open_node.finalize(self.offset, None)
        self.parent_node = self.last_open_node.parent
        self.current_node = None
        finalized_node = self.last_open_node
        self.last_open_node = self.open_nodes_stack[-1] if self.open_nodes_stack else None
        return finalized_node

    def build_from_stream(self, stream):
        """ Build an Asn1 tree starting from a byte string from a p7m file """

        self.clear()
        while self.offset < len(stream):

            start_offset = self.offset
            self.last_open_node = self.open_nodes_stack[-1] if self.open_nodes_stack else None

            # Read the definition and length bytes
            definition_byte, self.offset = self.consume('B', stream, self.offset)
            node_len, _bytes_read, self.offset = self.read_length(stream, self.offset)

            if definition_byte == 0 and node_len == 0 and self.open_nodes_stack:
                yield self.finalize_last_open_node()
                continue

            # Create the current Node
            self.current_node = self.create_node(definition_byte, node_len, start_offset, parent=self.parent_node)
            if not self.root:
                self.root = self.current_node

            # If not primitive, add to the stack
            if not issubclass(self.current_node.__class__, PrimitiveNode):
                self.open_nodes_stack.append(self.current_node)
                self.last_open_node = self.current_node
                self.parent_node = self.current_node
            else:
                data, self.offset = self.consume('%ss' % self.current_node.length, stream, self.offset)
                self.current_node.finalize(self.offset, data)
                yield self.current_node

            # Clear the stack of all finished nodes
            while (
                self.last_open_node
                and not self.last_open_node.finalized
                and self.last_open_node.length != '?'
                and self.last_open_node.start_offset + self.last_open_node.total_length() <= self.offset
            ):
                yield self.finalize_last_open_node()

        return self.root

    def consume(self, _format, stream, offset):
        """ Read from a bytes stream to get data out """
        size = struct.calcsize(_format)
        value = struct.unpack_from(_format, stream, offset)[0]
        offset += size
        return value, offset

    def read_length(self, stream, offset):
        """ Returns: (length of the node, bytes read, updated offset) """

        # Read the first byte: if it is zero, it's a special entry.
        # Probably it's the second byte of a closing tag of a node (\x00 \x00 <--)
        first_byte, offset = self.consume('B', stream, offset)
        if first_byte == 0:
            return 0, 1, offset

        # Convert byte to bits
        bits = byte_to_bit_array(first_byte)

        # If the first bit of the first length byte is on
        if not bits[0]:
            return first_byte, 1, offset

        # If it's the only bit being set, the length is indefinite,
        # and the node will terminate with a double \x00
        if not any(bits[1:]):
            return '?', 1, offset

        # We turn off the first bit, and the rest is the number of bytes we have to read
        bytes_read = bit_array_to_byte([0] + bits[1:])

        # Each byte we read is less significant, so we increase the significance of the
        # value we already read and increment by the current byte
        node_len = 0
        for _dummy in range(1, bytes_read + 1):
            current_byte, offset = self.consume('B', stream, offset)
            node_len = (node_len << 8) + current_byte

        return node_len, bytes_read, offset

    def create_node(self, definition_byte, node_len, start_offset, parent=None):
        """ Method to create new Asn1 nodes, given the definition bytes and the offset """

        target_class = Asn1Node
        kind = "Indefinite" if node_len == "?" else "Container"

        node_classes = {
            (0, 0): 'Universal',
            (0, 1): 'Application',
            (1, 0): 'Context-specific',
            (1, 1): 'Private'
        }
        bits = byte_to_bit_array(definition_byte)
        cls_bits = tuple(bits[0:2])
        cls = node_classes[cls_bits]
        if cls == 'Universal':
            is_primitive = not bool(bits[2])
            if is_primitive:
                tag = definition_byte % (1 << 5)
                kind = universal_tags.get(tag)
                if kind:
                    subclasses = PrimitiveNode.__subclasses__()
                    target_classes = {x.__name__: x for x in subclasses}
                    target_class = target_classes.get("%sNode" % kind, PrimitiveNode)

        return target_class(kind, start_offset, node_len, cls, parent)
