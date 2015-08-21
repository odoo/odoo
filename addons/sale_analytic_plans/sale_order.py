# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models, _
from openerp.exceptions import RedirectWarning


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _get_analytic_account(self):
        self.env.cr.execute('SELECT DISTINCT acc.id, acc.complete_name '
                            'FROM account_analytic_account as acc '
                            'INNER JOIN account_analytic_plan_instance_line as plan_line on (acc.id = plan_line.analytic_account_id) '
                            'INNER JOIN account_analytic_plan_instance as plan on (plan_line.plan_id = plan.id) '
                            'INNER JOIN sale_order_line as sale_line on (plan.id = sale_line.analytics_id AND sale_line.order_id = %s) '
                            'WHERE acc.state in %s', ((tuple(self.ids)), ('close', 'cancelled', 'pending')))
        contract_list = [(rec[0], rec[1]) for rec in self.env.cr.fetchall()]
        return contract_list

    @api.model
    def test_no_product(self, order):
        contract_list = order._get_analytic_account()
        if contract_list:
            contract_ids, contract_name = zip(*contract_list)
            action = self.env.ref('analytic.action_account_analytic_account_form').read(['name', 'type', 'view_type', 'view_mode', 'res_model', 'views', 'view', 'domain'])[0]
            action['name'] = _('Contract')
            action['domain'] = [('id', 'in', contract_ids)]
            if len(contract_ids) == 1:
                form_view = self.env.ref('analytic.view_account_analytic_account_form').id
                action['views'] = [(form_view or False, 'form'), (False, 'list')]
                action['res_id'] = contract_ids[0]
                button_string = _('Modify Contract')
            else:
                tree_view = self.env.ref('analytic.view_account_analytic_account_tree').id
                action['views'] = [(tree_view or False, 'list'), (False, 'form')]
                button_string = _('Modify Contract(s)')
            msg = _('''Contract(s) mentioned below %s in "Closed/Cancelled/To Renew" state, please renew %s before confirmation :\n%s.''') % (len(contract_list) > 1 and 'are' or 'is', len(contract_name) > 1 and 'them' or 'it', '-' + '\n- '.join(contract_name))
            raise RedirectWarning(msg, action, button_string)
        return super(SaleOrder, self).test_no_product(order)
