# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv


class crm_configuration(osv.TransientModel):
    _name = 'sale.config.settings'
    _inherit = ['sale.config.settings', 'fetchmail.config.settings']

    _columns = {
        'generate_sales_team_alias': fields.boolean(
            "Automatically generate an email alias at the sales team creation",
            help="Odoo will generate an email alias based on the sales team name"),
        'alias_prefix': fields.char('Default Alias Name for Leads'),
        'alias_domain' : fields.char('Alias Domain'),
        'group_use_lead': fields.selection([
            (0, "Each mail sent to the alias creates a new opportunity"),
            (1, "Use leads if you need a qualification step before creating an opportunity or a customer")
            ], "Leads", 
            implied_group='crm.group_use_lead'),
        'module_crm_voip': fields.boolean("VoIP integration",
            help="Integration with Asterisk"),
        'module_website_sign': fields.boolean("Odoo Sign"),
    }

    _defaults = {
        'alias_domain': lambda self, cr, uid, context: self.pool["ir.config_parameter"].get_param(cr, uid, "mail.catchall.domain", context=context),
    }

    def _find_default_lead_alias_id(self, cr, uid, context=None):
        alias_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'crm.mail_alias_lead_info')
        if not alias_id:
            alias_ids = self.pool['mail.alias'].search(
                cr, uid, [
                    ('alias_model_id.model', '=', 'crm.lead'),
                    ('alias_force_thread_id', '=', False),
                    ('alias_parent_model_id.model', '=', 'crm.team'),
                    ('alias_parent_thread_id', '=', False),
                    ('alias_defaults', '=', '{}')
                ], context=context)
            alias_id = alias_ids and alias_ids[0] or False
        return alias_id

    def get_default_generate_sales_team_alias(self, cr, uid, ids, context=None):
        return {'generate_sales_team_alias': self.pool['ir.values'].get_default(
            cr, uid, 'sales.config.settings', 'generate_sales_team_alias')}

    def set_default_generate_sales_team_alias(self, cr, uid, ids, context=None):
        config_value = self.browse(cr, uid, ids, context=context).generate_sales_team_alias
        self.pool['ir.values'].set_default(cr, uid, 'sales.config.settings', 'generate_sales_team_alias', config_value)

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
                create_ctx = dict(context, alias_model_name='crm.lead', alias_parent_model_name='crm.team')
                alias_id = self.pool['mail.alias'].create(cr, uid, {'alias_name': record.alias_prefix}, context=create_ctx)
            else:
                mail_alias.write(cr, uid, alias_id, {'alias_name': record.alias_prefix}, context=context)
        return True
