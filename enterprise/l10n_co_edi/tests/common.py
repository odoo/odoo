# coding: utf-8
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tools import misc
from odoo import Command

from unittest.mock import patch, Mock
from freezegun import freeze_time
import datetime
from contextlib import contextmanager

from pytz import timezone


class TestCoEdiCommon(AccountEdiTestCommon):

    @contextmanager
    def mock_carvajal(self):
        return_value_upload = {
            'message': 'mocked success',
            'transactionId': 'mocked_success',
        }

        return_value_check = {
            'filename': 'mock_signed_file',
            'xml_file': b'file_content',
            'attachments': None,
            'l10n_co_edi_cufe_cude_ref': 'cufe_cude ref',
            'message': 'successfully mocked'
        }

        try:
            with freeze_time(self.frozen_today), \
                 patch('odoo.addons.l10n_co_edi.models.carvajal_request.CarvajalRequest.upload',
                       new=Mock(return_value=return_value_upload)), \
                 patch('odoo.addons.l10n_co_edi.models.carvajal_request.CarvajalRequest.check_status',
                       new=Mock(return_value=return_value_check)), \
                 patch('odoo.addons.l10n_co_edi.models.carvajal_request.CarvajalRequest.client',
                       new=Mock(return_value=None)):
                yield
        finally:
            pass


    @classmethod
    @AccountEdiTestCommon.setup_country('co')
    @AccountEdiTestCommon.setup_edi_format('l10n_co_edi.edi_carvajal')
    def setUpClass(cls):
        super().setUpClass()

        cls.frozen_today = datetime.datetime(year=2020, month=8, day=27, hour=0, minute=0, second=0, tzinfo=timezone('utc'))

        cls.salesperson = cls.env.ref('base.user_admin')
        cls.salesperson.function = 'Funcionario de ventas y trato al cliente final'

        report_text = 'GRANDES CONTRIBUYENTES SHD Res. DDI-042065 13-10-17'
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.co').id,
            'l10n_co_edi_header_gran_contribuyente': report_text,
            'l10n_co_edi_header_tipo_de_regimen': report_text,
            'l10n_co_edi_header_retenedores_de_iva': report_text,
            'l10n_co_edi_header_autorretenedores': report_text,
            'l10n_co_edi_header_resolucion_aplicable': report_text,
            'l10n_co_edi_header_actividad_economica': report_text,
            'l10n_co_edi_header_bank_information': report_text,
            'l10n_co_edi_username': 'test',
            'l10n_co_edi_password': 'test',
            'l10n_co_edi_company': 'test',
            'l10n_co_edi_account': 'test',
            'vat': '213123432-1',
            'phone': '+57 123 4567890 123',  # Colombian telephone numbers are 10 digit numbers (January 2024); longer here to test shortening
            'website': 'http://www.example.com',
            'email': 'info@yourcompany.example.com',
            'street': 'Route de Ramilies',
            'zip': '1234',
            'city': 'Bogota',
            'state_id': cls.env.ref('base.state_co_01').id,
            'tax_calculation_rounding_method': 'round_globally',
        })

        if 'l10n_co_dian_provider' in cls.env['res.company']._fields:
            # when l10n_co_dian is installed, DIAN is used by default (and Carvajal is disabled)
            cls.company_data['company'].l10n_co_dian_provider = 'carvajal'

        cls.company_data['company'].partner_id.write({
            'l10n_latam_identification_type_id': cls.env.ref('l10n_co.rut').id,
            'l10n_co_edi_obligation_type_ids': [(6, 0, [cls.env.ref('l10n_co_edi.obligation_type_1').id])],
            'l10n_co_edi_large_taxpayer': True,
        })
        cls.company_data['default_journal_sale'].write({
            'l10n_co_edi_dian_authorization_end_date': cls.frozen_today,
            'l10n_co_edi_dian_authorization_number': 42,
            'l10n_co_edi_dian_authorization_date': cls.frozen_today,
        })
        cls.company_data['default_journal_purchase'].write({
            'l10n_co_edi_dian_authorization_end_date': cls.frozen_today,
            'l10n_co_edi_dian_authorization_number': 42,
            'l10n_co_edi_dian_authorization_date': cls.frozen_today,
        })

        cls.company_data_2 = cls.setup_other_company(
            name='company_2_data',
            country_id=cls.env.ref('base.co').id,
            phone='(870)-931-0505',
            website='http://wwww.company_2.com',
            email='company_2@example.com',
            street='Route de Eghezée',
            zip='4567',
            city='Medellín',
            state_id=cls.env.ref('base.state_co_02').id,
            vat='213.123.432-1',
        )

        cls.company_data_2['company'].partner_id.write({
            'l10n_latam_identification_type_id': cls.env.ref('l10n_co.rut').id,
            'l10n_co_edi_obligation_type_ids': [(6, 0, [cls.env.ref('l10n_co_edi.obligation_type_1').id])],
            'l10n_co_edi_large_taxpayer': True,
        })

        cls.tax = cls.company_data['default_tax_sale']
        cls.tax.write({
            'amount': 15,
            'l10n_co_edi_type': cls.env.ref('l10n_co_edi.tax_type_0').id
        })
        cls.retention_tax = cls.tax.copy({
            'name': 'retention_tax',
            'l10n_co_edi_type': cls.env.ref('l10n_co_edi.tax_type_9').id
        })

        cls.tax_group = cls.env['account.tax'].create({
            'name': 'tax_group',
            'amount_type': 'group',
            'amount': 0.0,
            'type_tax_use': 'sale',
            'l10n_co_edi_type': cls.env.ref('l10n_co_edi.tax_type_0').id,
            'children_tax_ids': [(6, 0, (cls.tax + cls.retention_tax).ids)],
        })

        uom = cls.env.ref('uom.product_uom_unit')

        cls.product_a.write({
            'default_code': 'P0000',
            'uom_id': uom,
            'l10n_co_edi_ref_nominal_tax': 500.0,
        })
        invoice_data = {
            'partner_id': cls.company_data_2['company'].partner_id.id,
            'move_type': 'out_invoice',
            'ref': 'reference',
            'invoice_user_id': cls.salesperson.id,
            'invoice_payment_term_id': cls.env.ref('account.account_payment_term_end_following_month').id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': cls.product_a.id,
                    'quantity': 150,
                    'price_unit': 250,
                    'discount': 10,
                    'name': 'Line 1',
                    'tax_ids': [Command.set((cls.tax + cls.retention_tax).ids)],
                }),
            ]
        }
        cls.invoice = cls.env['account.move'].create(invoice_data)

        # Invoice in non-company currency
        cls.currency_usd = cls.env.ref('base.USD')
        cls.currency_usd.active = True
        cls.env['res.currency.rate'].create({
            'name': cls.frozen_today,
            'company_id': cls.company_data['company'].id,
            'currency_id': cls.currency_usd.id,
            'rate': 1 / 3919.109578})
        cls.invoice_multicurrency = cls.env['account.move'].create({
            **invoice_data,
            'invoice_line_ids': [
                Command.create({
                    'product_id': cls.product_a.id,
                    'quantity': 1,
                    'price_unit': 252.2,
                    'discount': 10,
                    'name': 'Line 1',
                    'tax_ids': [Command.set((cls.tax + cls.retention_tax).ids)],
                }),
            ],
            'currency_id': cls.currency_usd.id,
        })

        cls.sugar_tax_1 = cls.env['account.tax'].create({
            'name': "IBUA >10gr 50ml",  # arbitrary values
            'amount_type': 'fixed',
            'amount': 17.5,  # actual rate of the tax = 35 (for a product with >10gr of sugar per 100ml)
            'l10n_co_edi_type': cls.env.ref('l10n_co_edi.tax_type_20').id,
        })
        cls.sugar_tax_2 = cls.sugar_tax_1.copy({
            'name': "IBUA >6gr & <10gr 50ml",
            'amount': 18,  # actual rate of the tax = 36 (for a product with >10gr of sugar per 100ml)
        })
        # an IBUA tax group to display the total IBUA tax amount in the tax totals section on the invoice
        cls.env['account.tax'].create({
            'name': 'IBUA',
            'amount_type': 'group',
            'amount': 0.0,
            'type_tax_use': 'sale',
            'children_tax_ids': [Command.set([cls.sugar_tax_1.id, cls.sugar_tax_2.id])],
        })
        cls.product_sugar = cls.env['product.product'].create({
            'name': 'Ice Cream',
            'uom_id': uom.id,
            'l10n_co_edi_ref_nominal_tax': 50.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'default_code': 'P0000',
        })

        # Sugar Invoice
        invoice_data['invoice_line_ids'] = [
            # Sugar taxes should not be grouped together since they have different rates
            Command.create({
                'product_id': cls.product_sugar.id,
                'quantity': 1,
                'price_unit': 100,
                'tax_ids': [Command.set([cls.tax.id, cls.sugar_tax_1.id])],
            }),
            Command.create({
                'product_id': cls.product_sugar.id,
                'quantity': 10,
                'price_unit': 200,
                'tax_ids': [Command.set([cls.tax.id, cls.sugar_tax_2.id])],
            }),
            # The following taxes should be grouped together (same CO tax code, amount, and amount_type)
            Command.create({
                'product_id': cls.product_a.id,
                'quantity': 10,
                'price_unit': 100,
                'tax_ids': [Command.set([cls.tax.id, cls.retention_tax.id])],
            }),
            Command.create({
                'product_id': cls.product_a.id,
                'quantity': 5,
                'price_unit': 100,
                'tax_ids': [Command.set([cls.tax.id, cls.retention_tax.id])],
            }),
        ]
        cls.sugar_tax_invoice = cls.env['account.move'].create(invoice_data)

        cls.tax_iva_19 = cls.env['account.tax'].create({
            'name': "IVA Ventas 19%",
            'amount': 19,
            'l10n_co_edi_type': cls.env.ref('l10n_co_edi.tax_type_0').id,
        })
        cls.tax_iva_5 = cls.env['account.tax'].create({
            'name': "IVA Ventas 5%",
            'amount': 5,
            'l10n_co_edi_type': cls.env.ref('l10n_co_edi.tax_type_0').id,
        })
        cls.tax_iva_excento_0 = cls.env['account.tax'].create({
            'name': "IVA Excento",
            'amount': 0,
            'l10n_co_edi_type': cls.env.ref('l10n_co_edi.tax_type_0').id,
        })
        cls.tax_iva_excluido_0 = cls.env['account.tax'].create({
            'name': "IVA Excluido",
            'amount': 0,
            'l10n_co_edi_type': cls.env.ref('l10n_co_edi.tax_type_0').id,
        })

        # Testing the grouping inside the TIM sections: invoice with 2 IVA taxes with different rates and 1 Bolsas
        invoice_data['invoice_line_ids'] = [
            # IVA 5% and IVA 19% should be grouped inside the same TIM section
            Command.create({
                'product_id': cls.product_a.id,
                'quantity': 1,
                'price_unit': 100,
                'tax_ids': [Command.set([cls.tax_iva_19.id])],
            }),
            Command.create({
                'product_id': cls.product_a.id,
                'quantity': 1,
                'price_unit': 200,
                'tax_ids': [Command.set([cls.tax_iva_5.id])],
            }),
            # The Bolsas tax should be in another TIM section
            Command.create({
                'product_id': cls.product_a.id,
                'quantity': 1,
                'price_unit': 200,
                'tax_ids': [Command.set([cls.tax_iva_19.id, cls.retention_tax.id])],
            }),
            # IVA Excento (IVA, 0%) and IVA Excluido (IVA, 0%): both should be grouped together (same rate and CO type)
            Command.create({
                'product_id': cls.product_a.id,
                'quantity': 1,
                'price_unit': 400,
                'tax_ids': [Command.set([cls.tax_iva_excento_0.id])],
            }),
            Command.create({
                'product_id': cls.product_a.id,
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [Command.set([cls.tax_iva_excluido_0.id])],
            }),
            Command.create({'display_type': 'line_section', 'name': 'Section'}),
            Command.create({'display_type': 'line_note', 'name': 'Note'}),
        ]
        cls.invoice_tim = cls.env['account.move'].create(invoice_data)

        cls.in_invoice = cls.env['account.move'].create({
            **invoice_data,
            'move_type': 'in_invoice',
            'invoice_date': cls.frozen_today,
        })

        cls.expected_invoice_xml = misc.file_open('l10n_co_edi/tests/accepted_invoice.xml', 'rb').read()
        cls.expected_invoice_multicurrency_xml = misc.file_open('l10n_co_edi/tests/accepted_invoice_multicurrency.xml', 'rb').read()
        cls.expected_sugar_tax_invoice_xml = misc.file_open('l10n_co_edi/tests/accepted_sugar_tax_invoice.xml', 'rb').read()
        cls.expected_credit_note_xml = misc.file_open('l10n_co_edi/tests/accepted_credit_note.xml', 'rb').read()
        cls.expected_invoice_tim_xml = misc.file_open('l10n_co_edi/tests/accepted_invoice_tim.xml', 'rb').read()
        cls.expected_in_invoice_xml = misc.file_open('l10n_co_edi/tests/accepted_in_invoice.xml', 'rb').read()
