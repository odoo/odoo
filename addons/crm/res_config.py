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
from openerp.osv import fields, osv


class crm_configuration(osv.TransientModel):
    _name = 'sale.config.settings'
    _inherit = ['sale.config.settings', 'fetchmail.config.settings']

    def set_group_multi_salesteams(self, cr, uid, ids, context=None):
        """ This method is automatically called by res_config as it begins
            with set. It is used to implement the 'one group or another'
            behavior. We have to perform some group manipulation by hand
            because in res_config.execute(), set_* methods are called
            after group_*; therefore writing on an hidden res_config file
            could not work.
            If group_multi_salesteams is checked: remove group_mono_salesteams
            from group_user, remove the users. Otherwise, just add
            group_mono_salesteams in group_user.
            The inverse logic about group_multi_salesteams is managed by the
            normal behavior of 'group_multi_salesteams' field.
        """
        def ref(xml_id):
            mod, xml = xml_id.split('.', 1)
            return self.pool['ir.model.data'].get_object(cr, uid, mod, xml, context)

        for obj in self.browse(cr, uid, ids, context=context):
            config_group = ref('base.group_mono_salesteams')
            base_group = ref('base.group_user')
            if obj.group_multi_salesteams:
                base_group.write({'implied_ids': [(3, config_group.id)]})
                config_group.write({'users': [(3, u.id) for u in base_group.users]})
            else:
                base_group.write({'implied_ids': [(4, config_group.id)]})
        return True

    _columns = {
        'group_fund_raising': fields.boolean("Manage Fund Raising",
            implied_group='crm.group_fund_raising',
            help="""Allows you to trace and manage your activities for fund raising."""),
        'module_crm_claim': fields.boolean("Manage Customer Claims",
            help='Allows you to track your customers/suppliers claims and grievances.\n'
                 '-This installs the module crm_claim.'),
        'module_crm_helpdesk': fields.boolean("Manage Helpdesk and Support",
            help='Allows you to communicate with Customer, process Customer query, and provide better help and support.\n'
                 '-This installs the module crm_helpdesk.'),
        'group_multi_salesteams': fields.boolean("Organize Sales activities into multiple Sales Teams",
            implied_group='base.group_multi_salesteams',
            help="""Allows you to use Sales Teams to manage your leads and opportunities."""),
        'alias_prefix': fields.char('Default Alias Name for Leads'),
        'alias_domain' : fields.char('Alias Domain'),
    }

    _defaults = {
        'alias_domain': lambda self, cr, uid, context: self.pool['mail.alias']._get_alias_domain(cr, SUPERUSER_ID, [1], None, None)[1],
    }

    def _find_default_lead_alias_id(self, cr, uid, context=None):
        alias_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'crm.mail_alias_lead_info')
        if not alias_id:
            alias_ids = self.pool['mail.alias'].search(
                cr, uid, [
                    ('alias_model_id.model', '=', 'crm.lead'),
                    ('alias_force_thread_id', '=', False),
                    ('alias_parent_model_id.model', '=', 'crm.case.section'),
                    ('alias_parent_thread_id', '=', False),
                    ('alias_defaults', '=', '{}')
                ], context=context)
            alias_id = alias_ids and alias_ids[0] or False
        return alias_id

    def get_default_alias_prefix(self, cr, uid, ids, context=None):
        alias_name = False
        alias_id = self._find_default_lead_alias_id(cr, uid, context=context)
        if alias_id:
            alias_name = self.pool['mail.alias'].browse(cr, uid, alias_id, context=context).alias_name
        return {'alias_prefix': alias_name}

    def set_default_alias_prefix(self, cr, uid, ids, context=None):
        mail_alias = self.pool['mail.alias']
        for record in self.browse(cr, uid, ids, context=context):
            alias_id = self._find_default_lead_alias_id(cr, uid, context=context)
            if not alias_id:
                create_ctx = dict(context, alias_model_name='crm.lead', alias_parent_model_name='crm.case.section')
                alias_id = self.pool['mail.alias'].create(cr, uid, {'alias_name': record.alias_prefix}, context=create_ctx)
            else:
                mail_alias.write(cr, uid, alias_id, {'alias_name': record.alias_prefix}, context=context)
        return True
