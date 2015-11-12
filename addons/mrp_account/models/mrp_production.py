# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'


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
