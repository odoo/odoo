# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class SeAccountTestCommon(AccountTestInvoicingCommon):
    """Swedish company on the K2 chart with a Swedish customer and vendor."""

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

    @classmethod
    def _tax(cls, xmlid):
        return cls.env['account.chart.template'].ref(xmlid)

    @classmethod
    def _account(cls, code):
        return cls.env['account.chart.template'].ref(f'a{code}')

    def _box(self, code, moves):
        """Value of a tax report box for the given moves, computed like the tax report.

        The tax tag carries the box code without sign; the expression's formula sign
        decides whether the balance is reported as is or negated.
        """
        expression = self.env['account.report.expression'].search([
            ('report_line_id.report_id', '=', self.env.ref('l10n_se.tax_report').id),
            ('engine', '=', 'tax_tags'),
            ('formula', 'in', (code, f'-{code}')),
        ], limit=1)
        self.assertTrue(expression, f"no tax report expression for {code}")
        tags = expression._get_matching_tags()
        lines = moves.line_ids.filtered(lambda line: line.tax_tag_ids & tags)
        sign = -1 if expression.formula.startswith('-') else 1
        return sign * sum(lines.mapped('balance'))

    def _invoice(self, move_type, taxes, amount=1000.0, partner=None, **kwargs):
        return self._create_invoice(
            move_type=move_type,
            partner_id=(partner or self.partner_se).id,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=amount, tax_ids=taxes)],
            post=True,
            **kwargs,
        )
