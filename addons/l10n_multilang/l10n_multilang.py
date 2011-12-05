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
from tools.translate import _


class wizard_multi_charts_accounts(osv.osv_memory):
    """
    Change wizard that a new account chart for a company.
        * Add option to install languages during the setup
        * Copy translations for COA, Tax, Tax Code and Fiscal Position from templates to target objects.
    """
    _inherit = 'wizard.multi.charts.accounts'

    def copy_translations(self, cr, uid, langs, in_obj, in_field, in_ids, out_obj, out_ids):
        """
        This method copies translations values of templates into new Accounts/Taxes/Journals for languages selected
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param langs: List of languages to load for new records
        @param in_field: Name of the translatable field of source templates
        @param in_obj: Name of source object of templates.
        @param in_ids: List of ids of source object
        @param out_obj: Destination object for which translation is to be copied
        @param out_ids: List of ids of destination object

        @param Return: String containing information of the translations loaded.
        """
        src = {}
        xlat_obj = self.pool.get('ir.translation')
        #find the source from Account Template
        for x in in_obj.browse(cr, uid, in_ids):
            src.update({x.id: x.name})
        for lang in langs:
            #find the value from Translation
            value = xlat_obj._get_ids(cr, uid, in_obj._name + ',' + in_field, 'model', lang, in_ids)
            for j in range(len(in_ids)):
                in_id = in_ids[j]
                if value[in_id]:
                    #copy Translation from Source to Destination object
                    xlat_obj.create(cr, uid, {
                      'name': out_obj._name + ',' + in_field,
                      'type': 'model',
                      'res_id': out_ids[j],
                      'lang': lang,
                      'src': src[in_id],
                      'value': value[in_id],
                })
                else:
                    logger.notifyChannel('addons.'+self._name, netsvc.LOG_ERROR,
                             'Language: %s. Translation from template: there is no translation available for %s!' %(lang,  out_obj._description))
        return True

    def execute(self, cr, uid, ids, context=None):
        res = super(wizard_multi_charts_accounts, self).execute(cr, uid, ids, context=context)
        obj_multi = self.browse(cr, uid, ids[0], context=context)
        obj_mod = self.pool.get('ir.module.module')
        obj_acc_template = self.pool.get('account.account.template')
        obj_acc = self.pool.get('account.account')
        obj_tax_code_template = self.pool.get('account.tax.code.template')
        obj_tax_code = self.pool.get('account.tax.code')
        obj_tax_template = self.pool.get('account.tax.template')
        obj_tax = self.pool.get('account.tax')
        obj_fiscal_position_template = self.pool.get('account.fiscal.position.template')
        obj_fiscal_position = self.pool.get('account.fiscal.position')

        company_id = obj_multi.company_id.id
        acc_template_root_id = obj_multi.chart_template_id.account_root_id.id
        acc_root_id = obj_acc.search(cr, uid, [('company_id', '=', company_id), ('parent_id', '=', None)])[0]
        tax_code_template_root_id = obj_multi.chart_template_id.tax_code_root_id.id
        tax_code_root_id = obj_tax_code.search(cr, uid, [('company_id', '=', company_id), ('parent_id', '=', None)])[0]

        # load languages
        langs = []
        installed_mids = obj_mod.search(cr, uid, [('state', '=', 'installed')])
        for lang in obj_multi.lang_ids:
            langs.append(lang.code)
            obj_mod.update_translations(cr, uid, installed_mids, lang.code)

        # copy account.account translations
        in_ids = obj_acc_template.search(cr, uid, [('id', 'child_of', [acc_template_root_id])], order='id')[1:]
        out_ids = obj_acc.search(cr, uid, [('id', 'child_of', [acc_root_id])], order='id')[1:]
        self.copy_translations(cr, uid, langs, obj_acc_template, 'name', in_ids, obj_acc, out_ids)

        # copy account.tax.code translations
        in_ids = obj_tax_code_template.search(cr, uid, [('id', 'child_of', [tax_code_template_root_id])], order='id')[1:]
        out_ids = obj_tax_code.search(cr, uid, [('id', 'child_of', [tax_code_root_id])], order='id')[1:]
        self.copy_translations(cr, uid, langs, obj_tax_code_template, 'name', in_ids, obj_tax_code, out_ids)

        # copy account.tax translations
        in_ids = sorted([x.id for x in obj_multi.chart_template_id.tax_template_ids])
        out_ids = obj_tax.search(cr, uid, [('company_id', '=', company_id)], order='id')
        self.copy_translations(cr, uid, langs, obj_tax_template, 'name', in_ids, obj_tax, out_ids)

        # copy account.fiscal.position translations
        in_ids = obj_fiscal_position_template.search(cr, uid, [('chart_template_id', '=', obj_multi.chart_template_id.id)], order='id')
        out_ids = obj_fiscal_position.search(cr, uid, [('company_id', '=', company_id)], order='id')
        self.copy_translations(cr, uid, langs, obj_fiscal_position_template, 'name', in_ids, obj_fiscal_position, out_ids)

        return res

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
    }

wizard_multi_charts_accounts()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
