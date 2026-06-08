import datetime

from freezegun import freeze_time

from odoo import Command, fields

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.account_edi_ubl_cii.tests.common import TestUblCiiCommon


class TestL10nFrAccountUblCiiCommon(TestUblCiiCommon, TestAccountMoveSendCommon):
    # Use a date after Feb decade/month end to place transaction/payment flows in grace/closed by default.
    TEST_TODAY = fields.Date.from_string('2025-03-05')
    TEST_INVOICE_DATE = fields.Date.from_string('2025-02-05')
    TEST_PAYMENT_DATE = fields.Date.from_string('2025-02-15')

    @classmethod
    @TestUblCiiCommon.setup_country('fr')
    def setUpClass(cls):
        super().setUpClass()

        cls.fakenow = datetime.datetime(2024, 12, 5)
        cls.startClassPatcher(freeze_time(cls.fakenow))

        company = cls.company_data['company']
        company.write({
            'street': 'Rue Abbé Huet',
            'city': 'Rennes',
            'zip': '35043',
            'vat': 'FR91746948785',
            'phone': '+33612345678',
            'pdp_identifier': '968515759_96851575905899'  # Should set siret, peppol_eas and peppol_endpoint
        })
        cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.company_data['company'].partner_id.id,
            'acc_number': 'FR5000400440116243',
            'allow_out_payment': True,
        })

        cls.partner_a = cls.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': cls.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'siret': '96851575905823',
            'invoice_edi_format': 'ubl_21_fr',
            'peppol_eas': '0225',
            'peppol_endpoint': '968515759_96851575905823',
        })
        cls.partner_b.write({
            'name': 'SUPER BELGIAN PARTNER',
            'street': 'Rue du Paradis, 10',
            'zip': '6870',
            'city': 'Eghezee',
            'country_id': cls.env.ref('base.be').id,
            'phone': '061928374',
            'vat': 'BE0897223670',
            'invoice_edi_format': 'ubl_bis3',
            'peppol_eas': '0208',
            'peppol_endpoint': '0239843188',
        })

    # -------------------------------------------------------------------------
    # ACCOUNTING HELPERS
    # -------------------------------------------------------------------------

    def _create_french_invoice(self, move_type='out_invoice', **kwargs):
        tax_1 = self.env['account.chart.template'].ref('tva_acq_normale')
        tax_2 = self.env['account.chart.template'].ref('tva_acq_specifique')
        return self.env["account.move"].create({
            'move_type': move_type,
            'partner_id': self.partner_a.id,
            'partner_bank_id': self.env.company.partner_id.bank_ids[:1].id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'narration': 'test narration',
            'ref': 'ref_move',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(tax_1.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax_2.ids)],
                }),
            ],
            **kwargs,
        })

    # -------------------------------------------------------------------------
    # ACCOUNTING HELPERS
    # -------------------------------------------------------------------------
    @classmethod
    def _send_patched(cls, invoice):
        # The successful verification sets the `invoice_sending_method` to `peppol` on the partner
        wizard = cls.env['account.move.send.wizard'] \
            .with_context(active_model=invoice._name, active_ids=invoice.ids) \
            .create({})
        wizard.action_send_and_print()
