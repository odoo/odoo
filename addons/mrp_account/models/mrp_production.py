# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, _


class MrpProductionWorkcenterLineTime(models.Model):
    _inherit = 'mrp.production.productivity'

    used = fields.Boolean('Used')


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.multi
    def _cal_price(self, consumed_moves):
        work_center_cost = 0
        if self.work_order_ids:
            duration = 0
            for work_order in self.work_order_ids:
                time_lines = work_order.time_ids.filtered(lambda x: x.state == 'done' and not x.used)
                duration += sum(time_lines.mapped('duration'))
                time_lines.write({'used': True})
                work_center_cost += (duration / 60) * work_order.workcenter_id.costs_hour
        for move in self.move_finished_ids.filtered(lambda x: x.product_id.id == self.product_id.id and x.state not in ('done', 'cancel')):
            if move.product_id.cost_method in ('real', 'average'):
                move.price_unit = (sum([q.qty * q.cost for q in consumed_moves.mapped('quant_ids')]) + work_center_cost) / move.product_qty
        return True

    def _costs_generate(self):
        """ Calculates total costs at the end of the production.
        :param production: Id of production order.
        :return: Calculated amount.
        """
        self.ensure_one()
        AccountAnalyticLine = self.env['account.analytic.line']
        amount = 0.0
        for wc_line in self.workcenter_line_ids:
            wc = wc_line.workcenter_id
            if wc.costs_hour_account_id:
                # Cost per hour
                value = wc_line.hour * wc.costs_hour
                account = wc.costs_hour_account_id.id
                if value and account:
                    amount += value
                    # we user SUPERUSER_ID as we do not guarantee an mrp user
                    # has access to account analytic lines but still should be
                    # able to produce orders
                    AccountAnalyticLine.sudo().create({
                        'name': wc_line.name + ' (H)',
                        'amount': value,
                        'account_id': account,
                        'ref': wc.code,
                        'unit_amount': wc_line.hour,
                    })
        return amount
