# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api

class IrModelReferenceReport(models.AbstractModel):
    _name = 'report.base.report_irmodulereference'

    @api.model
    def _object_find(self, module):
        model_data_obj = self.env['ir.model.data']
        models_data = model_data_obj.search([('model','=','ir.model'), ('module','=',module.name)])
        res_ids = [model_data.res_id for model_data in models_data]
        return self.env['ir.model'].browse(res_ids)

    @api.multi
    def _fields_find(self, model, module):
        res = []
        model_obj = self.env[model]
        model_fields = self.env['ir.model.fields']
        fname_wildcard = 'field_' + model_obj._name.replace('.', '_') + '_%'
        module_fields_ids = self.env['ir.model.data'].search([('model', '=', 'ir.model.fields'), ('module', '=', module.name), ('name', 'like', fname_wildcard)])
        module_fields_res_ids = [x.res_id for x in module_fields_ids]
        if module_fields_res_ids:
            module_fields_names = [x.name for x in model_fields.browse(module_fields_res_ids)]
            res = model_obj.fields_get(allfields=module_fields_names).items()
            res.sort()
        return res

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        module_report = report_obj._get_report_from_name('base.report_irmodulereference')
        selected_modules = self.env['ir.module.module'].browse(self.ids)
        docargs = {
            'doc_ids': self.ids,
            'doc_model': module_report.model,
            'docs': selected_modules,
            'findobj': self._object_find,
            'findfields': self._fields_find,
        }
        return report_obj.render('base.report_irmodulereference', docargs)