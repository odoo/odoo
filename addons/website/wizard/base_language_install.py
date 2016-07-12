# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp.osv import orm, osv, fields


class base_language_install(osv.osv_memory):
    _inherit = "base.language.install"
    _columns = {
        'website_ids': fields.many2many('website', string='Websites to translate'),
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        defaults = super(base_language_install, self).default_get(cr, uid, fields, context)
        website_id = context.get('params', {}).get('website_id')
        if website_id:
            if 'website_ids' not in defaults:
                defaults['website_ids'] = []
            defaults['website_ids'].append(website_id)
        return defaults

    def lang_install(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        action = super(base_language_install, self).lang_install(cr, uid, ids, context)
        language_obj = self.browse(cr, uid, ids)[0]
        website_ids = [website.id for website in language_obj['website_ids']]
        lang_id = self.pool['res.lang'].search(cr, uid, [('code', '=', language_obj['lang'])])
        if website_ids and lang_id:
            data = {'language_ids': [(4, lang_id[0])]}
            self.pool['website'].write(cr, uid, website_ids, data)
        params = context.get('params', {})
        if 'url_return' in params:
            return {
                'url': params['url_return'].replace('[lang]', language_obj['lang']),
                'type': 'ir.actions.act_url',
                'target': 'self'
            }
        return action
