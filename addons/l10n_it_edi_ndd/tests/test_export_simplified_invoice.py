from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.test_edi_export import TestItEdiExport


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiNddExport(TestItEdiExport):

    def _force_simplified(self, partner):
        td07 = self.env['l10n_it.document.type'].search([('code', '=', 'TD07')], limit=1)
        return self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': partner.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'cheap_line',
                    'price_unit': 100.00,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
            'l10n_it_document_type': td07.id,
        })

    def _get_simplified_errors(self, moves):
        return [
            k
            for k, v in moves._l10n_it_edi_is_simplified_checks().items()
            if v.get('level') in ('warning', 'error')
        ]

    def test_invoice_non_domestic_force_simplified(self):
        """ If the user forces a simplified document type (i.e. TD07) on a non-italian partner, an error is raised """
        invoice = self._force_simplified(self.american_partner)
        self.assertEqual(['l10n_it_edi_move_simplified_partner'], self._get_simplified_errors(invoice))

    def test_invoice_domestic_force_simplified(self):
        """ If the user forces a simplified document type (i.e. TD07) on an italian partner, it works """
        invoice = self._force_simplified(self.italian_partner_a)
        self.assertEqual([], self._get_simplified_errors(invoice))

    def test_invoice_pa_force_simplified(self):
        """ If the user forces a simplified document type (i.e. TD07) on an italian PA partner, errors are raised """
        invoice = self._force_simplified(self.italian_partner_b)
        self.assertEqual(['l10n_it_edi_move_simplified_partner'], self._get_simplified_errors(invoice))
