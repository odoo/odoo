# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class SeAccountTestCommon(AccountTestInvoicingCommon):
    """Swedish company on the K2 chart with a Swedish customer."""

    country_code = 'SE'
    chart_template = 'se_K2'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_se = cls.env['res.partner'].create({
            'name': 'Svensk Kund AB',
            'is_company': True,
            'country_id': cls.env.ref('base.se').id,
        })

    def _invoice(self, move_type, amount=1000.0):
        tax = self.env['account.chart.template'].ref('sale_tax_25_goods')
        return self._create_invoice(
            move_type=move_type,
            partner_id=self.partner_se.id,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=amount, tax_ids=tax)],
            post=True,
        )
