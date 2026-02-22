from freezegun import freeze_time

from odoo import Command, fields

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestL10nPtCommon(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('pt')
    def setUpClass(cls):
        def create_at_series(year):
            series = cls.env['l10n_pt.at.series'].create({
                'name': year,
                'company_id': cls.company_pt.id,
                'training_series': True,
                'sale_journal_id': cls.company_data['default_journal_sale'].id,
                'payment_journal_id': cls.company_data['default_journal_bank'].id,
                'at_series_line_ids': [
                    Command.create({
                        'type': series_type,
                        'prefix': prefix,
                        'at_code': f'AT-TEST{prefix}{year}',
                    })
                    for series_type, prefix in (('out_invoice', 'INV'), ('out_refund', 'RINV'), ('payment_receipt', 'PAY'))
                ]
            })
            return series

        super().setUpClass()
        cls.company_pt = cls.company_data['company']
        cls.company_pt.write({
            'street': '25 Avenida da Liberdade',
            'city': 'Lisboa',
            'zip': '9415-343',
            'company_registry': '123456',
            'phone': '+351 11 11 11 11',
            'country_id': cls.env.ref('base.pt').id,
            'vat': 'PT123456789',
        })
        cls.company_data_2 = cls.setup_other_company()
        cls.series_2017 = create_at_series('2017')
        cls.series_2024 = create_at_series('2024')
        cls.tax_sale_23 = cls.env['account.chart.template'].ref('iva_pt_sale_normal')
        cls.tax_sale_0 = cls.env['account.chart.template'].ref('iva_pt_sale_eu_isenta')

    @classmethod
    def create_invoice(cls, move_type='out_invoice', invoice_date='2024-01-01', l10n_pt_hashed_on=None, amount=1000.0,
                       tax=None, product_id=False, do_hash=False):
        invoice_data = {
            'company_id': cls.company_pt.id,
            'move_type': move_type,
            'partner_id': cls.partner_a.id,
            'invoice_date': fields.Date.from_string(invoice_date),
            'line_ids': [
                Command.create({
                    'name': 'Product A',
                    'product_id': product_id,
                    'quantity': 1,
                    'price_unit': amount,
                    'tax_ids': [tax.id if tax else cls.tax_sale_23.id],
                }),
            ],
        }
        # For years 2017 and 2024, the AT series will be computed. If move is in a different year, set an AT Series
        if invoice_data['invoice_date'].year not in ('2017', '2024'):
            invoice_data['l10n_pt_at_series_id'] = cls.series_2024.id

        move = cls.env['account.move'].with_company(cls.company_pt).create(invoice_data)
        move.action_post()
        if do_hash:
            with freeze_time(l10n_pt_hashed_on):
                move.button_hash()
        return move
