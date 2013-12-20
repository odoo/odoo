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

    def get_default_alias_prefix(self, cr, uid, ids, context=None):
        alias_name = ''
        mail_alias = self.pool.get('mail.alias')
        try:
            alias_name = self.pool.get('ir.model.data').get_object(cr, uid, 'crm', 'mail_alias_lead_info').alias_name
        except Exception:
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', 'crm.lead')], context=context)
            alias_ids = mail_alias.search(cr, uid, [('alias_model_id', '=', model_ids[0]),('alias_defaults', '=', '{}')], context=context)
            if alias_ids:
                alias_name = mail_alias.browse(cr, uid, alias_ids[0], context=context).alias_name
        return {'alias_prefix': alias_name}

    def set_default_alias_prefix(self, cr, uid, ids, context=None):
        mail_alias = self.pool.get('mail.alias')
        record = self.browse(cr, uid, ids[0], context=context)
        default_alias_prefix = self.get_default_alias_prefix(cr, uid, ids, context=context)['alias_prefix']
        if record.alias_prefix != default_alias_prefix:
            try:
                alias = self.pool.get('ir.model.data').get_object(cr, uid, 'crm', 'mail_alias_lead_info')
                if alias:
                    alias.write({'alias_name': record.alias_prefix})
            except Exception:
                model_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', 'crm.lead')], context=context)
                alias_ids = mail_alias.search(cr, uid, [('alias_model_id', '=', model_ids[0]),('alias_defaults', '=', '{}')], context=context)
                if alias_ids:
                    mail_alias.write(cr, uid, alias_ids[0], {'alias_name': record.alias_prefix}, context=context)
                else:
                    mail_alias.create_unique_alias(cr, uid, {'alias_name': record.alias_prefix}, model_name="crm.lead", context=context)
        return True

    def get_default_alias_domain(self, cr, uid, ids, context=None):
        alias_domain = self.pool.get("ir.config_parameter").get_param(cr, uid, "mail.catchall.domain", context=context)
        if not alias_domain:
            domain = self.pool.get("ir.config_parameter").get_param(cr, uid, "web.base.url", context=context)
            try:
                alias_domain = urlparse.urlsplit(domain).netloc.split(':')[0]
            except Exception:
                pass
        return {'alias_domain': alias_domain}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
