from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    repair_order_count = fields.Integer(
        string="Repair Order Count",
        groups='stock.group_stock_user',
        compute='_compute_repair_order_count',
    )

    def _compute_repair_order_count(self):
        self.repair_order_count = 0
        if not self.env.user.has_group('stock.group_stock_user'):
            return

        repair_counts_per_partner = self.env['repair.order']._read_group(
            domain=[('partner_id', 'child_of', self.ids)],
            groupby=['partner_id'],
            aggregates=['__count'],
        )
        self_ids = set(self._ids)

        for partner, count in repair_counts_per_partner:
            while partner:
                if partner.id in self_ids:
                    partner.repair_order_count += count
                partner = partner.parent_id

    def _compute_application_statistics_hook(self):
        data_list = super()._compute_application_statistics_hook()
        if not self.env.user.has_group('stock.group_stock_user'):
            return data_list

        for partner in self:
            if not partner.repair_order_count:
                continue
            data_list[partner.id].append({
                'iconClass': 'fa-wrench',
                'value': partner.repair_order_count,
                'label': self.env._("Repair Orders"),
            })
        return data_list
