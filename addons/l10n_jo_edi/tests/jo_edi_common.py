from odoo import Command
from odoo.tools import misc
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class JoEdiCommon(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('jo')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'name': 'Jordan Company',
            'vat': '8000514',
        })

        def _get_general_tax(amount):
            return cls.env['account.tax'].search([
                ('amount', '=', amount),
                ('amount_type', '=', 'percent'),
                ('type_tax_use', '=', 'sale'),
                ('company_id', '=', cls.company_data['company'].id)
            ], limit=1)

        def _create_special_tax(amount):
            return cls.env['account.tax'].create(
                {
                    'name': f'Fixed {amount}',
                    'amount_type': 'fixed',
                    'amount': amount,
                    'company_id': cls.company_data['company'].id,
                    'include_base_amount': True,
                    'is_base_affected': False,
                    'sequence': 0,
                })

        cls.jo_general_tax_10 = _get_general_tax(10)
        cls.jo_special_tax_10 = _create_special_tax(10)
        cls.jo_special_tax_5 = _create_special_tax(5)
        cls.jo_general_tax_16_included = _get_general_tax(16)
        cls.jo_general_tax_16_included.price_include = True

        cls.partner_jo = cls.env['res.partner'].create({
            'name': 'Ahmad',
            'ref': 'Jordan Partner',
            'city': 'Amman',
            'vat': '54321',
            'zip': '94538',
            'country_id': cls.env.ref('base.jo').id,
            'state_id': cls.env.ref('base.state_jo_az').id,
            'phone': '+962 795-5585-949',
            'company_type': 'company',
        })

        # The rate of 1 USD = 2 JOD is meant to simplify tests
        cls.usd = cls.env.ref('base.USD')
        cls.setup_currency_rate(cls.usd, 0.5)

        cls.company = cls.company_data['company']

    @classmethod
    def setup_currency_rate(cls, currency, rate):
        currency.sudo().update({
            'rate_ids': [Command.clear()],
            'active': True,
        })
        return cls.env['res.currency.rate'].create({
            'name': '2019-01-01',
            'rate': rate,
            'currency_id': currency.id,
            'company_id': cls.company_data['company'].id,
        })

    def _l10n_jo_create_invoice(self, invoice_vals):
        invoice_vals.update({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner_jo.id,
            'invoice_date': invoice_vals.get('invoice_date', '2019-01-01'),
        })
        move = self.env['account.move'].create(invoice_vals)
        move.action_post()
        return move

    def _l10n_jo_create_refund(self, invoice_vals, return_reason, refund_vals):
        invoice = self._l10n_jo_create_invoice(invoice_vals)
        reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'reason': return_reason,
            'journal_id': invoice.journal_id.id,
        }).refund_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])
        if 'invoice_line_ids' in refund_vals:
            # because they will be set by refund_vals
            reverse_move.invoice_line_ids = [Command.clear()]
        reverse_move.update(refund_vals)
        reverse_move.action_post()
        return reverse_move

    def _read_xml_test_file(self, file_name):
        with misc.file_open(f'l10n_jo_edi/tests/test_files/{file_name}.xml', 'rb') as file:
            result_file = file.read()
        return result_file
