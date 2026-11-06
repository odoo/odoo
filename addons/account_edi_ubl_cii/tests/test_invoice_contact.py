from lxml import etree

from odoo.tests import Form, tagged

from .common import TestUblBis3Common, TestUblCiiBECommon


@tagged('post_install', '-at_install')
class TestInvoiceContactEndpoint(TestUblBis3Common, TestUblCiiBECommon):

    def _create_invoice_contact(self, parent=None, **values):
        parent = parent or self.partner_fr
        return self.env['res.partner'].create({
            'name': 'Billing service',
            'parent_id': parent.id,
            'type': 'invoice',
            'country_id': parent.country_id.id,
            **values,
        })

    def test_invoice_contact_defaults_and_override(self):
        contact = self._create_invoice_contact()
        self.assertEqual(contact.peppol_eas, self.partner_fr.peppol_eas)
        self.assertEqual(contact.peppol_endpoint, self.partner_fr.peppol_endpoint)
        contact.write({'peppol_eas': '0088', 'peppol_endpoint': '1234567890128'})

        # A later parent edit or a recomputation must not erase the address
        # entered for a particular billing service.
        self.partner_fr.peppol_endpoint = 'FR23334175221'
        contact._compute_peppol_eas()
        contact._compute_peppol_endpoint()
        self.assertEqual(contact.peppol_eas, '0088')
        self.assertEqual(contact.peppol_endpoint, '1234567890128')

    def test_invoice_contact_country_and_type(self):
        for parent_country, contact_country, contact_type, allowed in (
            ('fr', 'fr', 'invoice', True),
            ('fr', False, 'invoice', True),
            ('be', 'be', 'invoice', False),
            ('be', False, 'invoice', False),
            ('be', 'fr', 'invoice', True),
            ('fr', 'be', 'invoice', True),
            ('be', 'nl', 'invoice', True),
            ('fr', 'fr', 'delivery', False),
            ('fr', 'fr', 'contact', False),
        ):
            with self.subTest(parent_country=parent_country, contact_country=contact_country, contact_type=contact_type):
                parent = self.partner_fr if parent_country == 'fr' else self.partner_be
                contact = self._create_invoice_contact(
                    parent=parent,
                    country_id=self.env.ref(f'base.{contact_country}').id if contact_country else False,
                    type=contact_type,
                )
                self.assertEqual(contact._is_peppol_invoice_contact(), allowed)
                self.assertEqual(contact._get_peppol_invoice_partner(), contact if allowed else parent)
                if contact_type == 'invoice':
                    self.assertEqual(bool(contact.available_peppol_eas), allowed)
                else:
                    # Keep the existing choices for ordinary contacts, including
                    # portal users configuring their own electronic address.
                    self.assertTrue(contact.available_peppol_eas)

    def test_invoice_contact_form(self):
        # Exercise both entry points: the embedded address form and a contact
        # opened on its own, whose ordinary accounting settings are hidden.
        with Form(self.partner_fr, view='base.view_partner_form') as partner_form:
            with partner_form.child_ids.new() as contact_form:
                contact_form.type = 'invoice'
                contact_form.name = 'Billing service'
                self.assertEqual(contact_form.peppol_eas, self.partner_fr.peppol_eas)
                self.assertEqual(contact_form.peppol_endpoint, self.partner_fr.peppol_endpoint)
        contact = self.partner_fr.child_ids
        with Form(contact, view='base.view_partner_form') as contact_form:
            contact_form.peppol_eas = '0088'
            contact_form.peppol_endpoint = '1234567890128'
        self.assertEqual(contact.peppol_endpoint, '1234567890128')

    def test_invoice_contact_form_country(self):
        # Reuse the available EAS list to hide configuration where an independent
        # billing address is not allowed, including after an onchange.
        with Form(self.partner_be, view='base.view_partner_form') as partner_form:
            with partner_form.child_ids.new() as contact_form:
                contact_form.type = 'invoice'
                contact_form.name = 'Billing service'
                self.assertTrue(contact_form._get_modifier('peppol_endpoint', 'invisible'))
                contact_form.country_id = self.env.ref('base.nl')
                self.assertFalse(contact_form._get_modifier('peppol_endpoint', 'invisible'))
        contact = self.partner_be.child_ids
        with Form(contact, view='base.view_partner_form') as contact_form:
            self.assertFalse(contact_form._get_modifier('peppol_endpoint', 'invisible'))
            contact_form.country_id = self.env.ref('base.be')
            self.assertTrue(contact_form._get_modifier('peppol_endpoint', 'invisible'))

    def test_invoice_contact_export(self):
        # Neither the company nor the contact is French. Cross-country billing
        # addresses must also work without the French localization installed.
        contact = self._create_invoice_contact(
            parent=self.partner_be,
            country_id=self.env.ref('base.nl').id,
            peppol_eas='0088',
            peppol_endpoint='1234567890128',
        )
        invoice = self._create_invoice_one_line(product_id=self.product_a, partner_id=contact, post=True)
        for new_helpers in (True, False):
            with self.subTest(new_helpers=new_helpers):
                self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', new_helpers)
                xml, errors = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)
                self.assertFalse(errors)
                tree = etree.fromstring(xml)
                customer = tree.find('./{*}AccountingCustomerParty/{*}Party')
                endpoint = customer.find('./{*}EndpointID')
                self.assertEqual(endpoint.text, contact.peppol_endpoint)
                self.assertEqual(endpoint.get('schemeID'), contact.peppol_eas)
                self.assertEqual(customer.findtext('./{*}PartyTaxScheme/{*}CompanyID'), self.partner_be.vat)
                self.assertEqual(
                    tree.findtext('./{*}AccountingSupplierParty/{*}Party/{*}EndpointID'),
                    self.env.company.partner_id.peppol_endpoint,
                )

    def test_invoice_contact_cii_export(self):
        self.env.company.partner_id.write({'email': 'billing@example.com', 'phone': '+3212345678'})
        contact = self._create_invoice_contact(
            parent=self.partner_be,
            country_id=self.env.ref('base.nl').id,
            peppol_eas='0088',
            peppol_endpoint='1234567890128',
        )
        invoice = self._create_invoice_one_line(product_id=self.product_a, partner_id=contact, post=True)
        xml, errors = self.env['account.edi.xml.cii']._export_invoice(invoice)
        self.assertFalse(errors)
        customer = etree.fromstring(xml).find('.//{*}BuyerTradeParty')
        endpoint = customer.find('./{*}URIUniversalCommunication/{*}URIID')
        self.assertEqual(endpoint.text, contact.peppol_endpoint)
        self.assertEqual(endpoint.get('schemeID'), contact.peppol_eas)

    def test_invoice_contact_matching_precedes_vat(self):
        self.partner_be.supplier_rank = 10
        for endpoint in ('1234567890128', '1234567890135'):
            contact = self._create_invoice_contact(
                parent=self.partner_be,
                country_id=self.env.ref('base.nl').id,
                peppol_eas='0088',
                peppol_endpoint=endpoint,
            )
            bill = self.env['account.move'].create({'move_type': 'in_invoice'})
            values = {
                'company': self.env.company,
                'invoice': bill,
                'customer_values': {
                    'vat': self.partner_be.vat,
                    'peppol_eas': '0088',
                    'peppol_endpoint': endpoint,
                },
                'to_write': {},
            }
            for edi_format in ('ubl_bis3', 'facturx'):
                values['customer_values'].pop('customer', None)
                values['to_write'].clear()
                builder = contact._get_edi_builder(edi_format)
                builder._import_retrieve_customer(values)
                self.assertEqual(values['to_write']['partner_id'], contact.id)

    def test_shared_endpoint_matching_falls_back_to_company(self):
        contacts = self._create_invoice_contact() | self._create_invoice_contact()
        for eas, endpoint in (
            (self.partner_fr.peppol_eas, self.partner_fr.peppol_endpoint),
            ('0088', '1234567890128'),
        ):
            # Several billing services can share an address even when their
            # company uses another one. No VAT is supplied to mask ambiguity.
            contacts.write({'peppol_eas': eas, 'peppol_endpoint': endpoint})
            for edi_format in ('ubl_bis3', 'facturx'):
                with self.subTest(eas=eas, endpoint=endpoint, edi_format=edi_format):
                    values = {
                        'company': self.env.company,
                        'invoice': self.env['account.move'].create({'move_type': 'in_invoice'}),
                        'customer_values': {'peppol_eas': eas, 'peppol_endpoint': endpoint},
                        'to_write': {},
                    }
                    self.partner_fr._get_edi_builder(edi_format)._import_retrieve_customer(values)
                    self.assertEqual(values['to_write']['partner_id'], self.partner_fr.id)

    def test_shared_endpoint_matching_across_companies(self):
        for parent in (self.partner_fr, self.partner_be):
            self._create_invoice_contact(
                parent=parent,
                country_id=self.env.ref('base.fr').id,
                peppol_eas='0088',
                peppol_endpoint='1234567890128',
            )
        # An address shared by unrelated companies cannot identify a parent.
        customer_values = {'peppol_eas': '0088', 'peppol_endpoint': '1234567890128'}
        self.env['res.partner']._import_retrieve_customer(
            [self.env['res.partner']._import_retrieve_customer_from_eas_endpoint],
            self.env.company,
            [customer_values],
        )
        self.assertFalse(customer_values.get('customer'))
