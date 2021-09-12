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
from odoo.models import NewId
from odoo.modules.module import get_module_resource
from odoo.addons.odoo_saas_kit.models.lib import saas
from odoo.addons.odoo_saas_kit.models.lib import query

import logging


_logger = logging.getLogger(__name__)

STATE = [
    ('open', 'Open'),
    ('confirm', 'Confirm')
]

class SaasOdooVersion(models.Model):
    _name = 'saas.odoo.version'


    name = fields.Char(string="Version Name")
    code = fields.Char(string="Version Code")
    state = fields.Selection(selection=STATE, string="State", default="open")
    is_template_created = fields.Boolean(string="Template Created", default=False)
    db_template = fields.Char(string="DB Template", compute="_compute_db_template_name", store=True)
    product_id = fields.Many2one(comodel_name="product.product", string="Template Product", domain="[('is_saas_module', '=', True)]")
    use_specific_user_template = fields.Boolean(
        string="Use Specific User Template", help="""Select if you want to provide some specific permissions to your user for acessing its odoo instance which is going to be created by this plan.""")
    template_user_id = fields.Char(string="Database Template User ID", help="""Enter the user_id of User which you have created in the DB Template with some specific permissions or whose permission you want to grant to the user of odoo instances which is going to be created by this plan.""")

    def create_db_template(self):
        for obj in self:
            server_id = self.env['saas.server'].sudo().search([('state', '=', 'confirm')], limit=1)
            if not server_id:
                raise UserError("Please confirm Atleast One server to Continue")
            if not obj.db_template:
                raise UserError("Please select the DB template name first.")
            config_path = get_module_resource('odoo_saas_kit')
            db_template_name = "template_{}".format(obj.db_template)
            modules = ['wk_saas_tool']
            host_server, db_server = server_id.get_server_details()
            try:
                response = saas.create_db_template(
                    db_template=db_template_name,
                    modules=modules,
                    config_path=config_path,
                    host_server=host_server,
                    db_server=db_server,
                    version=obj.code)
            except Exception as e:
                raise UserError(e)
            else:
                if response:
                    if response.get('status', False):
                        obj.db_template = db_template_name
                        obj.state = 'confirm'
                    else:
                        msg = response.get('msg', False)
                        if msg:
                            raise UserError(msg)
                        else:
                            raise UserError("Unknown Error. Please try again later with some different Template Name")
                else:
                    raise UserError("No Response. Please try again later with some different Template Name")


    def login_to_template(self):
        for obj in self:
            server_id = self.env['saas.server'].sudo().search([('host_server', '=', 'self'), ('state', '=', 'confirm')], limit=1)
            if not server_id:
                raise UserError("Please configure atleast one self server to continue..")
            host_server, db_server = server_id.get_server_details()
            response = query.get_credentials(
                obj.db_template,
                host_server=host_server,
                db_server=db_server)
            if response:
                login = response[0][0]
                password = response[0][1]
                login_url = "http://db{}_templates.{}/saas/login?db={}&login={}&passwd={}".format(obj.code.split('.')[0],server_id.server_domain,obj.db_template, login, password)
                _logger.info("$$$$$$$$$$$$$$%r", login_url)
                return {
                    'type': 'ir.actions.act_url',
                    'url': login_url,
                    'target': 'new',
                }
            else:
                raise UserError("Unknown Error!")
            


    @api.depends('name')
    def _compute_db_template_name(self):
        for obj in self:
            if obj.name and type(obj.id) != NewId and not obj.db_template:
                template_name = obj.name.lower().replace(" ", "_")
                obj.db_template = "{}_tid_{}".format(template_name, obj.id)

    def get_default_saas_values(self):
        data = dict()
        IrDefault = self.env['ir.default'].sudo()
        data['recurring_rule_type'] = IrDefault.get('res.config.settings', 'recurring_rule_type')
        data['is_odoo_version'] = IrDefault.get('res.config.settings', 'is_odoo_version')
        data['is_users'] = IrDefault.get('res.config.settings', 'is_users')
        data['apps_view'] = IrDefault.get('res.config.settings', 'apps_view')
        data['is_free_users'] = IrDefault.get('res.config.settings', 'is_free_users')
        data['free_users'] = int(IrDefault.get('res.config.settings', 'free_users') or 0)
        data['due_user_cost'] = int(IrDefault.get('res.config.settings', 'due_user_cost') or 0)
        data['addons_path'] = IrDefault.get('res.config.settings', 'addons_path')
        data['max_users'] = IrDefault.get('res.config.settings', 'max_users')
        data['is_multi_server'] = IrDefault.get('res.config.settings', 'is_multi_server')
        data['user_cost'] = int(IrDefault.get('res.config.settings', 'user_cost') or 0)
        data['costing_nature'] = IrDefault.get('res.config.settings', 'costing_nature')
        
        return data
