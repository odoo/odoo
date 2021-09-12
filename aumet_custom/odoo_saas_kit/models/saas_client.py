# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################

from urllib.parse import urlparse
from odoo import fields, models, api
from odoo.exceptions import UserError, Warning, ValidationError
from odoo.modules.module import get_module_resource
from odoo.models import NewId
import string
import random
import logging
import base64
from . lib import saas
from . lib import query
from . lib import containers
from . lib import client

_logger = logging.getLogger(__name__)

MODULE_STATUS = [
    ('installed', "Installed"),
    ('uninstalled', "Not Installed")]

CLIENT_STATE = [
    ('draft', "Draft"),
    ('started', "Started"),
    ('stopped', "Stopped"),
    ('inactive', 'Inactive'),
    ('cancel', 'Cancel'),]

def _code_generator(size=5, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


class SaasClient(models.Model):
    _name = 'saas.client'
    _order = 'id desc'
    _description = 'Class for managing SaaS Instances(Clients)'

    @api.depends('data_directory_path')
    def _compute_addons_path(self):
        for obj in self:
            if obj.data_directory_path and type(obj.id) != NewId:
                obj.addons_path = "{}/addons/14.0".format(
                    obj.data_directory_path)
            else:
                obj.addons_path = ""

    name = fields.Char(string="Name")
    client_url = fields.Char(string="URL")
    database_name = fields.Char(string="Database Name")
    saas_contract_id = fields.Many2one(comodel_name="saas.contract", string="SaaS Contract")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Customer")
    containter_port = fields.Char(string="Port")
    containter_path = fields.Char(string="Path")
    container_name = fields.Char(string="Instance Name")
    container_id = fields.Char(string="Instance ID")
    data_directory_path = fields.Char(string="Data Directory Path")
    addons_path = fields.Char(compute='_compute_addons_path', string="Extra Addons Path")
    saas_module_ids = fields.One2many(comodel_name="saas.module.status", inverse_name="client_id", string="Related Modules")
    server_id = fields.Many2one(comodel_name="saas.server", string="SaaS Server")
    invitation_url = fields.Char("Invitation URL")
    state = fields.Selection(selection=CLIENT_STATE, default="draft", string="State")
    is_drop_db = fields.Boolean(string="Drop Db", default=False)
    is_drop_container = fields.Boolean(string="Drop Container", default=False)

    _sql_constraints = [
        ('database_name_uniq', 'unique(database_name)', 'Database Name Must Be Unique !!!'),
    ]

    @api.model
    def create_docker_instance(self, domain_name=None):
        modules = [module.technical_name for module in self.saas_module_ids]
        host_server, db_server = self.saas_contract_id.server_id.get_server_details()
        response = None
        self.database_name = domain_name.replace("https://", "").replace("http://", "")
        config_path = get_module_resource('odoo_saas_kit')
        response = saas.main(dict(
            db_template = self.saas_contract_id.db_template,
            db_name=self.database_name,
            modules=modules,
            config_path = config_path,
            host_domain=domain_name,
            host_server=host_server,
            db_server=db_server)
        )
        return response

    @api.model
    def create_client_instance(self, domain_name=None):
        server_id = self.server_id
        if server_id.server_type == 'containerized':
            return self.create_docker_instance(domain_name)
        return False

    def fetch_client_url(self, domain_name=None):
        for obj in self:
            if type(domain_name) != str:
                if obj.saas_contract_id.use_separate_domain:
                    domain_name = obj.saas_contract_id.domain_name
                else:
                    domain_name = "{}.{}".format(obj.saas_contract_id.domain_name, obj.saas_contract_id.saas_domain_url)

            response = None
            try:
                response = obj.create_client_instance(domain_name)
            except Exception as e:
                raise UserError("Unable To Create Client\nERROR: {}".format(e))
            if response:
                obj.client_url = response.get("url", False)
                obj.containter_port = response.get("port", False)
                obj.containter_path = response.get("path", False)
                obj.container_name = response.get("name", False)
                obj.container_id = response.get("container_id", False)
                obj.state = "started"

                obj.data_directory_path = response.get("extra-addons", False)
                if response.get("modules_installation", False):
                    for module_status_id in obj.saas_module_ids:
                        module_status_id.status = 'installed'
                else:
                    for module_status_id in obj.saas_module_ids:
                        if module_status_id.technical_name not in response.get("modules_missed", []):
                            module_status_id.status = 'installed'
            else:
                raise UserError("Couldn't create the instance with the selected domain name. Please use some other domain name.")

    def login_to_client_instance(self):
        for obj in self:
            host_server, db_server = obj.saas_contract_id.server_id.get_server_details()
            response = query.get_credentials(
                obj.database_name,
                host_server=host_server,
                db_server=db_server)
            if response:
                login = response[0][0]
                password = response[0][1]
                login_url = "{}/saas/login?db={}&login={}&passwd={}".format(obj.client_url, obj.database_name, login, password)
                return {
                    'type': 'ir.actions.act_url',
                    'url': login_url,
                    'target': 'new',
                }
            else:
                raise UserError("Unknown Error!")

    def stop_client(self):
        for obj in self:
            host_server, db_server = obj.saas_contract_id.server_id.get_server_details()
            response_flag = containers.action(operation="stop",container_id=obj.container_id,host_server = host_server,db_server = db_server)
            if response_flag:
                obj.state = "stopped"
            else:
                raise UserError("Operation Failed! Unknown Error!")

    def start_client(self):
        for obj in self:
            if obj.saas_contract_id.state == 'hold':
                raise Warning("Related Contract is on Hold Please resume the contract first !")
            host_server, db_server = obj.saas_contract_id.server_id.get_server_details()
            response_flag = containers.action(operation="start",container_id=obj.container_id,host_server=host_server,db_server= db_server )
            if response_flag:
                obj.state = "started"
            else:
                raise UserError("Operation Failed! Unknown Error!")

    def restart_client(self):
        for obj in self:
            host_server, db_server = obj.saas_contract_id.server_id.get_server_details()
            response_flag = containers.action(operation="restart",container_id=obj.container_id,host_server=host_server,db_server= db_server )
            if response_flag:
                obj.state = "started"
            else:
                raise UserError("Operation Failed! Unknown Error!")

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('saas.client')
        return super(SaasClient, self).create(vals)

    def inactive_client(self):
        for obj in self:
            if obj.state in ['stopped', 'draft']:
                obj.state = 'inactive'
            else:
                raise UserError("Can't Inactive a Running Client") 

    def unlink(self):
       for obj in self:
           raise Warning("Can't Delete Instances")
    
    def drop_db(self):
        for obj in self:
            if obj.state == "inactive":
                host_server, db_server = obj.saas_contract_id.server_id.get_server_details()
                _logger.info("HOST SERER %r   DB SERVER  %r"%(host_server,db_server))
                response = client.main(obj.database_name, obj.containter_port, host_server, get_module_resource('odoo_saas_kit'), from_drop_db=True)
                if not response['db_drop']:
                    raise UserError("ERROR: Couldn't Drop Client Database. Please Try Again Later.\n\nOperation\tStatus\n\nDrop database: \t{}\n".format(response['db_drop']))
                else:
                    obj.is_drop_db = True
                    if obj.is_drop_container:
                        obj.saas_contract_id.state = 'cancel'
                        obj.state = 'cancel'

    def drop_container(self):
        for obj in self:
            if obj.state == "inactive":
                host_server, db_server = obj.saas_contract_id.server_id.get_server_details()
                _logger.info("HOST SERER %r   DB SERVER  %r"%(host_server,db_server))
                response = client.main(obj.database_name, obj.containter_port, host_server, get_module_resource('odoo_saas_kit'), container_id=obj.container_id, db_server=db_server, from_drop_container=True)
                if not response['drop_container'] or not response['delete_nginx_vhost'] or not response['delete_data_dir']:
                    raise UserError("ERROR: Couldn't Drop Client Container. Please Try Again Later.\n\nOperation\tStatus\n\nDelete Domain Mapping: \t{}\nDelete Data Directory: \t{}".format(response['drop_container'], response['delete_nginx_vhost']))
                else:
                    obj.is_drop_container = True
                    if obj.is_drop_db:
                        obj.saas_contract_id.state = 'cancel'
                        obj.state = 'cancel'

    def cancel_client(self):
        for obj in self:
            if obj.state == 'inactive':
                if not obj.is_drop_db:
                    raise UserError("Please Drop DB to cancel the client.")
                if not obj.is_drop_container:
                    raise UserError("Please Drop Container to cancel the client.")
                else:
                    obj.state = 'cancel'
            elif obj.state == 'draft':
                obj.state='cancel'                
            else:
                raise UserError('Please Inactive the Client first to cancel !')
