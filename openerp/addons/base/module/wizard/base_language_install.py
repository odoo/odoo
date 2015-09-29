# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _

class base_language_install(osv.osv_memory):
    """ Install Language"""

    _name = "base.language.install"
    _description = "Install Language"
    _columns = {
        'lang': fields.selection(tools.scan_languages(),'Language', required=True),
        'overwrite': fields.boolean('Overwrite Existing Terms', help="If you check this box, your customized translations will be overwritten and replaced by the official ones."),
        'state':fields.selection([('init','init'),('done','done')], 'Status', readonly=True),
    }
    _defaults = {
        'state': 'init',
        'overwrite': False
    }
    def lang_install(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        language_obj = self.browse(cr, uid, ids)[0]
        lang = language_obj.lang
        if lang:
            modobj = self.pool.get('ir.module.module')
            mids = modobj.search(cr, uid, [('state', '=', 'installed')])
            if language_obj.overwrite:
                context = {'overwrite': True}
            modobj.update_translations(cr, uid, mids, lang, context or {})
            self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return {
            'name': _('Language Pack'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'base.language.install',
            'domain': [],
            'context': dict(context, active_ids=ids),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': ids and ids[0] or False,
        }
