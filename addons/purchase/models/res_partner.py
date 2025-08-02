# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_purchase_order_count(self):
        self.purchase_order_count = 0
        if not self.env.user._has_group('purchase.group_purchase_user'):
            return

        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)],
            ['parent_id'],
        )
        purchase_order_groups = self.env['purchase.order']._read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            groupby=['partner_id'], aggregates=['__count'],
        )
        self_ids = set(self._ids)

        for partner, count in purchase_order_groups:
            while partner:
                if partner.id in self_ids:
                    partner.purchase_order_count += count
                partner = partner.parent_id

    property_purchase_currency_id = fields.Many2one(
        'res.currency', string="Supplier Currency", company_dependent=True,
        help="This currency will be used for purchases from the current partner")
    purchase_order_count = fields.Integer(
        string="Purchase Order Count",
        groups='purchase.group_purchase_user',
        compute='_compute_purchase_order_count',
    )
    purchase_warn_msg = fields.Text('Message for Purchase Order')

    receipt_reminder_email = fields.Boolean('Receipt Reminder', company_dependent=True,
        help="Automatically send a confirmation email to the vendor X days before the expected receipt date, asking him to confirm the exact date.")
    reminder_date_before_receipt = fields.Integer('Days Before Receipt', company_dependent=True,
        help="Number of days to send reminder email before the promised receipt date")
    buyer_id = fields.Many2one('res.users', string='Buyer')
    show_currency_warning = fields.Boolean(
        string="Show Purchase Currency Warning",
        store=False,
    )

    def _compute_application_statistics_hook(self):
        data_list = super()._compute_application_statistics_hook()
        if not self.env.user.has_group('purchase.group_purchase_user'):
            return data_list
        for partner in self.filtered(lambda partner: partner.purchase_order_count):
            stat_info = {'iconClass': 'fa-credit-card', 'value': partner.purchase_order_count, 'label': _('Purchases')}
            data_list[partner.id].append(stat_info)
        return data_list

    @api.onchange('property_purchase_currency_id')
    def _onchange_show_currency_warning(self):
        has_supplierinfo = self.env["product.supplierinfo"].search_count([('partner_id', 'in', self.ids)], limit=1)
        if has_supplierinfo and self._origin.property_purchase_currency_id != self.property_purchase_currency_id:
            self.show_currency_warning = True
        else:
            self.show_currency_warning = False

    def action_open_supplierinfo_pricelists(self):
        self.ensure_one()
        return {
            'name': self.env._('Vendor Pricelists'),
            'res_model': 'product.supplierinfo',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,kanban,form',
            'context': dict(self._context, search_default_partner_id=self.id),
        }

    def write(self, vals):
        res = super().write(vals)
        if 'property_purchase_currency_id' in vals:
            supplierinfo = self.env['product.supplierinfo'].search([('partner_id', 'in', self.ids)])
            if supplierinfo:
                supplierinfo.write({'currency_id': vals.get('property_purchase_currency_id')})
        return res
