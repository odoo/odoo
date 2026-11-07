from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import split_every


class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = ['account.tax', 'pos.load.mixin']

    pos_order_line_ids = fields.Many2many(
        comodel_name='pos.order.line',
        relation='account_tax_pos_order_line_rel',
        column1='account_tax_id',
        column2='pos_order_line_id',
        copy=False,
        readonly=True,
    )

    @api.depends('pos_order_line_ids')
    def _compute_is_used(self):
        super()._compute_is_used()
        self.sudo().search([
            ('id', 'in', self.filtered(lambda t: not t.is_used).ids),
            ('pos_order_line_ids', '!=', False),
        ]).is_used = True

    def _resolve_fpos_ids(self, vals):
        virtual = self.new(
            {"fiscal_position_ids": vals.get("fiscal_position_ids", [])},
            origin=self if self else None,
        )
        return set(virtual.fiscal_position_ids.ids)

    def _get_fpos_delta(self, vals):
        self.ensure_one()
        if 'fiscal_position_ids' not in vals:
            return set(), set()
        current = set(self.fiscal_position_ids.ids) if self else set()
        after = self._resolve_fpos_ids(vals)
        return after - current, current - after

    def _check_pos_order_usage(self, fpos_ids):
        if fpos_ids and self.env['pos.order'].sudo().search_count([
            ('fiscal_position_id', 'in', list(fpos_ids)),
            ('state', 'in', ['paid', 'done', 'invoiced']),
        ]):
            raise UserError(_(
                    "You cannot modify a fiscal position used in a POS order. "
                    "You should archive it and create a new one."
                ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if {'fiscal_position_ids', 'original_tax_ids', 'replacing_tax_ids'} & vals.keys():
                self._check_pos_order_usage(self._resolve_fpos_ids(vals))
        return super().create(vals_list)

    def write(self, vals):
        forbidden_fields = {
            'amount_type', 'amount', 'type_tax_use', 'tax_group_id', 'price_include',
            'price_include_override', 'include_base_amount', 'is_base_affected',
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
        if {'fiscal_position_ids', 'original_tax_ids', 'replacing_tax_ids'} & vals.keys():
            affected = set()
            for tax in self:
                if 'fiscal_position_ids' in vals:
                    added, removed = tax._get_fpos_delta(vals)
                    affected |= added | removed
                if {'original_tax_ids', 'replacing_tax_ids'} & vals.keys():
                    affected |= set(tax.fiscal_position_ids.ids)
            self._check_pos_order_usage(affected)
        return super(AccountTax, self).write(vals)

    @api.model
    def _load_pos_data_domain(self, data, config):
        return self.env['account.tax']._check_company_domain(config.company_id.id)

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            'id', 'name', 'price_include', 'include_base_amount', 'is_base_affected', 'has_negative_factor',
            'amount_type', 'children_tax_ids', 'amount', 'company_id', 'id', 'sequence', 'tax_group_id',
            'fiscal_position_ids',
        ]

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_in_pos_order(self):
        self._check_pos_order_usage(self.fiscal_position_ids.ids)
