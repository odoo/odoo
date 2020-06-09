from odoo import models, fields


class AccountTax(models.Model):
    _inherit = "account.tax"

    amount_type = fields.Selection(selection_add=([('partner_tax', 'Partner Tax')]))

    def _compute_amount(
            self, base_amount, price_unit, quantity=1.0, product=None, partner=None, is_refund=False,
            handle_price_include=True, date=None):
        if self.amount_type == 'partner_tax':
            partner_tax = self._get_partner_tax(partner, date=date)
            if not partner_tax:
                return 0.0
            if self._context.get('force_price_include', self.price_include):
                return base_amount - (base_amount / (1 + partner_tax.amount / 100))
            else:
                return base_amount * partner_tax.amount / 100
        else:
            return super()._compute_amount(
                base_amount, price_unit, quantity=quantity, product=product, partner=partner, date=date)

    def _get_partner_tax(self, partner, date=None):
        self.ensure_one()
        if partner:
            date = date or fields.Date.today()
            return partner.tax_ids.search([
                ('tax_id', '=', self.id),
                ('partner_id', '=', partner.commercial_partner_id.id),
                '|',
                ('from_date', '=', False),
                ('from_date', '<=', date),
                '|',
                ('to_date', '=', False),
                ('to_date', '>=', date),
            ], limit=1)
        else:
            return False
