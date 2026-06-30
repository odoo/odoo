from odoo import api, fields, models


class L10nInBoeLine(models.Model):
    _name = 'l10n_in.boe.line'
    _description = 'BOE Line'

    move_id = fields.Many2one('account.move', string="BOE Move", required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='move_id.company_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    product_id = fields.Many2one('product.product')
    assessable_value = fields.Monetary()
    custom_duty = fields.Monetary()
    tax_id = fields.Many2one('account.tax', domain="[('type_tax_use', '=', 'purchase')]")

    taxable_amount = fields.Monetary(compute='_compute_line_amounts')
    tax_amount = fields.Monetary(compute='_compute_line_amounts')

    @api.depends('assessable_value', 'custom_duty', 'tax_id')
    def _compute_line_amounts(self):
        for line in self:
            line.taxable_amount = line.assessable_value + line.custom_duty
            if line.tax_id and line.taxable_amount:
                taxes = line.tax_id.compute_all(
                    line.taxable_amount,
                    product=line.product_id,
                )
                line.tax_amount = taxes['total_included'] - taxes['total_excluded']
            else:
                line.tax_amount = 0.0

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ['custom_duty', 'tax_id', 'assessable_value']):
            self.move_id._sync_l10n_in_boe_move()
        return res

    def unlink(self):
        moves = self.mapped('move_id')
        res = super().unlink()
        moves._sync_l10n_in_boe_move()
        return res
