from unittest.mock import MagicMock, patch
from zlib import crc32

from odoo.tests.common import BaseCase
from odoo.tools import file_open


class MockSocket:
    def __init__(self, f):
        self.f = f

    def recv(self, num_bytes):
        return self.f.read(num_bytes)


class TestIncomingTransactionResponse(BaseCase):
    @patch.dict(
        "sys.modules", {
            # Mock out all of hw_drivers to avoid side-effects from starting services,
            # additional dependencies and modifying global imports
            "odoo.addons.hw_drivers": MagicMock(),
            # Mock the modules IngenicoDriver imports so the imports don't fail
            "odoo.addons.hw_drivers.driver": MagicMock(),
            "odoo.addons.hw_drivers.event_manager": MagicMock(),
            "odoo.addons.hw_drivers.iot_handlers.interfaces.SocketInterface": MagicMock(),
        }
    )
    def setUp(self):
        # pylint: disable=import-outside-toplevel
        from odoo.addons.iot.iot_handlers.drivers.IngenicoDriver import IncomingIngenicoMessage
        self.IncomingIngenicoMessage = IncomingIngenicoMessage

    def test_parse_ticketdata(self):
        # The file contains the payload of a TLV message. To view or modify its
        # contents, use a hex editor and the TLV Cash Register Interface specification
        # to interpret it. Most of the data has been anonymized.
        with file_open('iot/tests/data/TransactionResponse', 'rb') as f:
            dev = MockSocket(f)
            msg = self.IncomingIngenicoMessage(dev)
            ticket_data = msg.getTransactionTicket()

            # First expected string in the ticket data
            assert b'KOPIE' in ticket_data
            # Last expected string in the ticket data
            assert b'Chip' in ticket_data


class TestOutgoingIngenicoMessage(BaseCase):
    @patch.dict(
        "sys.modules", {
            # Mock out all of hw_drivers to avoid side-effects from starting services,
            # additional dependencies and modifying global imports
            "odoo.addons.hw_drivers": MagicMock(),
            # Mock the modules IngenicoDriver imports so the imports don't fail
            "odoo.addons.hw_drivers.driver": MagicMock(),
            "odoo.addons.hw_drivers.event_manager": MagicMock(),
            "odoo.addons.hw_drivers.iot_handlers.interfaces.SocketInterface": MagicMock(),
        }
    )
    def setUp(self):
        # pylint: disable=import-outside-toplevel
        from odoo.addons.iot.iot_handlers.drivers.IngenicoDriver import OutgoingIngenicoMessage

        self.OutgoingIngenicoMessage = OutgoingIngenicoMessage
        self.dev = MagicMock()
        self.msg = self.OutgoingIngenicoMessage(
            dev=self.dev,
            terminalId=b"1",
            ecrId="1",
            protocolId=b"1",
            messageType="TransactionRequest",
            sequence=b"1",
            transactionId=1,
            amount=1,
        )

    def test_mdc_tag_length(self):
        # 1 byte for the tag + 1 byte for the length + 4 bytes for the CRC
        self.assertEqual(len(self.msg._generateMDC(b"dummy")), 6)

    def test_unpadded_crc(self):
        content = bytes(11)

        # An even length CRC (in nibbles), which doesn't require padding
        crc = format(crc32(content), 'x')
        self.assertEqual(crc, '6b87b1ec')
        self.assertEqual(len(crc), 8)

        # Verify the CRC has the expected length and no errors are thrown
        self.assertEqual(len(self.msg._getCRC32(content)), 4)

    def test_padded_crc(self):
        content = bytes(13)

        # An odd length CRC (in nibbles), which does require padding
        crc = format(crc32(content), 'x')
        self.assertEqual(crc, 'f744682')
        self.assertEqual(len(crc), 7)

        # Verify the CRC has the expected length and no errors are thrown
        self.assertEqual(len(self.msg._getCRC32(content)), 4)
