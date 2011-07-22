# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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


from osv import fields, osv


class wizard_multi_charts_accounts(osv.osv_memory):
    """
    Change wizard that a new account chart for a company.
        * load Default languages
        * Replace creation of financial accounts by copy from template.
          This change results in adherence to Belgian MAR numbering scheme for cash accounts.
        * Create financial journals for each account of type liquidity
    """
    _inherit = 'wizard.multi.charts.accounts'

    def onchange_chart_template_id(self, cr, uid, ids, chart_template_id=False, context=None):
        res = super(wizard_multi_charts_accounts, self).onchange_chart_template_id(cr, uid, ids, chart_template_id, context=context)
        installed_lang = self.get_lang(cr, uid, chart_template_id, context=context)
        res['value'].update({'lang_ids': installed_lang})
        return res
    
    def get_lang(self, cr, uid, template_id=False, context=None):
        installed_lang = []
        if template_id:
            cr.execute("SELECT module from ir_model_data where model='account.chart.template' and res_id=%s" % (template_id))
            modulename = cr.fetchone()
            modulename = modulename and modulename[0] or False
            if modulename:
                import os
                module_obj = self.pool.get('ir.module.module')
                module_id = module_obj.search(cr, uid, [('name', '=', modulename)], context=context)
                module = module_obj.browse(cr, uid, module_id, context=context)[0]
                dirpath = module_obj._translations_subdir(module)
                if dirpath:
                    po_files = os.listdir(dirpath)
                    for po in po_files:
                        lang_id = self.pool.get('res.lang').search(cr, uid, [('code', 'ilike', '%s' % (po.split('.')[0])), ('translatable', '=', True)], context=context)
                        if lang_id:
                            installed_lang.append(lang_id[0])
        return installed_lang

    def default_get(self, cr, uid, fields, context=None):
        res = super(wizard_multi_charts_accounts, self).default_get(cr, uid, fields, context=context)
        installed_lang = self.get_lang(cr, uid, res.get('chart_template_id'), context=context)
        res.update({'lang_ids': installed_lang, 'bank_accounts_id': []})
        return res

    _columns = {
        'lang_ids': fields.many2many('res.lang', 'res_lang_type_rel', 'wizard_id', 'lang_id', 'Language'),
        'bank_from_template': fields.boolean('Banks/Cash from Template', 
            help="If True then Generate Bank/Cash accounts and journals from the Templates.", readonly=True),
    }
  
wizard_multi_charts_accounts()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
