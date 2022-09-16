from datetime import datetime
from pytz import timezone

from odoo.fields import Command
from odoo.tests import tagged
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon


class TestEGEdiCommon(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_eg.egypt_chart_template_standard', edi_format_ref='l10n_eg_edi_eta.edi_eg_eta'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.frozen_today = datetime(year=2022, month=3, day=15, hour=0, minute=0, second=0, tzinfo=timezone('utc'))

        cls.currency_aed_id = cls.env.ref('base.AED')
        cls.currency_aed_id.write({'active': True})
        cls.env['res.currency.rate'].search([]).unlink()
        cls.env['res.currency.rate'].create({'currency_id': cls.currency_aed_id.id,
                                            'rate': 0.198117095128, 'name': '2022-03-15'})

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.eg').id,
            'l10n_eg_client_identifier': 'ahuh1pojnbakKK',
            'l10n_eg_client_secret': '1ashiqwhejmasn197',
            'vat': 'EG1103143170L',
        })

        # ==== Business ====

        cls.partner_a.write({
            'vat': 'BE0477472701',
            'country_id': cls.env.ref('base.eg').id,
            'city': 'Iswan',
            'state_id': cls.env.ref('base.state_eg_c').id,
            'l10n_eg_building_no': '12',
            'street': '12th dec. street',
            'is_company': True,
        })
        cls.partner_b.write({
            'vat': 'ESF35999705',
            'country_id': cls.env.ref('base.us').id,
            'city': 'New York City',
            'state_id': cls.env.ref('base.state_us_27').id,
            'l10n_eg_building_no': '12',
            'street': '5th avenue street',
            'is_company': True,
        })
        cls.partner_c = cls.env['res.partner'].create({
            'name': 'عميل 1',
            'vat': 'EG11231212',
            'country_id': cls.env.ref('base.eg').id,
            'city': 'Iswan',
            'state_id': cls.env.ref('base.state_eg_c').id,
            'l10n_eg_building_no': '12',
            'street': '12th dec. street',
            'is_company': True,
        })

        cls.product_a.write({'barcode': '1KGS1TEST', })
        cls.product_b.write({
            'barcode': 'EG-EGS-TEST',
            'uom_id': cls.env.ref('uom.product_uom_cm').id,
        })
        cls.company_branch = cls.env['res.partner'].create({
            'name': 'branch partner',
            'vat': '918KKL1',
            'country_id': cls.env.ref('base.eg').id,
            'city': 'Iswan',
            'state_id': cls.env.ref('base.state_eg_c').id,
            'l10n_eg_building_no': '10',
            'street': '12th dec. street',
            'is_company': True,
        })
        cls.company_data['default_journal_sale'].write({
            'l10n_eg_branch_id': cls.company_branch.id,
            'l10n_eg_branch_identifier': '0',
            'l10n_eg_activity_type_id': cls.env.ref('l10n_eg_edi_eta.l10n_eg_activity_type_8121').id,
        })

    @classmethod
    def _get_tax_by_xml_id(cls, trailing_xml_id):
        return cls.env.ref(f'l10n_es.{cls.env.company.id}_account_tax_template_{trailing_xml_id}')

    @classmethod
    def create_invoice(cls, **kwargs):
        invoice = (
            cls.env['account.move']
            .with_context(edi_test_mode=True)
            .create({
                'move_type': 'out_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': '2022-03-15',
                'date': '2022-03-15',
                **kwargs,
                'invoice_line_ids': [Command.create({**line_vals, }) for line_vals in kwargs.get('invoice_line_ids', [])]
            })
        )
        # this fixes rounding issues in cache
        cls.env.invalidate_all()
        return invoice
