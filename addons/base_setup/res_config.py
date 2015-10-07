# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class base_config_settings(osv.osv_memory):
    _name = 'base.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'group_light_multi_company': fields.boolean('Manage multiple companies',
            help='Work in multi-company environments, with appropriate security access between companies.',
            implied_group='base.group_light_multi_company'),
        'module_share': fields.boolean('Allow documents sharing',
            help="""Share or embbed any screen of Odoo."""),
        'module_portal': fields.boolean('Activate the customer portal',
            help="""Give your customers access to their documents."""),
        'module_auth_oauth': fields.boolean('Use external authentication providers, sign in with Google...'),
        'module_base_import': fields.boolean("Allow users to import data from CSV/XLS/XLSX/ODS files"),
        'module_google_drive': fields.boolean('Attach Google documents to any record',
                                              help="""This installs the module google_docs."""),
        'module_google_calendar': fields.boolean('Allow the users to synchronize their calendar  with Google Calendar',
                                              help="""This installs the module google_calendar."""),
        'module_inter_company_rules': fields.boolean('Manage Inter Company',
            help="""This installs the module inter_company_rules.\n Configure company rules to automatically create SO/PO when one of your company sells/buys to another of your company."""),
        'company_share_partner': fields.boolean('Share partners to all companies',
            help="Share your partners to all companies defined in your instance.\n"
                 " * Checked : Partners are visible for every companies, even if a company is defined on the partner.\n"
                 " * Unchecked : Each company can see only its partner (partners where company is defined). Partners not related to a company are visible for all companies."),
    }

    def open_company(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        return {
            'type': 'ir.actions.act_window',
            'name': 'My Company',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'res.company',
            'res_id': user.company_id.id,
            'target': 'current',
        }

    def get_default_company_share_partner(self, cr, uid, ids, fields, context=None):
        partner_rule = self.pool['ir.model.data'].xmlid_to_object(cr, uid, 'base.res_partner_rule', context=context)
        return {
            'company_share_partner': not bool(partner_rule.active)
        }

    def set_default_company_share_partner(self, cr, uid, ids, context=None):
        partner_rule = self.pool['ir.model.data'].xmlid_to_object(cr, uid, 'base.res_partner_rule', context=context)
        for wizard in self.browse(cr, uid, ids, context=context):
            self.pool['ir.rule'].write(cr, uid, [partner_rule.id], {'active': not bool(wizard.company_share_partner)}, context=context)


# Empty class but required since it's overrided by sale & crm
class sale_config_settings(osv.osv_memory):
    _name = 'sale.config.settings'
    _inherit = 'res.config.settings'
    _columns = {
    }

