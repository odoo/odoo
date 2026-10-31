from odoo.addons.l10n_hr_edi.tests.test_hr_edi_common import TestL10nHrEdiCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nHrPaymentUnreported(TestL10nHrEdiCommon):

    def test_search_payment_unreported(self):
        """ The "Has unreported payments" filter only matches the moves whose reported
            amount differs from what was paid. """
        unreported = self._create_invoice_one_line(price_unit=100.0, post=True)
        reported = self._create_invoice_one_line(price_unit=100.0, post=True)
        self.env['l10n_hr_edi.addendum'].create({
            'move_id': unreported.id,
            'payment_reported_amount': 42.0,
        })

        both = unreported + reported
        self.assertEqual(
            both.search([('id', 'in', both.ids), ('l10n_hr_payment_unreported', '!=', False)]),
            unreported,
        )
        self.assertEqual(
            both.search([('id', 'in', both.ids), ('l10n_hr_payment_unreported', '=', False)]),
            reported,
        )
