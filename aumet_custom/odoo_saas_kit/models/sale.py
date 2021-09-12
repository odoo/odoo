# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

from dateutil.relativedelta import relativedelta
from odoo import fields, models, api
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    contract_id = fields.Many2one(comodel_name="saas.contract", string="SaaS Contract")

    @api.model
    def get_date_delta(self, interval):
        return relativedelta(months=interval)

    def action_view_contract(self):
        action = self.env.ref('odoo_saas_kit.saas_contract_action').read()[0]

        contract = self.env['saas.contract'].search([('sale_order_id', '=', self.id)])
        action['domain'] = [('id', 'in', contract.ids)]
        return action

    def process_contract(self):
        for order in self:
            all_contract_lines = list(filter(lambda line: line.product_id.saas_plan_id, order.order_line))
            for contract_line in all_contract_lines:
                user_billing = 0
                saas_users = 0
                if contract_line.plan_line_id:
                    saas_users = contract_line.plan_line_id.saas_users
                    user_billing = contract_line.plan_line_id.price_unit * contract_line.plan_line_id.product_uom_qty
                contract_product = contract_line.product_id
                contract_rate = contract_line.price_unit
                contract_price = contract_rate * contract_line.product_uom_qty
                total_cost = contract_price + user_billing
                relative_delta = relativedelta(days=contract_product.saas_plan_id.trial_period)
                old_date = fields.Date.from_string(fields.Date.today())
                start_date = fields.Date.to_string(old_date + relative_delta)

                recurring_interval_delta = relativedelta(months=(int(contract_line.product_id.recurring_interval * contract_line.product_uom_qty)))
                server_id = None
                if not contract_product.saas_plan_id.is_multi_server:
                    server_id = contract_product.saas_plan_id.server_id.id
                vals = dict(
                    partner_id=order.partner_id and order.partner_id.id or False,
                    recurring_interval=contract_line.product_id.recurring_interval,
                    recurring_rule_type=contract_product.saas_plan_id.recurring_rule_type,
                    invoice_product_id=contract_product and contract_product.id or False,
                    pricelist_id=order.pricelist_id and order.pricelist_id.id or False,
                    currency_id=order.pricelist_id and order.pricelist_id.currency_id and order.pricelist_id.currency_id.id or False,
                    start_date=start_date,
                    total_cycles=contract_line.product_uom_qty,
                    trial_period=contract_product.saas_plan_id.trial_period,
                    remaining_cycles=0,
                    next_invoice_date=fields.Date.to_string(fields.Date.from_string(start_date) + recurring_interval_delta),
                    contract_rate=contract_rate,
                    contract_price=contract_price,
                    per_user_pricing=contract_product.saas_plan_id.per_user_pricing,
                    user_cost=contract_product.saas_plan_id.user_cost * contract_line.product_id.recurring_interval,
                    due_users_price=contract_product.saas_plan_id.due_users_price,
                    saas_users=saas_users,
                    min_users=contract_product.saas_plan_id.min_users,
                    max_users=contract_product.saas_plan_id.max_users,
                    user_billing=user_billing,
                    total_cost=total_cost,
                    auto_create_invoice=False,
                    saas_module_ids=[(6, 0 , contract_product.saas_plan_id.saas_module_ids.ids)],
                    on_create_email_template=self.env.ref('odoo_saas_kit.client_credentials_template').id,
                    is_multi_server=contract_product.saas_plan_id.is_multi_server,
                    server_id=server_id,
                    sale_order_line_id=contract_line.id,
                    plan_id=contract_product.saas_plan_id.id,
                    db_template=contract_product.saas_plan_id.db_template,
                )
                try:
                    record_id = self.env['saas.contract'].create(vals)
                    _logger.info("------VIA-ORDER--Contract--Created-------%r", record_id)
                except Exception as e:
                    _logger.info("-----VIA-ORDER---Exception-While-Creating-Contract-------%r", e)
                else:
                    order.contract_id = record_id and record_id.id
                    record_id.send_subdomain_email()
    
    
    def _action_confirm(self):
        res = super(SaleOrder, self)._action_confirm()
        self.process_contract()
        return res

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """
        Override this method to maintain the custom price of user product for website
        """
        unit_price = None
        if product_id and line_id:
            order_line = self.env['sale.order.line'].sudo().browse(line_id)
            if order_line.plan_line_id:
                self._cart_update(product_id=order_line.plan_line_id.product_id.id, line_id=order_line.plan_line_id.id, add_qty=add_qty, set_qty=set_qty, **kwargs)
            if order_line.is_user_product:
                unit_price = order_line.price_unit  
        res = super(SaleOrder, self)._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs)
        if line_id and unit_price and order_line.exists() and order_line.id == res['line_id']:
            order_line.write({
                'price_unit': unit_price,
            })
            _logger.info("--------------    Price Maintained   -----------------")
        return res

class SaasSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_user_product = fields.Boolean(string="Is User Product", default=False)
    plan_line_id = fields.Many2one(comodel_name='sale.order.line', string="User Line")
    saas_users = fields.Integer(string="Saas Users")