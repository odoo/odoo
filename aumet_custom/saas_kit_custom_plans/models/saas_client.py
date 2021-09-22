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
from odoo.modules.module import get_module_resource
from odoo.addons.odoo_saas_kit.models.lib import query
from odoo.addons.odoo_saas_kit.models.lib import saas
from odoo.addons.odoo_saas_kit.models.lib import client


import logging

_logger = logging.getLogger(__name__)

from . lib import saas_install

MODULE_STATUS = [('installed', "Installed"), 
                ('to_be_installed', "To Be Installed")]


class CustomSaasClient(models.Model):
    _inherit = 'saas.client'

    missed_modules = fields.Boolean(string="Missed Modules", default=True)

    
    def install_modules(self):
        for obj in self:
            modules = [module.technical_name  for module in obj.saas_module_ids if module.status == 'to_be_installed']
            if not modules:
                obj.missed_modules = False
                return
            config_path = get_module_resource('odoo_saas_kit')
            host_server, db_server = obj.saas_contract_id.server_id.get_server_details()
            if obj.saas_contract_id.use_separate_domain:
                domain_name = obj.saas_contract_id.domain_name
            else:
                domain_name = "{}.{}".format(obj.saas_contract_id.domain_name, obj.saas_contract_id.saas_domain_url)
                
            try:
                cred_response = query.get_credentials(
                    obj.database_name,
                    host_server=host_server,
                    db_server=db_server)
                _logger.info("+++++++== %r =========="%cred_response)
                if cred_response:
                    login = cred_response[0][0]
                    password = cred_response[0][1]
                    response = saas_install.main(dict(
                        db_template = obj.saas_contract_id.db_template,
                        db_name=obj.database_name,
                        modules=modules,
                        config_path = config_path,
                        host_domain=domain_name,
                        host_server=host_server,
                        db_server=db_server,
                        container_port=obj.containter_port,
                        login=login,
                        password=password,
                        version=obj.saas_contract_id.odoo_version_id.code)
                    )
                    if response:
                        _logger.info("========== %r ======="%response)
                        if response.get('modules_installation'):
                            for module in obj.saas_module_ids:
                                module.status = 'installed'
                            obj.missed_modules = False
                        else:
                            obj.missed_modules = True
                            for module in obj.saas_module_ids:                            
                                if module.technical_name not in response.get('modules_missed'):
                                    module.status = 'to_be_installed'
                else:
                    raise UserError('Details Not Found..!')
            except Exception as e:
                raise UserError(e)


    def fetch_client_url(self, domain_name=None):
        for obj in self:
            if obj.saas_contract_id.is_custom_plan:
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
                    obj.install_modules()

                else:
                    raise UserError("Couldn't create the instance with the selected domain name. Please use some other domain name.")
            else:
                obj.missed_modules = False
                super(CustomSaasClient, self).fetch_client_url(domain_name=domain_name)

    @api.model
    def create_docker_instance(self, domain_name=None):
        if self.saas_contract_id.is_custom_plan:
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
                db_server=db_server,
                version=self.saas_contract_id.odoo_version_id.code)
            )
            return response
        else:
            res = super(CustomSaasClient, self).create_docker_instance(domain_name=domain_name)
            return res

    @api.model
    def module_installation_crone_action(self):
        client_ids = self.env['saas.client'].sudo().search([('state', '=', 'started'), ('missed_modules', '=', True)])
        for client_id in client_ids:
            client_id.install_modules()
            
    def drop_db(self):
        for obj in self:
            if obj.saas_contract_id.is_custom_plan:
                if obj.state == "inactive":
                    host_server, db_server = obj.saas_contract_id.server_id.get_server_details()
                    _logger.info("HOST SERER %r   DB SERVER  %r"%(host_server,db_server))
                    response = client.main(obj.database_name, obj.containter_port, host_server, get_module_resource('odoo_saas_kit'), from_drop_db=True, version=self.saas_contract_id.odoo_version_id.code)
                    if not response['db_drop']:
                        raise UserError("ERROR: Couldn't Drop Client Database. Please Try Again Later.\n\nOperation\tStatus\n\nDrop database: \t{}\n".format(response['db_drop']))
                    else:
                        obj.is_drop_db = True
                        if obj.is_drop_container:
                            obj.saas_contract_id.state = 'cancel'
                            obj.state = 'cancel'
            else:
                return super(CustomSaasClient, self).drop_db()
                        
    def drop_container(self):
        for obj in self:
            if obj.saas_contract_id.is_custom_plan:
                if obj.state == "inactive":
                    host_server, db_server = obj.saas_contract_id.server_id.get_server_details()
                    _logger.info("HOST SERER %r   DB SERVER  %r"%(host_server,db_server))
                    response = client.main(obj.database_name, obj.containter_port, host_server, get_module_resource('odoo_saas_kit'), container_id=obj.container_id, db_server=db_server, from_drop_container=True, version=self.saas_contract_id.odoo_version_id.code)
                    if not response['drop_container'] or not response['delete_nginx_vhost'] or not response['delete_data_dir']:
                        raise UserError("ERROR: Couldn't Drop Client Container. Please Try Again Later.\n\nOperation\tStatus\n\nDelete Domain Mapping: \t{}\nDelete Data Directory: \t{}".format(response['drop_container'], response['delete_nginx_vhost']))
                    else:
                        obj.is_drop_container = True
                        if obj.is_drop_db:
                            obj.saas_contract_id.state = 'cancel'
                            obj.state = 'cancel'
            else:
                return super(CustomSaasClient, self).drop_container()

class CustomModuleStatus(models.Model):
    _inherit = 'saas.module.status'

    status = fields.Selection(selection=MODULE_STATUS, default="to_be_installed")

