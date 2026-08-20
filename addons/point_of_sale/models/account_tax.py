from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import split_every


class AccountTax(models.Model):
    _inherit = 'account.tax'

    pos_order_line_ids = fields.Many2many(
        comodel_name='pos.order.line',
        relation='account_tax_pos_order_line_rel',
        column1='account_tax_id',
        column2='pos_order_line_id',
        copy=False,
        readonly=True,
    )

    def write(self, vals):
        forbidden_fields = {
            'amount_type', 'amount', 'type_tax_use', 'tax_group_id', 'price_include',
            'include_base_amount', 'is_base_affected',
        }
        if forbidden_fields & set(vals.keys()):
            lines = self.env['pos.order.line'].sudo().search([
                ('order_id.session_id.state', '!=', 'closed')
            ])
            self_ids = set(self.ids)
            for lines_chunk in map(self.env['pos.order.line'].sudo().browse, split_every(100000, lines.ids)):
                if any(tid in self_ids for ts in lines_chunk.read(['tax_ids']) for tid in ts['tax_ids']):
                    raise UserError(_(
                        'It is forbidden to modify a tax used in a POS order not posted. '
                        'You must close the POS sessions before modifying the tax.'
                    ))
                lines_chunk.invalidate_recordset(['tax_ids'])
        return super(AccountTax, self).write(vals)

    @api.depends('pos_order_line_ids')
    def _compute_is_used(self):
        super()._compute_is_used()
        self.sudo().search([
            ('id', 'in', self.filtered(lambda t: not t.is_used).ids),
            ('pos_order_line_ids', '!=', False),
        ]).is_used = True
