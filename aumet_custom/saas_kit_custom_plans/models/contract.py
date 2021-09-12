# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

from odoo import models, api, fields, _
from odoo.addons.auth_signup.models.res_partner import random_token as generate_token
from odoo.exceptions import UserError, Warning
from odoo.addons.odoo_saas_kit.models.lib import query


from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class ContractCustomPlan(models.Model):
    _inherit = 'saas.contract'

    is_custom_plan = fields.Boolean(string="Is Custom Plan", default=False)
    odoo_version_id = fields.Many2one(comodel_name="saas.odoo.version")
    update_saas_module_ids = fields.One2many(comodel_name="saas.module",inverse_name="contract_id", string="Related Modules")
    sync_required = fields.Boolean(string="Is Sync Required", default=False)
    expiry_warnings = fields.Integer(string="Warning Remaining", default=3)

    def send_credential_email(self):
        if self.is_custom_plan:
            self.ensure_one()
            if not self.saas_client.client_url:
                raise UserError("SaaS Instance Not Found! Please create it from the associated client record for sharing the credentials.")
            template = self.on_create_email_template
            compose_form = self.env.ref('mail.email_compose_message_wizard_form')

            try:
                token = generate_token()
                self.sudo().set_user_data(token=token)
                self._cr.commit()
                reset_pwd_url = "{}/web/signup?token={}&db={}".format(self.saas_client.client_url, token, self.saas_client.database_name)
                self.saas_client.invitation_url = reset_pwd_url
            except Exception as e:
                _logger.info("--------EXCEPTION-WHILE-UPDATING-DATA-AND-SENDING-INVITE-------%r----", e)

            ctx = dict(
                default_model='saas.client',
                default_res_id=self.saas_client.id,
                default_use_template=bool(template),
                default_template_id=template and template.id or False,
                default_composition_mode='comment',
            )
            return {
                'name': _('Compose Email'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }
        else:
            res = super(ContractCustomPlan, self).send_credential_email()
            return res

    def generate_invoice(self, first_invoice=None):
        for obj in self:
            if obj.is_custom_plan:
                if obj.remaining_cycles:
                    user_count = None
                    data = {}
                    if obj.per_user_pricing:
                        if obj.saas_client and obj.saas_client.database_name:
                            _, db_server = obj.server_id.get_server_details()
                            response = query.get_user_count(obj.saas_client.database_name, db_server=db_server)
                            if response:
                                user_count = response[0][0]
                                if obj.max_users != -1 and user_count > obj.max_users:
                                    raise UserError("Client have crossed the maximum user limit.")
                                user_count = max(user_count, obj.saas_users)
                                if user_count > obj.previous_cycle_user:
                                    arrer_response = query.get_arrear_users(
                                        obj.saas_client.database_name,
                                        db_server=db_server,
                                        limit = user_count - obj.previous_cycle_user,
                                    )
                                    if not arrer_response:
                                        raise UserError("Couldn't fetch arrer users! Please try again.")
                                    data = obj.calculate_arrear_price(arrer_response)

                        if not user_count:
                            raise UserError("Couldn't fetch user count! Please try again later.")                    
                    try:
                        price = None                    
                        if first_invoice == True:
                            if obj.per_user_pricing:
                                obj.update_billing_history(first=True)
                                obj.previous_cycle_user = max(obj.min_users, obj.saas_users)
                            price = obj.total_cost
                        else:
                            if obj.per_user_pricing:
                                res = obj.update_billing_history(arrear_users=data.get('arrear_users', 0), arrear_price=data.get('total_price', 0))
                                price = res.get('total_cost', 0) + obj.contract_rate
                                obj.previous_cycle_user = res.get('new_users', obj.previous_cycle_user)
                            else:
                                price = obj.contract_rate

                        invoice_vals = {
                            'move_type': 'out_invoice',
                            'partner_id': obj.partner_id and obj.partner_id.id or False,
                            'currency_id': obj.pricelist_id and obj.pricelist_id.currency_id.id or False,
                            'contract_id': obj.id,
                            'invoice_line_ids': [(0, 0, {
                                'price_unit': price,
                                'quantity': 1.0,
                                'product_id': obj.invoice_product_id.id,
                            })],
                        }
                        invoice = self.env['account.move'].sudo().create(invoice_vals)
                        invoice.action_post()
                        obj.send_invoice_mail(invoice)
                        _logger.info("--------Invoice--Created-------%r", invoice)
                    except Exception as e:
                        _logger.info("--------Exception-While-Creating-Invoice-------%r", e)
                        raise UserError("Exception While Creating Invoice: {}".format(e))
                    else:
                        old_date = obj.next_invoice_date and fields.Date.from_string(obj.next_invoice_date) or fields.Date.from_string(fields.Date.today())
                        if first_invoice == True:
                            relative_delta = relativedelta(months=(self.recurring_interval*self.total_cycles))
                            obj.remaining_cycles = 0
                        else:    
                            relative_delta = relativedelta(months=self.recurring_interval)
                            obj.remaining_cycles -= 1
                        next_date = fields.Date.to_string(old_date + relative_delta)
                        obj.next_invoice_date = next_date
                else:
                    raise UserError("This Contract Has Expired!")
            else:
                res = super(ContractCustomPlan, self).generate_invoice(first_invoice=first_invoice)
                return res

    def set_user_data(self, token=False):
        for obj in self:
            if obj.is_custom_plan:
                data = dict()
                partner_id = obj.partner_id
                user_id = self.env['res.users'].search([('partner_id', '=', obj.partner_id.id)], limit=1)
                if not user_id and not partner_id.email:
                    raise UserError("Please Specify The Email Of The Selected Partner!")
                host_server, db_server = obj.server_id.get_server_details()
                data['database'] = obj.saas_client and obj.saas_client.database_name or False
                data['user_id'] = obj.odoo_version_id.template_user_id and int(obj.plan_id.template_user_id)
                data['user_data'] = dict(
                    name = user_id and user_id.name or partner_id.name or '',
                    login = user_id and user_id.login or partner_id.email or '',
                )

                data['partner_data'] = dict(
                    name = partner_id.name or '',
                    street = partner_id.street or '',
                    street2 = partner_id.street2 or '',
                    city = partner_id.city or '',
                    state_id = partner_id.state_id and partner_id.state_id.id or False,
                    zip = partner_id.zip or '',
                    country_id = partner_id.country_id and partner_id.country_id.id or False,
                    phone = partner_id.phone or '',
                    mobile = partner_id.mobile or '',
                    email = partner_id.email or '',
                    website = partner_id.website or '',
                    signup_token=token or '',
                    signup_type="signup",
                )
                data['host_server'] = host_server
                data['db_server'] = db_server
                _logger.info("------DATAAA-------%r", data)
                response = query.update_user(**data)
                if response:
                    _logger.info("------1-------")
                    obj.user_data_updated = True
                    obj.user_data_error = False
                    self._cr.commit()
                    obj.message_post(
                        body="User Data Update Successfully",
                        subject="User Data Update Response",
                    )
                else:
                    _logger.info("------2-------")
                    obj.user_data_updated = False
                    obj.user_data_error = True
                    self._cr.commit()
                    raise UserError("Unable To Write User Data")
                if obj.per_user_pricing:
                    vals = dict()
                    vals['database'] = obj.saas_client and obj.saas_client.database_name or False
                    vals['min_users'] = obj.min_users
                    vals['max_users'] = obj.max_users
                    try:
                        response = None
                        response = query.set_user_limt(vals, db_server=db_server, is_count=True)
                    except Exception as e:
                        _logger.info("-------Exception while updation limit %r -------"%e)    
                    if response:
                        obj.saas_client.restart_client()
                        _logger.info("---------   Updated User limits --------")
                    else:
                        _logger.info("---------   Exception While updating user limits  ------")
            else:
                res = super(ContractCustomPlan, self).set_user_data(token=token)
                return res


    def update_user_data(self):
        """
        Called from The button "Set UserData in the Contract Form"
        """
        for obj in self:
            # if not obj.plan_id:  # Need to update this
                # raise UserError("Database Template User ID Not Set!")
            token = generate_token()
            try:
                if obj.from_backend:
                    obj.generate_invoice(first_invoice=True)
                elif obj.per_user_pricing:
                    obj.update_billing_history(first=True)
                    obj.previous_cycle_user = max(obj.min_users, obj.saas_users)
            except Exception as e:
                raise UserError("Unable To Write User Data %r"%e)
            obj.sudo().set_user_data(token=token)
            obj._cr.commit()
            reset_pwd_url = "{}/web/signup?token={}&db={}".format(obj.saas_client.client_url, token, obj.saas_client.database_name)
            obj.saas_client.invitation_url = reset_pwd_url


    def install_remaining_modules(self):
        for obj in self:
            obj.saas_client.install_modules()

    def add_apps(self, apps, contract_id):
        modules = self.env['saas.module'].sudo().search([('technical_name' , 'in', apps)])
        contract_id = self.env['saas.contract'].sudo().browse([contract_id])
        config = contract_id.odoo_version_id.get_default_saas_values()
        multiplier = 1
        if config['costing_nature'] == 'per_user':
            multiplier = contract_id.saas_users
        else:
            multiplier = contract_id.recurring_interval
        modules_list = []
        for x in contract_id.saas_module_ids:
            modules_list.append(x.id)
        extra_module_price = 0
        for module in modules:
            if not contract_id.sync_required and contract_id.saas_client:
                contract_id.sync_required = True
            modules_list.append(module.id)
            extra_module_price += module.price
        
        extra_module_price *= multiplier
        contract_id.saas_module_ids = [(6 , 0, modules_list)]
        contract_id.contract_rate += extra_module_price
        contract_id.contract_price += extra_module_price
        contract_id.total_cost += extra_module_price
        extra_modules = self.env['saas.module'].sudo().search([('is_published', '=', True), ('id', 'not in', modules_list)])
        extra_modules = [x.id for x in extra_modules]
        contract_id.update_saas_module_ids = [(6, 0 ,extra_modules)]
        _logger.info('-------------- %r -------------'%contract_id.token)
        contract_id.sync_modules()
        return contract_id.token

    def get_module(self, contract_id):
        contract_id = self.env['saas.contract'].sudo().browse([contract_id])
        modules = self.env['saas.module'].sudo().search([('is_published', '=', True)])
        extra_modules = []
        for module in modules:
            if module in contract_id.saas_module_ids:
                continue
            extra_modules.append(module.id)
        _logger.info("----------- %r ----------"%extra_modules)        
        contract_id.update_saas_module_ids = [(6, 0 ,extra_modules)]
        _logger.info("----------- %r ----------"%contract_id.update_saas_module_ids)
        contract_id._cr.commit()
        return True

    def sync_modules(self):
        if not self.saas_client:
            raise UserError("Not Associated Clients ...")
        modules_ids = [x.module_id.id for x in self.saas_client.saas_module_ids]
        for module in self.saas_module_ids:
            if module.id not in modules_ids:
                self.saas_client.missed_modules = True
                self.env['saas.module.status'].create(dict(
                    module_id=module.id,
                    client_id=self.saas_client.id,
                ))
        self.sync_required = False

    @api.model
    def check_reminder_contracts(self):
        number_of_mails = 3
        IrDefault = self.env['ir.default'].sudo()
        is_reminder_period = IrDefault.get('res.config.settings', 'is_reminder_period')
        if not is_reminder_period:
            return
        reminder_period = IrDefault.get('res.config.settings', 'reminder_period')
        if not reminder_period:
            return    
        starting_date = fields.Date.today() + relativedelta(days=reminder_period)
        contracts = self.env['saas.contract'].sudo().search([('expiry_warnings', '>', 0), ('next_invoice_date', '<=', starting_date), ('state', 'in', ['confirm', 'hold'])])
        for contract in contracts:
            gap_factor = reminder_period / number_of_mails
            next_period = reminder_period - ((number_of_mails - contract.expiry_warnings)*gap_factor)
            if next_period <= 0 and contract.expiry_warnings != 0:
                contract.send_expiry_warning_mail()
            else:
                next_date = fields.Date.today() + relativedelta(days=next_period)
                if next_date >= contract.next_invoice_date and contract.expiry_warnings != 0:
                    contract.send_expiry_warning_mail()

    def send_expiry_warning_mail(self):
        for obj in self:
            template = self.env.ref('saas_kit_custom_plans.contract_expiry_warning_template')
            mail_id = template.send_mail(obj.id)
            current_mail = self.env['mail.mail'].browse(mail_id)
            res = current_mail.send()
            mail_number = "First" if obj.expiry_warnings == 3 else "Second" if obj.expiry_warnings == 2 else "Third"
            obj.expiry_warnings -= 1
            obj.message_post(body=mail_number+" Expiry mail sent to Custom", subject="Waring Mail")
            if obj.expiry_warnings == 0:
                obj.check_contract_expiry()

