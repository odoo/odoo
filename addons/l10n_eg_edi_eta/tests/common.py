from datetime import datetime, UTC

from odoo.fields import Command
from odoo.tools import BinaryBytes
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon


class TestEGEdiCommon(TestAccountMoveSendCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country('eg')
    def setUpClass(cls):
        super().setUpClass()

        cls.frozen_today = datetime(year=2022, month=3, day=15, hour=0, minute=0, second=0, tzinfo=UTC)

        cls.currency_aed_id = cls.setup_other_currency('AED', rates=[('2022-03-14', 0.198117095128)])

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        cls.company_data['company'].write({
            'l10n_eg_client_identifier': 'ahuh1pojnbakKK',
            'l10n_eg_client_secret': '1ashiqwhejmasn197',
            'vat': '123-456-789',
            'l10n_eg_edi_api_mode': 'production',
        })

        # ==== Business ====

        cls.partner_a.write({
            'vat': '123456789',
            'country_id': cls.env.ref('base.eg').id,
            'city': 'Iswan',
            'state_id': cls.env.ref('base.state_eg_c').id,
            'l10n_eg_building_no': '12',
            'street': '12th dec. street',
            'zip': '33445',
        })
        cls.partner_b.write({
            'vat': 'ESF35999705',
            'country_id': cls.env.ref('base.us').id,
            'city': 'New York City',
            'state_id': cls.env.ref('base.state_us_27').id,
            'l10n_eg_building_no': '12',
            'street': '5th avenue street',
            'zip': '54321',
        })
        cls.partner_c = cls.env['res.partner'].create({
            'name': 'عميل 1',
            'vat': '123456789',
            'country_id': cls.env.ref('base.eg').id,
            'city': 'Iswan',
            'state_id': cls.env.ref('base.state_eg_c').id,
            'l10n_eg_building_no': '12',
            'street': '12th dec. street',
            'zip': '98765',
        })

        cls.product_a.write({'barcode': '1KGS1TEST', })
        cls.product_b.write({
            'barcode': 'EG-EGS-TEST',
            'uom_id': cls.env.ref('uom.product_uom_cm').id,
        })
        cls.company_branch = cls.env['res.partner'].create({
            'name': 'branch partner',
            'vat': '456789123',
            'country_id': cls.env.ref('base.eg').id,
            'city': 'Iswan',
            'state_id': cls.env.ref('base.state_eg_c').id,
            'l10n_eg_building_no': '10',
            'street': '12th dec. street',
            'zip': '12345',
        })
        cls.company_data['default_journal_sale'].write({
            'l10n_eg_branch_id': cls.company_branch.id,
            'l10n_eg_branch_identifier': '0',
            'l10n_eg_activity_type_id': cls.env.ref('l10n_eg_edi_eta.l10n_eg_activity_type_8121').id,
        })
        cls.env['l10n_eg_edi.thumb.drive'].create({
            'company_id': cls.company.id,
            'pin': '12345678',
            'access_token': 'abcd-1234-defg-5678',
            'certificate': BinaryBytes(b'randomcertificatebytes')
        })

    @classmethod
    def _get_tax_by_xml_id(cls, trailing_xml_id):
        return cls.env.ref(f'account.{cls.env.company.id}_account_tax_template_{trailing_xml_id}')

    @classmethod
    def _create_invoice_eg(cls, **kwargs):
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
