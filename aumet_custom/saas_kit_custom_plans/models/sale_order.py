# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

from odoo import models, fields, api
from odoo.exceptions import UserError, Warning


from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class PlanSaleOrder(models.Model):
    _inherit = 'sale.order'


    def process_contract(self):
        res = super(PlanSaleOrder, self).process_contract()
        for order in self:
            custom_plan_orderlines = list(filter(lambda line: line.is_custom_plan, order.order_line))
            for line in custom_plan_orderlines:
                saas_users = None
                default_data = line.odoo_version_id.get_default_saas_values()
                user_billing = 0
                server_id = self.env['saas.server'].sudo().search([('state','=', 'confirm'), ('total_clients', '<', 'max_clients')], limit=1)
                contract_product = line.product_id
                relative_delta = relativedelta(days=0)
                old_date = fields.Date.from_string(fields.Date.today())
                start_date = fields.Date.to_string(old_date + relative_delta)
                if line.plan_line_id:
                    saas_users = line.plan_line_id.saas_users
                    user_billing = line.plan_line_id.price_unit * line.plan_line_id.product_uom_qty
                recurring_interval_delta = relativedelta(months=(int(line.recurring_interval * line.product_uom_qty)))
                contract_rate = line.price_unit
                contract_price = contract_rate * line.product_uom_qty
                total_cost = contract_price + user_billing                
                vals = dict(
                    is_custom_plan=True,
                    odoo_version_id=line.odoo_version_id.id,
                    partner_id=order.partner_id and order.partner_id.id or False,
                    recurring_interval=line.recurring_interval,
                    recurring_rule_type=default_data['recurring_rule_type'] or 'monthly',
                    invoice_product_id=contract_product and contract_product.id or False,
                    pricelist_id=order.pricelist_id and order.pricelist_id.id or False,
                    currency_id=order.pricelist_id and order.pricelist_id.currency_id and order.pricelist_id.currency_id.id or False,
                    start_date=start_date,
                    total_cycles=line.product_uom_qty,
                    trial_period=0, # Zero For now
                    remaining_cycles=0,
                    next_invoice_date=fields.Date.to_string(fields.Date.from_string(start_date) + recurring_interval_delta),
                    contract_rate=contract_rate,
                    contract_price=contract_price,
                    per_user_pricing=default_data['user_cost'],
                    user_cost=default_data['user_cost'] * line.recurring_interval,
                    due_users_price=default_data['due_user_cost'],
                    saas_users=saas_users,
                    min_users=saas_users,
                    max_users=default_data['max_users'],
                    user_billing=user_billing,
                    total_cost=total_cost,
                    auto_create_invoice=False,
                    saas_module_ids=[(6, 0 , line.saas_module_ids.ids)],
                    on_create_email_template=self.env.ref('odoo_saas_kit.client_credentials_template').id,
                    is_multi_server=default_data['is_multi_server'],
                    server_id=server_id and server_id.id or False,
                    sale_order_line_id=line.id,
                    plan_id=None,
                    db_template=line.odoo_version_id.db_template,
                )

                try:
                    record_id = self.env['saas.contract'].create(vals)
                    _logger.info("------VIA-ORDER--Contract--Created-------%r", record_id)
                except Exception as e:
                    _logger.info("-----VIA-ORDER---Exception-While-Creating-Contract-------%r", e)
                else:
                    order.contract_id = record_id and record_id.id
                    modules = self.env['saas.module'].sudo().search([('is_published', '=', True)])
                    extra_modules = []
                    for module in modules:
                        if module in order.contract_id.saas_module_ids:
                            continue
                        extra_modules.append(module.id)
                    order.contract_id.update_saas_module_ids = [(6, 0 ,extra_modules)]
                    record_id.send_subdomain_email()
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
            if order_line.is_user_product or order_line.is_custom_plan: 
                unit_price = order_line.price_unit  
        res = super(PlanSaleOrder, self)._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs)
        if line_id and unit_price and order_line.exists() and order_line.id == res['line_id']:
            order_line.write({
                'price_unit': unit_price,
            })
            _logger.info("--------------    Price Maintained   -----------------")
        return res


    def create_custom_contract_line(self, product_id=None, odoo_version_id=None, saas_users=None, total_cost=None, users_cost=None, recurring_interval=None, module_ids=None):
        custom_contract_line_config = self._cart_update(
            product_id=product_id.id,
            add_qty=1,
        )
        if saas_users:
            user_product = self.env['product.product'].sudo().search([('is_user_pricing', '=', True)], limit=1)
            custom_contract_user_line_config = self._cart_update(
                product_id=user_product.id,
                add_qty=1,
            )

        for line in self.order_line:
            if saas_users and user_product and line.id == custom_contract_user_line_config['line_id']:
                line.saas_users = saas_users
                line.price_unit = users_cost
                line.is_user_product = True
                line.linked_line_id = custom_contract_line_config['line_id']
            elif line.id == custom_contract_line_config['line_id']:
                line.price_unit = total_cost
                line.is_custom_plan = True
                line.recurring_interval = recurring_interval
                if saas_users:
                    line.plan_line_id = custom_contract_user_line_config['line_id']
                line.odoo_version_id = odoo_version_id.id
                line.saas_module_ids = [(6 , 0, module_ids)]
        self._cr.commit()
        return True


class CustomOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_custom_plan = fields.Boolean(string="Is Custom Plan", default=False)
    recurring_interval = fields.Integer(string="Recurring Interval")
    odoo_version_id = fields.Many2one(comodel_name='saas.odoo.version', string="Odoo Version")
    saas_module_ids = fields.One2many(comodel_name='saas.module', inverse_name='order_line_id', string="Modules")
