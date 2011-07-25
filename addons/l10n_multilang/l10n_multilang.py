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
import os
import netsvc

logger=netsvc.Logger()

class wizard_multi_charts_accounts(osv.osv_memory):
    """
    Change wizard that a new account chart for a company.
        * load Default languages
        * Replace creation of financial accounts by copy from template.
          This change results in adherence to Belgian MAR numbering scheme for cash accounts.
        * Create financial journals for each account of type liquidity
    """
    _inherit = 'wizard.multi.charts.accounts'

    def copy_translation(self, cr, uid, langs, in_obj, in_field, in_ids, out_obj, out_ids):
        done = False
        error = False
        xlat_obj = self.pool.get('ir.translation')
        while not done:
            #compare template with Accounts
            if len(in_ids) != len(out_ids):
                logger.notifyChannel('addons.'+self._name, netsvc.LOG_ERROR,
                     'generate translations from template for %s failed (error 1)!' % out_obj._name)
                error = True
                break
            #copy Translation from Source to Destination object
            for lang in langs:
                cr.execute("SELECT src, value FROM ir_translation "  \
                           "WHERE name=%s AND type='model' AND lang=%s AND res_id IN %s "   \
                           "ORDER by res_id",
                           (in_obj._name + ',' + in_field, lang, tuple(in_ids)))
                xlats = cr.fetchall()
                #IF there is no Translation Available or missing some Translation
                if len(xlats) != len(out_ids):
                    logger.notifyChannel('addons.'+self._name, netsvc.LOG_ERROR,
                        'There is no Translation available for template %s !' % out_obj._name)
                    error = True
                    break
                for i in range(len(out_ids)):
                    src = xlats[i][0]
                    value = xlats[i][1]
                    out_record = out_obj.browse(cr, uid, out_ids[i])
                    #compare with source to destination object name 
                    if getattr(out_record, in_field) != src:
                        logger.notifyChannel('addons.'+self._name, netsvc.LOG_ERROR,
                             'generate translations from template for %s failed (error 3)!' % out_obj._name)
                        error = True
                        break
                    #Copy Translation
                    xlat_obj.create(cr, uid, {
                          'name': out_obj._name + ',' + in_field,
                          'type': 'model',
                          'res_id': out_record.id,
                          'lang': lang,
                          'src': src,
                          'value': value,
                    })
            done = True
        if error:
            raise osv.except_osv(_('Warning!'),
                 _('The generation of translations from the template for %s failed!' % out_obj._name))
        
    def execute(self, cr, uid, ids, context=None):
        super(wizard_multi_charts_accounts, self).execute(cr, uid, ids, context=context)
        obj_multi = self.browse(cr, uid, ids[0], context=context)
        obj_mod = self.pool.get('ir.module.module')
        obj_acc_template = self.pool.get('account.account.template')
        obj_acc = self.pool.get('account.account')
        obj_data = self.pool.get('ir.model.data')

        company_id = obj_multi.company_id.id
        acc_template_root_id = obj_multi.chart_template_id.account_root_id.id
        acc_root_id = obj_acc.search(cr, uid, [('company_id', '=', company_id), ('parent_id', '=', None)])[0]                       
                         
        # load languages
        langs = []
        for lang in obj_multi.lang_ids:
            langs.append(lang.code)
        installed_mids = obj_mod.search(cr, uid, [('state', '=', 'installed')])
        for lang in langs:
                    obj_mod.update_translations(cr, uid, installed_mids, lang)

        # copy account.account translations
        in_field = 'name'
        in_ids = obj_acc_template.search(cr, uid, [('id', 'child_of', [acc_template_root_id])], order='id')[1:]
        out_ids = obj_acc.search(cr, uid, [('id', 'child_of', [acc_root_id])], order='id')[1:]
        self.copy_translation(cr, uid, langs, obj_acc_template, in_field, in_ids, obj_acc, out_ids)

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
                module_obj = self.pool.get('ir.module.module')
                module_id = module_obj.search(cr, uid, [('name', '=', modulename)], context=context)
                module = module_obj.browse(cr, uid, module_id, context=context)[0]
                dirpath = module_obj._translations_subdir(module)
                if dirpath:
                    for po in os.listdir(dirpath):
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
