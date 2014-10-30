# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-TODAY OpenERP S.A. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import SUPERUSER_ID
from openerp import models, api, fields, _


class crm_configuration(models.TransientModel):
    _name = 'sale.config.settings'
    _inherit = ['sale.config.settings', 'fetchmail.config.settings']

    group_fund_raising = fields.Boolean("Manage Fund Raising",
        implied_group='crm.group_fund_raising',
        help="""Allows you to trace and manage your activities for fund raising.""")
    module_crm_claim = fields.Boolean("Manage Customer Claims",
        help='Allows you to track your customers/suppliers claims and grievances.\n'
             '-This installs the module crm_claim.')
    module_crm_helpdesk = fields.Boolean("Manage Helpdesk and Support",
        help='Allows you to communicate with Customer, process Customer query, and provide better help and support.\n'
             '-This installs the module crm_helpdesk.')
    alias_prefix = fields.Char('Default Alias Name for Leads')
    alias_domain = fields.Char('Alias Domain', 
        default = lambda self:self.pool['mail.alias']._get_alias_domain(self._cr, SUPERUSER_ID, [1], None, None)[1])
    group_scheduled_calls = fields.Boolean("Schedule calls to manage call center",
        implied_group='crm.group_scheduled_calls',
            help="""This adds the menu 'Scheduled Calls' under 'Sales / Phone Calls'""")

    @api.multi
    def _find_default_lead_alias_id(self):
        alias_id = self.pool['ir.model.data'].xmlid_to_res_id(self._cr, self._uid, 'crm.mail_alias_lead_info')
        if not alias_id:
            alias_ids = self.pool['mail.alias'].search(self._cr, self._uid, 
                [
                    ('alias_model_id.model', '=', 'crm.lead'),
                    ('alias_force_thread_id', '=', False),
                    ('alias_parent_model_id.model', '=', 'crm.team'),
                    ('alias_parent_thread_id', '=', False),
                    ('alias_defaults', '=', '{}')
                ])
            alias_id = alias_ids and alias_ids[0].id or False
        return alias_id

    @api.multi
    def get_default_alias_prefix(self):
        alias_name = False
        alias_id = self._find_default_lead_alias_id()
        if alias_id:
            alias_name = self.pool['mail.alias'].browse(self._cr, self._uid, alias_id, context=self._context).alias_name
            return {'alias_prefix': alias_name}
            # alias_name = self.env['mail.alias'].browse(alias_id, context=context).alias_name
        return {'alias_prefix': alias_name}


    @api.multi
    def set_default_alias_prefix(self):
        mail_alias = self.pool['mail.alias']
        for record in self:
            alias_id = self._find_default_lead_alias_id()
            if not alias_id:
                self = self.with_context(alias_model_name='crm.lead', alias_parent_model_name='crm.team')
                alias_id = mail_alias.create(self._cr, self._uid, {'alias_name': record.alias_prefix})
            else:
                mail_alias.write(self._cr, self._uid, alias_id, {'alias_name': record.alias_prefix})
        return True