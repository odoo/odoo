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

from openerp.osv import fields, osv
import os
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class wizard_multi_charts_accounts(osv.osv_memory):
    """
    Change wizard that a new account chart for a company.
        * Add option to install languages during the setup
        * Copy translations for COA, Tax, Tax Code and Fiscal Position from templates to target objects.
    """
    _inherit = 'wizard.multi.charts.accounts'

    def process_translations(self, cr, uid, langs, in_obj, in_field, in_ids, out_obj, out_ids, force_write=False, context=None):
        """
        This method copies translations values of templates into new Accounts/Taxes/Journals for languages selected

        :param cr: A database cursor
        :param uid: ID of the user currently logged in
        :param langs: List of languages to load for new records
        :param in_field: Name of the translatable field of source templates
        :param in_obj: Name of source object of templates.
        :param in_ids: List of ids of source object
        :param out_obj: Destination object for which translation is to be copied
        :param out_ids: List of ids of destination object
        :param force_write: boolean that depicts if we need to create a translation OR simply replace the actual value
            with the translation in the uid's language by doing a write (in case it's TRUE)
        :param context: usual context information. May contain the key 'lang', which is the language of the user running
            the wizard, that will be used if force_write is True

        :return: True
        """
        if context is None:
            context = {}
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
                    if not force_write:
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
                        #replace the value in the destination object only if it's the user lang
                        if context.get('lang') == lang:
                            self.pool.get(out_obj._name).write(cr, uid, out_ids[j], {in_field: value[in_id]})
                else:
                    _logger.info('Language: %s. Translation from template: there is no translation available for %s!' %(lang,  src[in_id]))#out_obj._name))
        return True

    def execute(self, cr, uid, ids, context=None):
        res = super(wizard_multi_charts_accounts, self).execute(cr, uid, ids, context=context)

        obj_multi = self.browse(cr, uid, ids[0], context=context)
        company_id = obj_multi.company_id.id

        # load languages
        langs = []
        res_lang_obj = self.pool.get('res.lang')
        installed_lang_ids = res_lang_obj.search(cr, uid, [])
        installed_langs = [x.code for x in res_lang_obj.browse(cr, uid, installed_lang_ids, context=context)]
        if obj_multi.chart_template_id.spoken_languages:
            for lang in obj_multi.chart_template_id.spoken_languages.split(';'):
                if lang not in installed_langs:
                    # the language is not installed, so we don't need to load its translations
                    continue
                else: 
                    # the language was already installed, so the po files have been loaded at the installation time
                    # and now we need to copy the translations of templates to the right objects
                    langs.append(lang)
        if langs:
            # write account.account translations in the real COA
            self._process_accounts_translations(cr, uid, obj_multi, company_id, langs, 'name', context=context)

            # copy account.tax.code translations
            self._process_tax_codes_translations(cr, uid, obj_multi, company_id, langs, 'name', context=context)

            # copy account.tax translations
            self._process_taxes_translations(cr, uid, obj_multi, company_id, langs, 'name', context=context)

            # copy account.fiscal.position translations
            self._process_fiscal_pos_translations(cr, uid, obj_multi, company_id, langs, 'name', context=context)

        return res

    def _process_accounts_translations(self, cr, uid, obj_multi, company_id, langs, field, context=None):
        obj_acc_template = self.pool.get('account.account.template')
        obj_acc = self.pool.get('account.account')
        acc_template_root_id = obj_multi.chart_template_id.account_root_id.id
        acc_root_id = obj_acc.search(cr, uid, [('company_id', '=', company_id), ('parent_id', '=', None)])[0]
        in_ids = obj_acc_template.search(cr, uid, [('id', 'child_of', [acc_template_root_id])], order='id')[1:]
        out_ids = obj_acc.search(cr, uid, [('id', 'child_of', [acc_root_id])], order='id')[1:]
        return self.process_translations(cr, uid, langs, obj_acc_template, field, in_ids, obj_acc, out_ids, force_write=True, context=context)

    def _process_tax_codes_translations(self, cr, uid, obj_multi, company_id, langs, field, context=None):
        obj_tax_code_template = self.pool.get('account.tax.code.template')
        obj_tax_code = self.pool.get('account.tax.code')
        tax_code_template_root_id = obj_multi.chart_template_id.tax_code_root_id.id
        tax_code_root_id = obj_tax_code.search(cr, uid, [('company_id', '=', company_id), ('parent_id', '=', None)])[0]
        in_ids = obj_tax_code_template.search(cr, uid, [('id', 'child_of', [tax_code_template_root_id])], order='id')[1:]
        out_ids = obj_tax_code.search(cr, uid, [('id', 'child_of', [tax_code_root_id])], order='id')[1:]
        return self.process_translations(cr, uid, langs, obj_tax_code_template, field, in_ids, obj_tax_code, out_ids, force_write=False, context=context)

    def _process_taxes_translations(self, cr, uid, obj_multi, company_id, langs, field, context=None):
        obj_tax_template = self.pool.get('account.tax.template')
        obj_tax = self.pool.get('account.tax')
        in_ids = sorted([x.id for x in obj_multi.chart_template_id.tax_template_ids])
        out_ids = obj_tax.search(cr, uid, [('company_id', '=', company_id)], order='id')
        return self.process_translations(cr, uid, langs, obj_tax_template, field, in_ids, obj_tax, out_ids, force_write=False, context=context)

    def _process_fiscal_pos_translations(self, cr, uid, obj_multi, company_id, langs, field, context=None):
        obj_fiscal_position_template = self.pool.get('account.fiscal.position.template')
        obj_fiscal_position = self.pool.get('account.fiscal.position')
        in_ids = obj_fiscal_position_template.search(cr, uid, [('chart_template_id', '=', obj_multi.chart_template_id.id)], order='id')
        out_ids = obj_fiscal_position.search(cr, uid, [('company_id', '=', company_id)], order='id')
        return self.process_translations(cr, uid, langs, obj_fiscal_position_template, field, in_ids, obj_fiscal_position, out_ids, force_write=False, context=context)

wizard_multi_charts_accounts()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
