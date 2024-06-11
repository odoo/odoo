# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

import datetime
from unittest import mock


class L10nHuEdiTestCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='hu'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.today = datetime.date.today()

        # Company
        company = cls.company_data['company']
        company.write({
            'city': 'Budapest',
            'zip': '1073',
            'street': 'Akácfa utca 74.',
            'country_id': cls.env.ref('base.hu').id,
            'vat': '27725414-2-13',
        })

        cls.write_edi_credentials()

        # Products
        cls.product_service = cls.env['product.product'].create({
            'name': 'Consultancy Service',
            'type': 'service',
            'uom_id': cls.env.ref('uom.product_uom_hour').id,
            'uom_po_id': cls.env.ref('uom.product_uom_hour').id,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
        })
        cls.product_no_uom = cls.env['product.product'].create({
            'name': 'Item without UoM',
            'type': 'service',
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
        })

        # Partners
        cls.partner_company = cls.env['res.partner'].create({
            'name': 'Magyar Vevő Kft.',
            'is_company': True,
            'street': 'Alkotmány utca 11.',
            'city': 'Debrecen',
            'zip': '4000',
            'country_id': cls.env.ref('base.hu').id,
            'vat': '14933477-2-13',
        })
        cls.partner_group_company_1 = cls.env['res.partner'].create({
            'name': 'MOL Nyrt.',
            'is_company': True,
            'street': 'Dombóvári út 28.',
            'city': 'Budapest',
            'zip': '1117',
            'country_id': cls.env.ref('base.hu').id,
            'vat': '10625790-4-44',
            'l10n_hu_group_vat': '17781774-5-44',
        })
        cls.partner_group_company_2 = cls.env['res.partner'].create({
            'name': 'MOL Petrolkémia Zrt.',
            'is_company': True,
            'street': 'TVK-Ipartelep, TVK Központi Irodaház 2119/3hrsz. 136. ép.',
            'city': 'Tiszaújváros',
            'zip': '3581',
            'country_id': cls.env.ref('base.hu').id,
            'vat': '10725759-4-05',
            'l10n_hu_group_vat': '17781774-5-44',
        })

        # Currency rates
        currency_eur = cls.env.ref('base.EUR')
        currency_eur.active = True
        cls.env['res.currency.rate'].create(
            {
                'name': cls.today,
                'currency_id': currency_eur.id,
                'company_id': company.id,
                'inverse_company_rate': '380.77',
            }
        )
        cls.env['res.currency.rate'].create(
            {
                'name': cls.today - datetime.timedelta(days=1),
                'currency_id': currency_eur.id,
                'company_id': company.id,
                'inverse_company_rate': '377.66',
            }
        )

        # Taxes
        cls.tax_vat = cls.env['account.chart.template'].ref('F27')
        cls.tax_vat_18 = cls.env['account.chart.template'].ref('F18')
        cls.tax_aam = cls.env['account.chart.template'].ref('VA')
        cls.tax_price_include = cls.env['account.tax'].create({
            'name': 'Excise tax',
            'amount_type': 'percent',
            'amount': 30.0,
            'country_id': company.account_fiscal_country_id.id,
            'tax_exigibility': 'on_invoice',
            'price_include': True,
            'include_base_amount': True,
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'repartition_type': 'tax',
                    'account_id': cls.company_data['default_account_tax_sale'].id,
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'repartition_type': 'tax',
                    'account_id': cls.company_data['default_account_tax_sale'].id,
                }),
            ],
        })

    @classmethod
    def write_edi_credentials(cls):
        # Set up test EDI user
        with mock.patch.object(type(cls.env['res.company']), '_l10n_hu_edi_test_credentials', autospec=True):
            return cls.company_data['company'].write({
                'l10n_hu_edi_server_mode': 'test',
                'l10n_hu_edi_username': 'this',
                'l10n_hu_edi_password': 'that',
                'l10n_hu_edi_signature_key': 'some_key',
                'l10n_hu_edi_replacement_key': 'abcdefghijklmnop',
            })

    def create_invoice_simple(self):
        """ Create a really basic invoice - just one line. """
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'currency_id': self.env.ref('base.HUF').id,
            'partner_id': self.partner_company.id,
            'invoice_date': self.today,
            'delivery_date': self.today,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 10000.0,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_vat.ids)],
                })
            ]
        })

    def create_advance_invoice(self):
        """ Create a sale order, an advance invoice and a final invoice. """
        self.product_a.invoice_policy = 'order'
        pricelist_huf = self.env['product.pricelist'].create({
            'name': 'HUF pricelist',
            'currency_id': self.company_data['company'].currency_id.id,
            'company_id': False,
        })
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_company.id,
            'pricelist_id': pricelist_huf.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1,
                    'price_unit': 10000.0,
                    'tax_id': [Command.set(self.tax_vat.ids)],
                })
            ]
        })
        sale_order.action_confirm()

        context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        downpayment_1 = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 6350.0,
            'deposit_account_id': self.company_data['default_account_revenue'].id,
        })
        downpayment_1.create_invoices()
        advance_invoice = sale_order.invoice_ids

        downpayment_2 = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'delivered',
        })
        downpayment_2.create_invoices()
        final_invoice = sale_order.invoice_ids - advance_invoice

        return advance_invoice, final_invoice

    def create_invoice_complex_huf(self):
        """ Create a complex invoice in HUF, with cash rounding. """
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'currency_id': self.env.ref('base.HUF').id,
            'partner_id': self.partner_company.id,
            'invoice_date': self.today,
            'delivery_date': self.today,
            'l10n_hu_payment_mode': 'TRANSFER',
            'invoice_cash_rounding_id': self.env.ref('l10n_hu_edi.cash_rounding_1_huf').id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 10.00,
                    'quantity': 3,
                    'discount': 20,
                    'tax_ids': [Command.set((self.tax_vat | self.tax_price_include).ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 19.99,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_vat.ids)],
                }),
                Command.create({
                    'product_id': self.product_service.id,
                    'price_unit': 50.00,
                    'quantity': 2,
                    'tax_ids': [Command.set(self.tax_vat_18.ids)],
                }),
                Command.create({
                    'product_id': self.product_no_uom.id,
                    'price_unit': 200.00,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_aam.ids)],
                })
            ]
        })

    def create_invoice_complex_eur(self):
        """ Create a complex invoice in EUR with several lines, different taxes, and discounts. """
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'currency_id': self.env.ref('base.EUR').id,
            'partner_id': self.partner_company.id,
            'invoice_date': self.today,
            'delivery_date': self.today,
            'l10n_hu_payment_mode': 'TRANSFER',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 10.00,
                    'quantity': 3,
                    'discount': 20,
                    'tax_ids': [Command.set((self.tax_vat | self.tax_price_include).ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 19.99,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_vat.ids)],
                }),
                Command.create({
                    'product_id': self.product_service.id,
                    'price_unit': 50.00,
                    'quantity': 2,
                    'tax_ids': [Command.set(self.tax_vat_18.ids)],
                }),
                Command.create({
                    'product_id': self.product_no_uom.id,
                    'price_unit': 200.00,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_aam.ids)],
                })
            ]
        })

    def create_reversal(self, invoice, is_modify=False):
        """ Create a credit note that reverses an invoice. """
        wizard_vals = {'journal_id': invoice.journal_id.id}
        wizard_reverse = self.env['account.move.reversal'].with_context(active_ids=invoice.ids, active_model='account.move').create(wizard_vals)
        wizard_reverse.reverse_moves(is_modify=is_modify)
        return wizard_reverse.new_move_ids

    def create_cancel_wizard(self):
        """ Create an invoice, send it, and create a cancellation wizard for it. """
        invoice = self.create_invoice_simple()
        invoice.action_post()
        send_and_print = self.create_send_and_print(invoice, l10n_hu_edi_enable_nav_30=True)
        send_and_print.action_send_and_print()
        cancel_wizard = self.env['l10n_hu_edi.cancellation'].with_context({"default_invoice_id": invoice.id}).create({
            'code': 'ERRATIC_DATA',
            'reason': 'Some reason...',
        })
        return invoice, cancel_wizard
