# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nSGReverseChargeTax(AccountTestInvoicingCommon):
    """ The SG reverse charge group taxes pair a -9% SRRC child with a +9%
    TXRC child, so the net GST on a bill is 0. The TXRC-TS and TXRC-ESS
    children used to ship inactive, which dropped them from the group (the
    children_tax_ids m2m hides inactive taxes), leaving only the -9% SRRC and
    a wrong -9% GST. """

    @classmethod
    @AccountTestInvoicingCommon.setup_country('sg')
    def setUpClass(cls):
        super().setUpClass()

    def _group_tax(self, trailing_xml_id):
        return self.env.ref(f"account.{self.company_data['company'].id}_{trailing_xml_id}")

    def test_reverse_charge_child_taxes_active(self):
        """ Both reverse charge child taxes must ship active, otherwise the
        group tax drops them. """
        for xml_id in ('sg_purchase_tax_txrc_ts_9', 'sg_purchase_tax_txrc_ess_9'):
            tax = self.env.ref(f"account.{self.company_data['company'].id}_{xml_id}")
            self.assertTrue(tax.active, f"{xml_id} must be active for the group tax to aggregate it")

    def test_reverse_charge_group_tax_nets_to_zero(self):
        """ A bill taxed with a reverse charge group nets to 0 GST: the -9%
        SRRC child and the +9% TXRC child cancel out. """
        for xml_id in ('sg_group_tax_rc_srrc_txrc_ts', 'sg_group_tax_rc_srrc_txrc_ess'):
            group_tax = self._group_tax(xml_id)
            bill = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2024-01-01',
                'currency_id': self.env.ref('base.SGD').id,
                'invoice_line_ids': [Command.create({
                    'name': 'reverse charge line',
                    'quantity': 1,
                    'price_unit': 10000.0,
                    'tax_ids': [Command.set(group_tax.ids)],
                })],
            })
            self.assertEqual(
                bill.amount_tax, 0.0,
                f"{xml_id}: reverse charge should net to 0 GST, the +9% TXRC "
                f"child cancels the -9% SRRC child",
            )
            self.assertEqual(bill.amount_total, 10000.0)
