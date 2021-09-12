# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, Warning
import logging
_logger = logging.getLogger(__name__)

BILLING_CRITERIA = [
    ('fixed', "Fixed Rate"),
    ('per_user', 'Based on the No. of users')
]


class ContractCreation(models.TransientModel):
    _name = "saas.contract.creation"
    _description = 'Contract Creation Wizard.'

    plan_id = fields.Many2one(comodel_name="saas.plan", string="Related SaaS Plan", required=False)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        required=True,
    )
    recurring_interval = fields.Integer(
        default=1,
        string='Billing Cycle',
        help="Repeat every (Days/Week/Month/Year)",
    )
    recurring_rule_type = fields.Selection(
        [('daily', 'Day(s)'),
         ('weekly', 'Week(s)'),
         ('monthly', 'Month(s)'),
         ('monthlylastday', 'Month(s) last day'),
         ('yearly', 'Year(s)'),
         ],
        default='monthly',
        string='Recurrence',
        help="Specify Interval for automatic invoice generation.", readonly=True,
    )
    # billing_criteria = fields.Selection(
    #     selection=BILLING_CRITERIA,
    #     string="Billing Criteria",
    #     required=True)
    invoice_product_id = fields.Many2one(comodel_name="product.product", required=True, string="Invoice Product")
    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string='Pricelist'
    )
    currency_id = fields.Many2one(comodel_name="res.currency")
    contract_rate = fields.Float(string="Contract Rate")
    per_user_pricing = fields.Boolean(string="Per user pricing")
    user_cost = fields.Float(string="Per User cost")
    min_users = fields.Integer(string="Min. No. of users", help="""Range for Number of users in cliet's Instance""")
    max_users = fields.Integer(string="Max. No. of users", help="""Range for Number of users in cliet's Instance""")
    saas_users = fields.Integer(string="No. of users")
    contract_price = fields.Float(string="Contract Price", help="""Pricing for Contract""")
    user_billing = fields.Float(string="User Billing", help="""User Based Billing""")
    total_cost = fields.Float(string="Total Contract Cost")
    due_users_price = fields.Float(string="Due users price", default=1.0)
    auto_create_invoice = fields.Boolean(string="Automatically create next invoice")
    start_date = fields.Date(
        string='Purchase Date',
        required=True
    )
    total_cycles = fields.Integer(
        string="Number of Cycles(Remaining/Total)", default=1)
    trial_period = fields.Integer(
        string="Complimentary(Free) days", default=0)

    @api.model
    def get_date_delta(self, interval):
        return relativedelta(months=interval)


    @api.onchange('user_cost', 'contract_rate', 'saas_users', 'total_cycles')
    def calculate_total_cost(self):
        for obj in self:
            obj.contract_price = obj.contract_rate * obj.total_cycles    
            if obj.per_user_pricing and obj.saas_users:
                if obj.saas_users < obj.min_users:
                    raise Warning("No. of users can't be less than %r"%obj.min_users)
                if obj.max_users != -1 and obj.saas_users > obj.max_users:
                    raise Warning("No. of users can't be greater than %r"%obj.max_users)
                obj.user_billing = obj.saas_users * obj.user_cost * obj.total_cycles
            obj.total_cost = obj.contract_price + obj.user_billing
            _logger.info("+++11++++OBJ>TOTALCOST+++++++%s",obj.total_cost)

    @api.model
    def create(self, vals):
        if self.user_billing:
            vals['user_billing'] = self.saas_users * self.user_cost * self.total_cycles
        if self.contract_price:
            vals['contract_price'] = self.contract_rate * self.total_cycles
        if self.total_cost:
            vals['total_cost'] = vals['contract_price'] + vals['user_billing']
        res = super(ContractCreation, self).create(vals)
        return res
    
    def write(self, vals):
        for obj in self:
            if not obj.user_billing:
                vals['user_billing'] = obj.saas_users * obj.user_cost * obj.total_cycles
            if not obj.contract_price:
                vals['contract_price'] = obj.contract_rate * obj.total_cycles
            if not obj.total_cost:
                vals['total_cost'] = vals['contract_price'] + vals['user_billing']
            res = super(ContractCreation, self).write(vals)
            return res

    @api.onchange('trial_period')
    def trial_period_change(self):
        relative_delta = relativedelta(days=self.trial_period)
        old_date = fields.Date.from_string(fields.Date.today())
        self.start_date = fields.Date.to_string(old_date + relative_delta)

    @api.onchange('plan_id')
    def plan_id_change(self):
        self.recurring_interval = self.plan_id.recurring_interval
        self.recurring_rule_type = self.plan_id.recurring_rule_type
        self.per_user_pricing = self.plan_id.per_user_pricing
        self.user_cost = self.plan_id.user_cost
        self.min_users = self.plan_id.min_users
        self.max_users = self.plan_id.max_users
        self.saas_users = self.plan_id.min_users
        self.trial_period = self.plan_id.trial_period
        self.contract_price = self.contract_rate * self.total_cycles
        self.user_billing = self.saas_users * self.user_cost * self.total_cycles 
        self.total_cost = self.contract_price + self.user_billing
        self.due_users_price = self.plan_id.due_users_price
        relative_delta = relativedelta(days=self.trial_period)
        old_date = fields.Date.from_string(fields.Date.today())
        self.start_date = fields.Date.to_string(old_date + relative_delta)
        _logger.info("=============%s",self.total_cost)
        _logger.info("=============%s",self.contract_price)

    @api.onchange('partner_id')
    def partner_id_change(self):
        self.pricelist_id = self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False
        self.currency_id = self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.currency_id.id or False

    @api.onchange('invoice_product_id')
    def invoice_product_id_change(self):
        self.contract_rate = self.invoice_product_id and self.invoice_product_id.lst_price or False
        return {
            'domain': {'invoice_product_id' : [('saas_plan_id', '=', self.plan_id.id)]}
        }
        
    def action_create_contract(self):
        for obj in self:
            if obj.per_user_pricing:
                obj.user_billing = obj.saas_users * obj.user_cost * obj.total_cycles
                if obj.saas_users < obj.min_users and obj.max_users != -1 and obj.saas_users > obj.max_users:
                    raise Warning("Please select number of users in limit {} - {}".format(obj.min_users, obj.max_users))
            obj.total_cost = obj.contract_price + obj.user_billing
            server_id = None
            if not obj.plan_id.is_multi_server:
                server_id = obj.plan_id.server_id.id
            vals = dict(
                partner_id=obj.partner_id and obj.partner_id.id or False,
                recurring_interval=obj.recurring_interval,
                recurring_rule_type=obj.recurring_rule_type,
                invoice_product_id=obj.invoice_product_id and obj.invoice_product_id.id or False,
                pricelist_id=obj.partner_id.property_product_pricelist and obj.partner_id.property_product_pricelist.id or False,
                currency_id=obj.partner_id.property_product_pricelist and obj.partner_id.property_product_pricelist.currency_id and obj.partner_id.property_product_pricelist.currency_id.id or False,
                start_date=obj.start_date,
                total_cycles=obj.total_cycles,
                trial_period=obj.trial_period,
                remaining_cycles=obj.total_cycles,
                next_invoice_date=obj.start_date,
                contract_rate=obj.contract_rate,
                contract_price=obj.contract_price,
                due_users_price=obj.due_users_price,
                total_cost=obj.total_cost,
                per_user_pricing=obj.per_user_pricing,
                user_billing=obj.user_billing,
                user_cost=obj.user_cost,
                saas_users=obj.saas_users,
                min_users=obj.min_users,
                max_users=obj.max_users,
                auto_create_invoice=obj.auto_create_invoice,
                saas_module_ids=[(6, 0 , obj.plan_id.saas_module_ids.ids)],
                is_multi_server=obj.plan_id.is_multi_server,                
                server_id=server_id,
                db_template=obj.plan_id.db_template,
                plan_id=obj.plan_id.id,
                from_backend=True,
            )

            try:
                _logger.info("!!!!!!!===!!!!!!!!%s",obj.total_cost)
                record_id = self.env['saas.contract'].create(vals)
                _logger.info("--------Contract--Created-------%r", record_id)
            except Exception as e:
                _logger.info("--------Exception-While-Creating-Contract-------%r", e)
            else:
                imd = self.env['ir.model.data']
                action = imd.xmlid_to_object('odoo_saas_kit.saas_contract_action')
                list_view_id = imd.xmlid_to_res_id('odoo_saas_kit.saas_contract_tree_view')
                form_view_id = imd.xmlid_to_res_id('odoo_saas_kit.saas_contract_form_view')

                return {
                    'name': action.name,
                    'res_id': record_id.id,
                    'type': action.type,
                    'views': [[form_view_id, 'form'], [list_view_id, 'tree'], ],
                    'target': action.target,
                    'context': action.context,
                    'res_model': action.res_model,
                }
