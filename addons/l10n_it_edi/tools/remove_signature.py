"""
    Italian E-invoice signed files content extraction.

    - PyOpenSSL doesn't support ``load_pkcs7_data`` anymore.
      https://github.com/pyca/pyopenssl/commit/0fe822dc8d6610b8ec9ebaff626d6bf23e0a7ad3
    - Cryptography is migrating PKCS7_verify to Rust, and has removed PKCS7_NOVERIFY
      https://github.com/pyca/cryptography/commit/615967bfab5b49e470fe7d0df44649c69fb9a847
      https://github.com/pyca/cryptography/pull/8332
    - ``asn1`` library is pure Python and MIT licensed, but is slower than our homemade solution
      https://github.com/andrivet/python-asn1/blob/master/src/asn1.py

    This version is more optimized than what we had as a fallback.
"""


from contextlib import suppress


PKCS7_DATA_OID = '1.2.840.113549.1.7.1'
universal_tags = [
    'Zero', 'Boolean', 'Integer', 'BitString', 'OctetString',
    'Null', 'ObjectIdentifier', 'ObjectDescriptor', 'External', 'Real',
    'Enumerated', 'EmbeddedPDV', 'UTF8String', 'RelativeOid', None,
    None, 'Sequence', 'Set', 'NumericString', 'PrintableString',
    'TeletexString', 'VideotexString', 'IA5String', 'UTCTime', 'GeneralizedTime',
    'GraphicString', 'VisibleString', 'GeneralString', 'UniversalString', 'CharacterString',
    'BMPString',
]


def remove_signature(content, target=None):
    """ Takes a bytestring supposedly PKCS7 signed and returns its PKCS7-data only """
    if target:
        target.remove_signature_method = '_remove_signature'
    try:
        return _remove_signature(content)
    except Exception:
        return content


def _remove_signature(content):
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
    result, header_found, data_found = b'', False, False
    reader = Reader()
    for node in reader.build_from_stream(content):
        if node.kind == 'ObjectIdentifier' and node.content == PKCS7_DATA_OID:
            header_found = True
        if header_found and node.kind == 'OctetString':
            data_found = True
            result += node.content
        elif data_found:
            break
    if not header_found:
        raise Exception("ASN1 Header not found")
    if not data_found:
        raise Exception("ASN1 Content not found")
    return result


class Asn1Node:
    """ Base class for Asn1 nodes """
    _content = None
    is_primitive = False
    finalized = False

    def __init__(self, kind, start_offset, node_len):
        """ Initialization of the Asn1 node """
        self.kind = kind
        self.start_offset = start_offset
        self.length = node_len

    def total_length(self):
        """ Get the total length of the node if defined. The definition and length bytes must be considered. """
        return self.length + 2 if self.length != "?" else "?"

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, content):
        self._content = content


class PrimitiveNode(Asn1Node):
    """ Primitive Asn1 nodes contain pure data """
    is_primitive = True
    name = "Primitive"


class ObjectIdentifierNode(PrimitiveNode):
    """ Asn1 Object Identifier, i.e. 1.3.6.1.5.5.7.48.1 """
    @Asn1Node.content.setter
    def content(self, content):
        # Run through the content's bytes
        calc = 0
        result = f"{content[0] // 40}.{content[0] % 40}"
        for octet in content[1:]:
            # Other positions value the less significant 7 bits,
            # but the most significant bit is only negative when there's a break
            calc = (calc << 7) + (octet % (1 << 7))
            if not (octet & 0x80):
                result = f"{result}.{calc}"
                calc = 0
        self._content = result


class Reader:
    offset = 0
    root = None
    current_node = None
    last_open_node = None

    def __init__(self, *args, **kwargs):
        self.open_nodes_stack = []

    def finalize_last_open_node(self):
        """ Whenever a node is complete, it is finalized, and the references are updated """
        node = self.open_nodes_stack.pop()
        node.content = None
        self.current_node = None
        node.end_offset = self.offset
        node.finalized = True
        self.last_open_node = self.open_nodes_stack[-1] if self.open_nodes_stack else None
        return node

    def build_from_stream(self, stream):
        """ Build an Asn1 tree starting from a byte string from a p7m file """

        len_stream = len(stream)
        while self.offset < len_stream:

            start_offset = self.offset
            self.last_open_node = self.open_nodes_stack[-1] if self.open_nodes_stack else None

            # Read the definition and length bytes
            definition_byte = ord(stream[self.offset:self.offset + 1])
            self.offset += 1
            node_len, self.offset = self.read_length(stream, self.offset)

            if definition_byte == 0 and node_len == 0 and self.open_nodes_stack:
                yield self.finalize_last_open_node()
                continue

            # Create the current Node
            self.current_node = self.create_node(definition_byte, node_len, start_offset)
            if not self.root:
                self.root = self.current_node

            # If not primitive, add to the stack
            if not self.current_node.is_primitive:
                self.open_nodes_stack.append(self.current_node)
                self.last_open_node = self.current_node
            else:
                node = self.current_node
                new_offset = self.offset + node_len
                node.content = stream[self.offset:new_offset]
                self.offset = new_offset
                node.end_offset = new_offset
                node.finalized = True
                yield node

            # Clear the stack of all finished nodes
            while (
                self.last_open_node
                and not self.last_open_node.finalized
                and self.last_open_node.length != '?'
                and self.last_open_node.start_offset + self.last_open_node.total_length() <= self.offset
            ):
                yield self.finalize_last_open_node()

        return self.root

    def read_length(self, stream, offset):
        """ Returns: (length of the node, bytes read, updated offset) """

        # Read the first byte: if it is zero, it's a special entry.
        # Probably it's the second byte of a closing tag of a node (\x00 \x00 <--)

        first_byte = stream[offset:offset + 1]
        if first_byte == b'\x00':
            return 0, offset + 1
        elif first_byte == b'\x80':
            # If it's the only bit being set, the length is indefinite,
            # and the node will terminate with a double \x00
            return '?', offset + 1
        first_byte_val = ord(first_byte)
        if first_byte < b'\x80':
            # If the first bit of the first length byte is on
            return first_byte_val, offset + 1
        else:
            # Each byte we read is less significant, so we increase the significance of the
            # value we already read and increment by the current byte
            offset += 1
            node_len = 0
            length_bytes_no = first_byte_val % (1 << 7)
            for length_byte in stream[offset:offset + length_bytes_no]:
                node_len = (node_len << 8) + length_byte
            return node_len, offset + length_bytes_no

    def create_node(self, definition_byte, node_len, start_offset):
        """ Method to create new Asn1 nodes, given the definition bytes and the offset """
        target_class = Asn1Node
        kind = "Indefinite" if node_len == "?" else "Container"
        cls = {
            (0, 0): 'Universal',
            (0, 1): 'Application',
            (1, 0): 'Context-specific',
            (1, 1): 'Private'
        }[(
            definition_byte & (1 << 7) and 1,
            definition_byte & (1 << 6) and 1
        )]
        if cls == 'Universal' and not definition_byte & (1 << 5) and 1:
            tag = definition_byte % (1 << 5)
            kind = universal_tags[tag]
            if kind == 'ObjectIdentifier':
                target_class = ObjectIdentifierNode
            else:
                target_class = PrimitiveNode
        return target_class(kind, start_offset, node_len)


if __name__ == '__main__':
    """
        python remove_signature.py /path/to/einvoice.xml.p7m [times]
    """
    import sys
    from lxml import etree
    from cProfile import Profile
    from pstats import SortKey, Stats

    filename = sys.argv[1]
    times = len(sys.argv) > 2 and sys.argv[2]

    with open(filename, 'rb') as f:
        content = f.read().rstrip()

    if times:
        with Profile() as profile:
            for i in range(1, int(times) + 1):
                result = remove_signature(content)
            Stats(profile).strip_dirs().sort_stats(SortKey.CALLS).print_stats()
    else:
        result = remove_signature(content)
        parser = etree.XMLParser(recover=True, resolve_entities=False)
        print(etree.tostring(etree.fromstring(result, parser)).decode())
