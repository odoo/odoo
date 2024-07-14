# -*- coding: utf-8 -*-
from freezegun import freeze_time
from unittest.mock import patch

from odoo.tools import misc
from odoo.tests import tagged
from odoo.addons.l10n_cl_edi.tests.common import TestL10nClEdiCommon, _check_with_xsd_patch


@tagged('post_install_l10n', 'post_install', '-at_install')
@patch('odoo.tools.xml_utils._check_with_xsd', _check_with_xsd_patch)
class TestL10nClExportsDte(TestL10nClEdiCommon):
    """
    Summary of the document types to test:
        - 110:
            - An exportation invoice
    """

    @freeze_time('2019-10-22T20:23:27', tz_offset=3)
    def test_l10n_cl_dte_110(self):
        foreign_partner = self.env['res.partner'].create({
            'name': 'Mitchell Admin',
            'country_id': self.env.ref('base.us').id,
            'city': 'Scranton',
            'state_id': self.env.ref('base.state_us_39').id,
            'street': '215 Vine St',
            'phone': '+1 555-555-5555',
            'company_id': self.company_data['company'].id,
            'email': 'admin@yourcompany.example.com',
            'l10n_latam_identification_type_id': self.env.ref('l10n_latam_base.it_pass').id,
            'l10n_cl_sii_taxpayer_type': '4',
            'vat': '123456789',
        })
        currency_usd = self.env.ref('base.USD')
        currency_usd.active = True
        self.env['res.currency.rate'].create({
            'name': '2019-10-22',
            'company_id': self.company_data['company'].id,
            'currency_id': currency_usd.id,
            'rate': 0.0013})
        pay_term_today = self.env['account.payment.term'].create({
            'name': 'Today',
            'line_ids': [
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 100,
                    'nb_days': 0,
                }),
            ],
        })
        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'partner_id': foreign_partner.id,
            'move_type': 'out_invoice',
            'invoice_date': '2019-10-22',
            'invoice_date_due': '2019-10-22',
            'currency_id': currency_usd.id,
            'journal_id': self.sale_journal.id,
            'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_fe_dte').id,
            'l10n_cl_customs_sale_mode': '1',
            'company_id': self.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 2,
                'price_unit': 5018.75,
                'tax_ids': [],
            })],
            'invoice_payment_term_id': pay_term_today.id,
            'l10n_cl_port_origin_id': self.env.ref('l10n_cl_edi_exports.port_904').id,
            'l10n_cl_port_destination_id': self.env.ref('l10n_cl_edi_exports.port_293').id,
            'l10n_cl_customs_quantity_of_packages': 2,
            'l10n_cl_customs_service_indicator': False,
            'l10n_cl_customs_transport_type': '01',
            'invoice_incoterm_id': self.env.ref('account.incoterm_CIF').id,
        })

        invoice.with_context(skip_xsd=True).action_post()

        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_cl_dte_status, 'not_sent')

        xml_expected_dte = misc.file_open('l10n_cl_edi_exports/tests/expected_dtes/dte_110.xml').read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_attachment(invoice.l10n_cl_sii_send_file),
            self.get_xml_tree_from_string(xml_expected_dte.encode()),
        )
