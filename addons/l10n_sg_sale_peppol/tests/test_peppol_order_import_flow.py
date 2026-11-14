import json
import logging
from base64 import b64decode, b64encode
from datetime import datetime
from lxml import etree

from requests import PreparedRequest, Response, Session

from odoo.tests import freeze_time
from odoo.tests.common import tagged
from odoo.tools.misc import file_open

from odoo.addons.account_peppol.tests.test_peppol_messages import TestPeppolMessage

_logger = logging.getLogger(__name__)

FILE_PATH = 'l10n_sg_sale_peppol/tests/assets'
FAKE_UUID = ['yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy',
             'zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz']


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPeppolOrderImportFlow(TestPeppolMessage):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_product_a = cls.env["product.product"].create(
            {
                "name": "Needle 4mm",
                "default_code": "121212",
                "type": "consu",
                "list_price": 50,
            },
        )
        cls.sent_documents = []

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        response = Response()
        response.status_code = 200
        url = r.path_url.lower()

        if url == '/api/peppol/1/get_document':
            body = json.loads(r.body)
            uuid = body['params']['message_uuids'][0]
            if uuid == FAKE_UUID[0]:
                response_content = {
                    'accounting_supplier_party': False,
                    'filename': 'test_outgoing.xml',
                    'enc_key': '',
                    'document': '',
                    'state': 'done' if not cls.env.context.get('error') else 'error',
                    'direction': 'outgoing',
                    'document_type': 'Invoice',
                }
            elif uuid == FAKE_UUID[1]:
                response_content = {
                    'accounting_supplier_party': '0198:dk16356706',
                    'filename': 'test_incoming',
                    'enc_key': file_open(f'{FILE_PATH}/enc_key', mode='rb').read(),
                    'document': b64encode(file_open(f'{FILE_PATH}/{cls.mocked_incoming_invoice_fname}', mode='rb').read()),
                    'state': 'done' if not cls.env.context.get('error') else 'error',
                    'direction': 'incoming',
                    'document_type': 'Invoice',
                    'origin_message_uuid': 'not_used_on_advanced_order',
                }
            response.json = lambda: {'result': {uuid: response_content}}
            return response

        if url == '/api/peppol/1/get_all_documents':
            response.json = lambda: {'result': {'messages': [{
                'uuid': FAKE_UUID[1],
                'state': 'done',
                'direction': 'incoming',
                'document_type': 'Invoice',
                'sender': '0198:dk16356706',
                'receiver': '0088:test',
                'timestamp': '2024-01-01',
                'error': False,
            }]}}
            return response

        if url == '/api/peppol/1/send_document':
            body = json.loads(r.body)
            cls.sent_documents.extend(body['params']['documents'])
            num_docs = len(body['params']['documents'])
            response.json = lambda: {'result': {'messages': [{'message_uuid': '11111111-1111-4111-8111-111111111111'}] * num_docs}}
            return response

        if url == '/api/peppol/1/ack':
            response.json = lambda: {'result': {}}
            return response

        return super()._request_handler(s, r, **kw)

    def _get_review_activities(self, order):
        return order.activity_ids.filtered(
            lambda a: a.activity_type_id == self.env.ref('l10n_sg_sale_peppol.mail_activity_type_peppol_order_review'),
        )

    def test_end_to_end_basic_order_processing(self):
        """Test complete workflow from XML document to sale order creation - basic order"""
        cls = self.__class__
        cls.mocked_incoming_invoice_fname = 'order_encrypted'

        def restore_mocked_incoming_invoice_fname():
            cls.mocked_incoming_invoice_fname = 'incoming_invoice'
        self.addCleanup(restore_mocked_incoming_invoice_fname)

        with freeze_time('2024-01-15 03:00:00'):
            self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()

        order = self.env['sale.order'].sudo().search([('l10n_sg_peppol_message_uuid', '=', FAKE_UUID[1])])
        # The quotation date is the import date, not a date from the document.
        self.assertEqual(order.date_order, datetime(2024, 1, 15, 3, 0, 0))
        self.assertEqual(order.l10n_sg_peppol_buyer_endpoint, '0088:7300010000001')
        self.assertRecordValues(order.partner_id, [{'name': 'Martin Foggerty', 'email': 'martin.foggerty@cityhospital.se'}])
        self.assertRecordValues(order.partner_id.parent_id, [{'name': 'City Hospital 345433', 'email': False, 'phone': False}])
        order_tx = order.l10n_sg_peppol_order_tx_ids[0]
        self.assertRecordValues(
            order_tx,
            [{
                'document_type': 'order',
                'state': 'to_reply',
            }],
        )
        self.assertEqual(self._get_review_activities(order), order_tx.activity_id)
        with freeze_time('2024-01-20 05:00:00'):
            order.action_confirm()
        # Once confirmed, the quotation date is the confirmation date.
        self.assertEqual(order.date_order, datetime(2024, 1, 20, 5, 0, 0))
        self.assertRecordValues(order_tx, [{
            'state': 'accepted',
        }])
        self.assertFalse(self._get_review_activities(order))

    def test_order_response_receiver(self):
        """ Order Responses go to the EndpointID the order was received from, even when the
        customer's own Peppol ID differs.
        """
        cls = self.__class__
        cls.mocked_incoming_invoice_fname = 'order_encrypted'
        self.addCleanup(setattr, cls, 'mocked_incoming_invoice_fname', 'incoming_invoice')
        self.sent_documents.clear()

        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()
        order = self.env['sale.order'].sudo().search([('l10n_sg_peppol_message_uuid', '=', FAKE_UUID[1])])
        order.partner_id.commercial_partner_id.write({'routing_scheme': '0208', 'routing_endpoint': '0477472701'})
        order.action_confirm()

        self.assertEqual([doc['receiver'] for doc in self.sent_documents], ['0088:7300010000001'] * 2)
        for doc in self.sent_documents:
            endpoint = etree.fromstring(b64decode(doc['ubl'])).find('./{*}BuyerCustomerParty/{*}Party/{*}EndpointID')
            self.assertEqual((endpoint.get('schemeID'), endpoint.text), ('0088', '7300010000001'))

    def test_order_change_processing(self):
        """ Test complete workflow from XML document to sale order creation and follow up receipt
            of order change request.
        """
        cls = self.__class__

        def restore_mocked_incoming_invoice_fname():
            cls.mocked_incoming_invoice_fname = 'incoming_invoice'
        self.addCleanup(restore_mocked_incoming_invoice_fname)

        cls.mocked_incoming_invoice_fname = 'order_encrypted'
        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()

        # Test order amount total
        order = self.env['sale.order'].sudo().search([('l10n_sg_peppol_message_uuid', '=', FAKE_UUID[1])])
        self.assertEqual(order.amount_total, 840.0)

        cls.mocked_incoming_invoice_fname = 'order_change_encrypted'
        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()

        # Test log notes
        messages = order.message_ids.filtered(lambda m: 'Line changed: Item 1' in m.body)
        self.assertTrue(messages)

        order_change_tx = order.l10n_sg_peppol_order_tx_ids.filtered_domain([
            ('document_type', '=', 'order_change'),
        ])
        self.assertTrue(order_change_tx.activity_id)
        customer, delivery_partner = order.partner_id, order.partner_shipping_id
        partner_count = self.env['res.partner'].search_count([])
        self.assertFalse(order.message_ids.filtered(lambda m: "differs from the order's customer" in m.body))
        order.action_apply_peppol_order_change()
        self.assertEqual(order.amount_total, 600.0)
        self.assertEqual(order.partner_id, customer)
        self.assertEqual(order.partner_shipping_id, delivery_partner)
        self.assertEqual(self.env['res.partner'].search_count([]), partner_count)
        self.assertEqual(order_change_tx.state, 'accepted')
        self.assertTrue(order_change_tx.activity_id.date_done)

    def test_order_cancel_processing(self):
        """ Test complete workflow from XML document to sale order creation and follow up receipt
            of order cancellation request.
        """
        cls = self.__class__

        def restore_mocked_incoming_invoice_fname():
            cls.mocked_incoming_invoice_fname = 'incoming_invoice'
        self.addCleanup(restore_mocked_incoming_invoice_fname)

        cls.mocked_incoming_invoice_fname = 'order_encrypted'
        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()

        cls.mocked_incoming_invoice_fname = 'order_cancel_encrypted'
        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()

        order = self.env['sale.order'].sudo().search([('l10n_sg_peppol_message_uuid', '=', FAKE_UUID[1])])
        customer = order.partner_id
        import_activities = order.activity_ids - self._get_review_activities(order)
        self.assertFalse(order.message_ids.filtered(lambda m: "differs from the order's customer" in m.body))
        order_tx = order.l10n_sg_peppol_order_tx_ids.filtered_domain([('document_type', '=', 'order')])
        order.action_apply_peppol_order_cancel()
        self.assertEqual(order.state, 'cancel')
        self.assertEqual(order.partner_id, customer)
        # The pending order itself is not rejected: the cancellation reply answers the buyer.
        self.assertEqual(order_tx.state, 'to_reply')
        self.assertEqual(order.activity_ids, import_activities)

    def test_order_rejection_processing(self):
        """Test complete workflow from XML document to sale order creation - order rejection"""
        cls = self.__class__
        cls.mocked_incoming_invoice_fname = 'order_encrypted'

        def restore_mocked_incoming_invoice_fname():
            cls.mocked_incoming_invoice_fname = 'incoming_invoice'
        self.addCleanup(restore_mocked_incoming_invoice_fname)

        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()

        order = self.env['sale.order'].sudo().search([('l10n_sg_peppol_message_uuid', '=', FAKE_UUID[1])])
        order_tx = order.l10n_sg_peppol_order_tx_ids[0]
        self.assertRecordValues(
            order_tx,
            [{
                'document_type': 'order',
                'state': 'to_reply',
            }],
        )
        self.assertEqual(self._get_review_activities(order), order_tx.activity_id)
        order.action_cancel()
        self.assertRecordValues(order_tx, [{
            'state': 'rejected',
        }])
        self.assertFalse(self._get_review_activities(order))

    def test_order_change_rejection_processing(self):
        """ Test complete workflow from XML document to sale order creation and follow up receipt
            of order change request rejection.
        """
        cls = self.__class__

        def restore_mocked_incoming_invoice_fname():
            cls.mocked_incoming_invoice_fname = 'incoming_invoice'
        self.addCleanup(restore_mocked_incoming_invoice_fname)

        cls.mocked_incoming_invoice_fname = 'order_encrypted'
        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()

        # Test order amount total
        order = self.env['sale.order'].sudo().search([('l10n_sg_peppol_message_uuid', '=', FAKE_UUID[1])])
        original_amount = order.amount_total
        self.assertEqual(original_amount, 840.0)

        cls.mocked_incoming_invoice_fname = 'order_change_encrypted'
        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()

        # Test log notes
        messages = order.message_ids.filtered(lambda m: 'Line changed: Item 1' in m.body)
        self.assertTrue(messages)

        order_change_tx = order.l10n_sg_peppol_order_tx_ids.filtered_domain([
            ('document_type', '=', 'order_change'),
        ])[0]
        order.action_reject_peppol_order_change()
        self.assertRecordValues(order_change_tx, [{
            'state': 'rejected',
        }])
        # Verify order amount remains unchanged after rejection
        self.assertEqual(order.amount_total, original_amount)

    def test_line_delivery_period_import(self):
        """Test that RequestedDeliveryPeriod is parsed from a LineItem node into the requested
        delivery datetimes of the order line, stored in UTC."""
        parser = self.env['sale.edi.xml.ubl_bis3_advanced_order']
        order = self.env['sale.order'].new({'company_id': self.env.company.id})
        self.env.company.partner_id.tz = 'Asia/Singapore'

        def get_delivery_vals(line_tree):
            line_vals = parser._retrieve_line_vals(order, line_tree)
            return {key: line_vals[key] for key in ('l10n_sg_delivery_start', 'l10n_sg_delivery_end') if key in line_vals}

        def make_period_xml(start_date='', start_time='', end_date='', end_time=''):
            children = ''
            if start_date:
                children += f'<cbc:StartDate>{start_date}</cbc:StartDate>'
            if start_time:
                children += f'<cbc:StartTime>{start_time}</cbc:StartTime>'
            if end_date:
                children += f'<cbc:EndDate>{end_date}</cbc:EndDate>'
            if end_time:
                children += f'<cbc:EndTime>{end_time}</cbc:EndTime>'
            return etree.fromstring(
                f'<LineItem'
                f' xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"'
                f' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
                f'<cbc:ID>1</cbc:ID><cbc:Quantity>1</cbc:Quantity><cac:Item><cbc:Name>Item</cbc:Name></cac:Item>'
                f'<cac:Delivery><cac:RequestedDeliveryPeriod>{children}</cac:RequestedDeliveryPeriod></cac:Delivery>'
                f'</LineItem>'
            )

        # Times without offset are in the company timezone (UTC+8).
        vals = get_delivery_vals(make_period_xml('2024-01-01', '09:00:00', '2024-01-31', '17:00:00'))
        self.assertEqual(vals, {
            'l10n_sg_delivery_start': datetime(2024, 1, 1, 1, 0, 0),
            'l10n_sg_delivery_end': datetime(2024, 1, 31, 9, 0, 0),
        })

        # Times with an offset are converted from it.
        vals = get_delivery_vals(make_period_xml(start_date='2024-01-01', start_time='09:00:00Z'))
        self.assertEqual(vals, {'l10n_sg_delivery_start': datetime(2024, 1, 1, 9, 0, 0), 'l10n_sg_delivery_end': False})

        # Dates without time cover the whole day.
        vals = get_delivery_vals(make_period_xml(start_date='2024-01-01', end_date='2024-01-31'))
        self.assertEqual(vals, {
            'l10n_sg_delivery_start': datetime(2023, 12, 31, 16, 0, 0),
            'l10n_sg_delivery_end': datetime(2024, 1, 31, 15, 59, 59),
        })

        # No delivery element at all
        self.assertEqual(get_delivery_vals(etree.fromstring(
            '<LineItem xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
            '<cbc:ID>1</cbc:ID><cbc:Quantity>1</cbc:Quantity></LineItem>'
        )), {})

    @freeze_time('2024-01-05 03:00:00')
    def test_order_validity_period_import(self):
        """Test the buyer's deadline (ValidityPeriod) becomes the due date of the review activity,
        and that neither it nor a line delivery date is used as a quotation date or expiration."""
        env = self.env(su=True)
        order = env['sale.order'].create({'partner_id': env['res.partner'].create({'name': 'Buyer'}).id})
        default_validity_date = order.validity_date

        def make_order_xml(validity_end_date=None):
            validity_xml = (
                f'<cac:ValidityPeriod><cbc:EndDate>{validity_end_date}</cbc:EndDate></cac:ValidityPeriod>'
                if validity_end_date else ''
            )
            return (
                f'<Order xmlns="urn:oasis:names:specification:ubl:schema:xsd:Order-2"'
                f' xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"'
                f' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
                f'<cbc:ID>ORDER-1</cbc:ID><cbc:IssueDate>2024-01-05</cbc:IssueDate>{validity_xml}'
                f'<cac:OrderLine><cac:LineItem><cac:Delivery><cac:RequestedDeliveryPeriod>'
                f'<cbc:EndDate>2024-02-01</cbc:EndDate>'
                f'</cac:RequestedDeliveryPeriod></cac:Delivery>'
                f'<cac:Item><cbc:Name>Item</cbc:Name></cac:Item></cac:LineItem></cac:OrderLine>'
                f'</Order>'
            )

        order_vals, _logs = env['sale.edi.xml.ubl_bis3_advanced_order']._retrieve_order_vals(
            order, etree.fromstring(make_order_xml('2024-01-11')),
        )
        self.assertNotIn('date_order', order_vals)
        self.assertNotIn('validity_date', order_vals)

        def schedule_review(validity_end_date=None):
            order_tx = env['sale.peppol.advanced.order.transaction'].create({
                'order_id': order.id,
                'attachment_id': env['ir.attachment'].create({
                    'name': 'order.xml',
                    'raw': make_order_xml(validity_end_date).encode(),
                    'mimetype': 'application/xml',
                }).id,
                'state': 'to_reply',
                'document_type': 'order',
            })
            order._l10n_sg_peppol_schedule_review(order_tx, "Review the order.")
            return order_tx.activity_id

        activity = schedule_review('2024-01-11')
        self.assertEqual(str(activity.date_deadline), '2024-01-11')
        self.assertIn('The buyer expects a response by', str(activity.note))
        self.assertEqual(order.validity_date, default_validity_date)

        # Without a deadline from the buyer, the activity type's default due date applies.
        activity = schedule_review()
        self.assertEqual(str(activity.date_deadline), '2024-01-05')
        self.assertNotIn('The buyer expects a response by', str(activity.note))

    def test_order_cancel_rejection_processing(self):
        """ Test complete workflow from XML document to sale order creation and follow up receipt
            of order cancellation request rejection.
        """
        cls = self.__class__

        def restore_mocked_incoming_invoice_fname():
            cls.mocked_incoming_invoice_fname = 'incoming_invoice'
        self.addCleanup(restore_mocked_incoming_invoice_fname)

        cls.mocked_incoming_invoice_fname = 'order_encrypted'
        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()

        cls.mocked_incoming_invoice_fname = 'order_cancel_encrypted'
        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()

        order = self.env['sale.order'].sudo().search([('l10n_sg_peppol_message_uuid', '=', FAKE_UUID[1])])
        order_cancel_tx = order.l10n_sg_peppol_order_tx_ids.filtered_domain([
            ('document_type', '=', 'order_cancel'),
        ])[0]
        # Verify order is not cancelled before rejection
        self.assertNotEqual(order.state, 'cancel')
        order.action_reject_peppol_order_cancel()
        self.assertRecordValues(order_cancel_tx, [{
            'state': 'rejected',
        }])
        # Verify order remains active (not cancelled) after rejecting the cancellation
        self.assertNotEqual(order.state, 'cancel')

    def test_order_delivery_partner_import(self):
        """Test the delivery information of an order is resolved to the buyer, one of its contacts
        or a known GLN partner, and becomes a new delivery address of the buyer otherwise."""
        env = self.env(su=True)
        parser = env['sale.edi.xml.ubl_bis3_advanced_order']
        singapore = env.ref('base.sg')
        buyer = env['res.partner'].create({
            'name': 'Buyer',
            'is_company': True,
            'street': '1 Buyer Road',
            'zip': '111111',
            'country_id': singapore.id,
        })
        warehouse = env['res.partner'].create({
            'name': 'Buyer Warehouse',
            'type': 'delivery',
            'parent_id': buyer.id,
            'street': '2 Warehouse Road',
            'zip': '222222',
            'country_id': singapore.id,
        })
        end_customer = env['res.partner'].create({'name': 'End Customer', 'global_location_number': '5880000000010'})
        order = env['sale.order'].create({'partner_id': buyer.id})

        def import_delivery_partner(delivery_xml):
            return parser._import_order_delivery_partner(order, etree.fromstring(
                f'<Order xmlns="urn:oasis:names:specification:ubl:schema:xsd:Order-2"'
                f' xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"'
                f' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
                f'<cbc:ID>ORDER-1</cbc:ID>{delivery_xml}</Order>'
            ))[0]

        def make_address_xml(street, zip_code, tag='Address'):
            return (
                f'<cac:{tag}><cbc:StreetName>{street}</cbc:StreetName><cbc:PostalZone>{zip_code}</cbc:PostalZone>'
                f'<cac:Country><cbc:IdentificationCode>SG</cbc:IdentificationCode></cac:Country></cac:{tag}>'
            )

        def make_party_xml(name, inner=''):
            return f'<cac:DeliveryParty>{inner}<cac:PartyName><cbc:Name>{name}</cbc:Name></cac:PartyName></cac:DeliveryParty>'

        # Without delivery information, the order is delivered to the buyer.
        self.assertEqual(import_delivery_partner(''), buyer)
        self.assertEqual(import_delivery_partner(
            '<cac:Delivery><cac:RequestedDeliveryPeriod><cbc:EndDate>2024-02-01</cbc:EndDate>'
            '</cac:RequestedDeliveryPeriod></cac:Delivery>'
        ), buyer)

        # Delivery information repeating the buyer's address resolves to the buyer.
        self.assertEqual(import_delivery_partner(
            f'<cac:Delivery><cac:DeliveryLocation>{make_address_xml(" 1  buyer road", "111111")}</cac:DeliveryLocation>'
            f'{make_party_xml("Buyer")}</cac:Delivery>'
        ), buyer)

        # An address of a known contact resolves to it, from the location or the party address.
        self.assertEqual(import_delivery_partner(
            f'<cac:Delivery><cac:DeliveryLocation>{make_address_xml("2 Warehouse Road", "222222")}</cac:DeliveryLocation></cac:Delivery>'
        ), warehouse)
        self.assertEqual(import_delivery_partner(
            f'<cac:Delivery>{make_party_xml("Buyer Warehouse", make_address_xml("2 Warehouse Road", "222222", "PostalAddress"))}</cac:Delivery>'
        ), warehouse)

        # A contact name alone resolves to that contact.
        self.assertEqual(import_delivery_partner(f'<cac:Delivery>{make_party_xml("Buyer Warehouse")}</cac:Delivery>'), warehouse)

        # A known GLN resolves to its partner, even outside the buyer's contacts.
        self.assertEqual(import_delivery_partner(
            '<cac:Delivery><cac:DeliveryLocation><cbc:ID schemeID="0088">5880000000010</cbc:ID>'
            f'{make_address_xml("3 Elsewhere Road", "333333")}</cac:DeliveryLocation></cac:Delivery>'
        ), end_customer)

        # An unknown delivery location becomes a new delivery address of the buyer.
        new_address = import_delivery_partner(
            '<cac:Delivery><cac:DeliveryLocation><cbc:ID schemeID="0088">5880000000027</cbc:ID>'
            f'{make_address_xml("4 New Road", "444444")}</cac:DeliveryLocation>'
            f'{make_party_xml("Site Office", "")}</cac:Delivery>'
        )
        self.assertRecordValues(new_address, [{
            'name': 'Site Office',
            'type': 'delivery',
            'parent_id': buyer.id,
            'street': '4 New Road',
            'zip': '444444',
            'country_id': singapore.id,
            'global_location_number': '5880000000027',
        }])

        # An invalid GLN is ignored.
        new_address = import_delivery_partner(
            '<cac:Delivery><cac:DeliveryLocation><cbc:ID schemeID="0088">1234</cbc:ID>'
            f'{make_address_xml("5 New Road", "555555")}</cac:DeliveryLocation></cac:Delivery>'
        )
        self.assertRecordValues(new_address, [{
            'type': 'delivery',
            'parent_id': buyer.id,
            'street': '5 New Road',
            'global_location_number': False,
        }])

    def test_buyer_mismatch_log(self):
        """Test a document received for an existing order logs where its buyer differs from the
        order's customer, without changing the customer."""
        env = self.env(su=True)
        parser = env['sale.edi.xml.ubl_bis3_advanced_order']
        buyer = env['res.partner'].create({'name': 'Buyer', 'is_company': True, 'vat': '201912345K'})
        contact = env['res.partner'].create({'name': 'Jane Buyer', 'email': 'jane@buyer.test', 'parent_id': buyer.id})
        env['res.partner'].create({'name': 'Other Company', 'is_company': True, 'vat': '201954321K'})
        order = env['sale.order'].create({'partner_id': contact.id})

        def log_buyer_mismatch(vat, contact_name, contact_email):
            messages = order.message_ids
            parser.log_buyer_mismatch(order, etree.fromstring(
                '<Order xmlns="urn:oasis:names:specification:ubl:schema:xsd:Order-2"'
                ' xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"'
                ' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
                '<cac:BuyerCustomerParty><cac:Party>'
                f'<cac:PartyLegalEntity><cbc:RegistrationName>Buyer</cbc:RegistrationName><cbc:CompanyID>{vat}</cbc:CompanyID></cac:PartyLegalEntity>'
                f'<cac:Contact><cbc:Name>{contact_name}</cbc:Name><cbc:ElectronicMail>{contact_email}</cbc:ElectronicMail></cac:Contact>'
                '</cac:Party></cac:BuyerCustomerParty></Order>'
            ))
            self.assertEqual(order.partner_id, contact)
            new_messages = order.message_ids - messages
            return str(new_messages.body) if new_messages else ''

        self.assertFalse(log_buyer_mismatch('201912345K', 'Jane Buyer', 'jane@buyer.test'))
        self.assertFalse(log_buyer_mismatch('201912345K', 'J. Buyer', 'JANE@buyer.test'))

        log = log_buyer_mismatch('201954321K', 'Jane Buyer', 'jane@buyer.test')
        self.assertIn('Buyer: Other Company (order: Buyer)', log)
        self.assertNotIn('Contact', log)

        log = log_buyer_mismatch('201912345K', 'John Buyer', 'john@buyer.test')
        self.assertNotIn('Buyer: ', log)
        self.assertIn('Contact name: John Buyer (order: Jane Buyer)', log)
        self.assertIn('Contact email: john@buyer.test (order: jane@buyer.test)', log)

    def test_new_buyer_peppol_id(self):
        """Test a buyer partner created from the document gets the document's EndpointID as its
        Peppol ID, while an existing one keeps its own."""
        env = self.env(su=True)
        parser = env['sale.edi.xml.ubl_bis3_advanced_order']

        def import_buyer(name):
            tree = etree.fromstring(
                '<Order xmlns="urn:oasis:names:specification:ubl:schema:xsd:Order-2"'
                ' xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"'
                ' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
                '<cac:BuyerCustomerParty><cac:Party>'
                '<cbc:EndpointID schemeID="0088">7300010000001</cbc:EndpointID>'
                '<cac:PostalAddress><cac:Country><cbc:IdentificationCode>BE</cbc:IdentificationCode></cac:Country></cac:PostalAddress>'
                '<cac:PartyTaxScheme><cbc:CompanyID>BE0477472701</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>'
                f'<cac:PartyLegalEntity><cbc:RegistrationName>{name}</cbc:RegistrationName></cac:PartyLegalEntity>'
                '</cac:Party></cac:BuyerCustomerParty></Order>'
            )
            partner, _logs = parser._import_partner(self.env.company, **parser._import_retrieve_partner_vals(tree, 'BuyerCustomer'))
            return partner

        new_buyer = import_buyer('New Buyer')
        self.assertEqual(new_buyer.name, 'New Buyer')
        self.assertEqual(new_buyer.routing_identifier, '0088:7300010000001')
        self.assertEqual(new_buyer.country_id.code, 'BE')

        new_buyer.write({'routing_scheme': '0208', 'routing_endpoint': '0477472701', 'country_id': False})
        self.assertEqual(import_buyer('Existing Buyer'), new_buyer)
        self.assertEqual(new_buyer.routing_identifier, '0208:0477472701')
        self.assertFalse(new_buyer.country_id)

    def test_buyer_endpoint_matching(self):
        """Test the buyer is matched on the document's EndpointID before its VAT, only when a single
        company partner has that EndpointID."""
        env = self.env(su=True)
        parser = env['sale.edi.xml.ubl_bis3_advanced_order']
        tree = etree.fromstring(
            '<Order xmlns="urn:oasis:names:specification:ubl:schema:xsd:Order-2"'
            ' xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"'
            ' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
            '<cac:BuyerCustomerParty><cac:Party>'
            '<cbc:EndpointID schemeID="0088">7300010000001</cbc:EndpointID>'
            '<cac:PostalAddress><cac:Country><cbc:IdentificationCode>BE</cbc:IdentificationCode></cac:Country></cac:PostalAddress>'
            '<cac:PartyTaxScheme><cbc:CompanyID>BE0477472701</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>'
            '<cac:PartyLegalEntity><cbc:RegistrationName>Buyer</cbc:RegistrationName></cac:PartyLegalEntity>'
            '</cac:Party></cac:BuyerCustomerParty></Order>'
        )
        endpoint = {'routing_scheme': '0088', 'routing_endpoint': '7300010000001'}
        vat_partner = env['res.partner'].create({'name': 'VAT Buyer', 'is_company': True, 'vat': 'BE0477472701'})
        endpoint_partner = env['res.partner'].create({'name': 'Endpoint Buyer', 'is_company': True, **endpoint})
        env['res.partner'].create({'name': 'Endpoint Contact', 'parent_id': vat_partner.id}).write(endpoint)

        def import_buyer():
            partner, _logs = parser._import_partner(self.env.company, **parser._import_retrieve_partner_vals(tree, 'BuyerCustomer'))
            return partner

        self.assertEqual(import_buyer(), endpoint_partner)
        self.assertFalse(endpoint_partner.country_id)

        order = env['sale.order'].create({'partner_id': endpoint_partner.id})
        messages = order.message_ids
        parser.log_buyer_mismatch(order, tree)
        self.assertFalse(order.message_ids - messages)

        env['res.partner'].create({'name': 'Other Endpoint Buyer', 'is_company': True, **endpoint})
        self.assertEqual(import_buyer(), vat_partner)

    def test_buyer_contact_import(self):
        """Test the buyer contact of the document becomes the customer only when its email matches a
        single contact of the buyer, or creates one when none matches, and is logged otherwise."""
        env = self.env(su=True)
        parser = env['sale.edi.xml.ubl_bis3_advanced_order']
        buyer = env['res.partner'].create({'name': 'Buyer', 'is_company': True, 'vat': '201912345K'})
        jane = env['res.partner'].create({'name': 'Jane Buyer', 'email': 'jane@buyer.test', 'parent_id': buyer.id})
        for name in ('John Buyer', 'Johnny Buyer'):
            env['res.partner'].create({'name': name, 'email': 'john@buyer.test', 'parent_id': buyer.id})
        individual = env['res.partner'].create({'name': 'Indie', 'email': 'indie@buyer.test'})
        order = env['sale.order'].create({'partner_id': buyer.id})

        def make_order_xml(contact_xml):
            return etree.fromstring(
                '<Order xmlns="urn:oasis:names:specification:ubl:schema:xsd:Order-2"'
                ' xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"'
                ' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
                '<cbc:ID>ORDER-1</cbc:ID><cac:BuyerCustomerParty><cac:Party>'
                '<cac:PartyLegalEntity><cbc:RegistrationName>Buyer</cbc:RegistrationName><cbc:CompanyID>201912345K</cbc:CompanyID></cac:PartyLegalEntity>'
                f'{contact_xml}</cac:Party></cac:BuyerCustomerParty></Order>'
            )

        def import_contact(partner, name=None, phone=None, email=None):
            contact_xml = ''.join(
                f'<cbc:{tag}>{value}</cbc:{tag}>'
                for tag, value in (('Name', name), ('Telephone', phone), ('ElectronicMail', email)) if value
            )
            messages = order.message_ids
            contact = parser._import_buyer_contact(order, partner, make_order_xml(f'<cac:Contact>{contact_xml}</cac:Contact>'))
            new_messages = order.message_ids - messages
            return contact, str(new_messages.body) if new_messages else ''

        self.assertEqual(parser._import_buyer_contact(order, buyer, make_order_xml('')), buyer)

        contact, log = import_contact(buyer, 'J. Buyer', '+65 6000 0000', 'JANE@buyer.test')
        self.assertEqual(contact, jane)
        self.assertFalse(log)
        self.assertRecordValues(jane, [{'name': 'Jane Buyer', 'phone': False}])

        contact, log = import_contact(jane, 'John Buyer', email='john@buyer.test')
        self.assertEqual(contact, buyer)
        self.assertIn('Several contacts of Buyer', log)

        contact, log = import_contact(buyer, 'Jane Buyer')
        self.assertEqual(contact, buyer)
        self.assertIn('no email', log)
        self.assertIn('Name: Jane Buyer', log)

        contact, log = import_contact(buyer, 'Jan Buyer', '+65 6000 0001', 'jan_@buyer.test')
        self.assertRecordValues(contact, [{
            'name': 'Jan Buyer',
            'phone': '+65 6000 0001',
            'email': 'jan_@buyer.test',
            'parent_id': buyer.id,
            'type': 'contact',
        }])
        self.assertIn('Created the contact Jan Buyer under Buyer', log)

        self.assertEqual(import_contact(individual, 'Indie', email='indie@buyer.test'), (individual, ''))
        contact, log = import_contact(individual, 'Someone Else', email='indie@buyer.test')
        self.assertEqual(contact, individual)
        self.assertIn('differs from the customer', log)

        order_vals, _logs = parser._retrieve_order_vals(
            order, make_order_xml('<cac:Contact><cbc:ElectronicMail>jane@buyer.test</cbc:ElectronicMail></cac:Contact>'),
        )
        self.assertEqual(order_vals['partner_id'], jane.id)
        self.assertEqual(order_vals['partner_shipping_id'], buyer.id)

    def test_buyer_address_mismatch_log(self):
        """Test the order import logs where the buyer address of the document differs from the
        customer's, without changing the customer."""
        env = self.env(su=True)
        parser = env['sale.edi.xml.ubl_bis3_advanced_order']
        buyer = env['res.partner'].create({
            'name': 'Address Buyer',
            'is_company': True,
            'street': '1 Buyer Road',
            'zip': '111111',
            'country_id': env.ref('base.sg').id,
        })
        order = env['sale.order'].create({'partner_id': buyer.id})

        def import_address(street, zip_code):
            messages = order.message_ids
            parser._retrieve_order_vals(order, etree.fromstring(
                '<Order xmlns="urn:oasis:names:specification:ubl:schema:xsd:Order-2"'
                ' xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"'
                ' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
                '<cbc:ID>ORDER-1</cbc:ID><cac:BuyerCustomerParty><cac:Party>'
                f'<cac:PostalAddress><cbc:StreetName>{street}</cbc:StreetName><cbc:PostalZone>{zip_code}</cbc:PostalZone>'
                '<cac:Country><cbc:IdentificationCode>SG</cbc:IdentificationCode></cac:Country></cac:PostalAddress>'
                '<cac:PartyLegalEntity><cbc:RegistrationName>Address Buyer</cbc:RegistrationName></cac:PartyLegalEntity>'
                '</cac:Party></cac:BuyerCustomerParty></Order>'
            ))
            new_messages = order.message_ids - messages
            return str(new_messages.body) if new_messages else ''

        self.assertFalse(import_address(' 1  buyer road', '111111'))

        log = import_address('9 Other Road', '111111')
        self.assertIn('Street: 9 Other Road (customer: 1 Buyer Road)', log)
        self.assertNotIn('ZIP', log)
        self.assertNotIn('Country', log)
        self.assertEqual(buyer.street, '1 Buyer Road')

    def test_order_change_delivery_address(self):
        """Test the delivery information of an order change is logged against the delivery address
        of the order, and becomes its delivery address once the change is applied."""
        env = self.env(su=True)
        parser = env['sale.edi.xml.ubl_bis3_order_change']
        singapore = env.ref('base.sg')
        buyer = env['res.partner'].create({
            'name': 'Buyer',
            'is_company': True,
            'street': '1 Buyer Road',
            'zip': '111111',
            'country_id': singapore.id,
        })
        order = env['sale.order'].create({'partner_id': buyer.id})

        def make_order_change_xml(delivery_xml):
            return etree.fromstring(
                '<OrderChange xmlns="urn:oasis:names:specification:ubl:schema:xsd:OrderChange-2"'
                ' xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"'
                ' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
                f'<cbc:ID>CHANGE-1</cbc:ID>{delivery_xml}</OrderChange>'
            )

        def make_delivery_xml(street, zip_code):
            return (
                '<cac:Delivery><cac:DeliveryLocation><cac:Address>'
                f'<cbc:StreetName>{street}</cbc:StreetName><cbc:PostalZone>{zip_code}</cbc:PostalZone>'
                '<cac:Country><cbc:IdentificationCode>SG</cbc:IdentificationCode></cac:Country>'
                '</cac:Address></cac:DeliveryLocation></cac:Delivery>'
            )

        def log_order_change_diff(tree):
            messages = order.message_ids
            parser.log_order_change_diff(order, tree)
            return str((order.message_ids - messages).body)

        self.assertNotIn('Delivery address', log_order_change_diff(make_order_change_xml('')))
        self.assertNotIn('Delivery address', log_order_change_diff(make_order_change_xml(make_delivery_xml(' 1  buyer road', '111111'))))

        log = log_order_change_diff(make_order_change_xml(make_delivery_xml('4 New Road', '444444')))
        self.assertIn('Delivery address changed: Buyer', log)
        self.assertIn('Street: 1 Buyer Road -&gt; 4 New Road', log)
        self.assertIn('Zip: 111111 -&gt; 444444', log)
        self.assertNotIn('Country', log)

        def apply_order_change(tree):
            parser.process_peppol_order_change(order, env['ir.attachment'].create({
                'name': 'order_change.xml',
                'raw': etree.tostring(tree),
                'mimetype': 'application/xml',
            }))

        apply_order_change(make_order_change_xml(''))
        self.assertEqual(order.partner_shipping_id, buyer)

        apply_order_change(make_order_change_xml(make_delivery_xml('4 New Road', '444444')))
        self.assertRecordValues(order.partner_shipping_id, [{
            'type': 'delivery',
            'parent_id': buyer.id,
            'street': '4 New Road',
            'zip': '444444',
        }])
        self.assertEqual(buyer.street, '1 Buyer Road')

    def test_order_change_currency_warning(self):
        """Test an order change in another currency than the order's is flagged in the change log."""
        env = self.env(su=True)
        parser = env['sale.edi.xml.ubl_bis3_order_change']
        order = env['sale.order'].create({'partner_id': env['res.partner'].create({'name': 'Buyer'}).id})
        other_currency = 'EUR' if order.currency_id.name == 'USD' else 'USD'

        def log_order_change_diff(currency_code):
            messages = order.message_ids
            parser.log_order_change_diff(order, etree.fromstring(
                '<OrderChange xmlns="urn:oasis:names:specification:ubl:schema:xsd:OrderChange-2"'
                ' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
                f'<cbc:ID>CHANGE-1</cbc:ID><cbc:DocumentCurrencyCode>{currency_code}</cbc:DocumentCurrencyCode></OrderChange>'
            ))
            return str((order.message_ids - messages).body)

        self.assertNotIn('currency', log_order_change_diff(order.currency_id.name))
        self.assertIn(
            f"The currency of the order change, {other_currency}, differs from the order's, {order.currency_id.name}",
            log_order_change_diff(other_currency).replace('&#39;', "'"),
        )

    def test_order_response_promised_delivery(self):
        """Test the commitment date is sent as the promised delivery time in the company timezone."""
        env = self.env(su=True)
        env.company.partner_id.tz = 'Asia/Singapore'
        order = env['sale.order'].create({
            'partner_id': env['res.partner'].create({'name': 'Buyer'}).id,
            'commitment_date': datetime(2024, 1, 15, 2, 0, 0),
        })
        order_tx = env['sale.peppol.advanced.order.transaction'].create({
            'order_id': order.id,
            'attachment_id': env['ir.attachment'].create({'name': 'order.xml', 'raw': b'<Order/>'}).id,
            'state': 'to_reply',
            'document_type': 'order',
        })
        root = etree.fromstring(env['sale.edi.xml.ubl_bis3_order_response_advanced'].build_order_response_xml(order, order_tx, 'AP'))
        period = root.find('./{*}Delivery/{*}PromisedDeliveryPeriod')
        self.assertEqual((period.findtext('./{*}EndDate'), period.findtext('./{*}EndTime')), ('2024-01-15', '10:00:00'))
