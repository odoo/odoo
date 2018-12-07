# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrModelReferenceReport(models.AbstractModel):
    _name = 'report.base.report_irmodulereference'
    _description = 'Module Reference Report (base)'

    @api.model
    def _object_find(self, module):
        Data = self.env['ir.model.data'].sudo()
        data = Data.search([('model','=','ir.model'), ('module','=',module.name)])
        res_ids = data.mapped('res_id')
        return self.env['ir.model'].browse(res_ids)

    @api.multi
    def _fields_find(self, model, module):
        Data = self.env['ir.model.data'].sudo()
        fname_wildcard = 'field_' + model.replace('.', '_') + '_%'
        data = Data.search([('model', '=', 'ir.model.fields'), ('module', '=', module.name), ('name', 'like', fname_wildcard)])
        if data:
            res_ids = data.mapped('res_id')
            fnames = self.env['ir.model.fields'].browse(res_ids).mapped('name')
            return sorted(self.env[model].fields_get(fnames).items())
        return []

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('base.report_irmodulereference')
        selected_modules = self.env['ir.module.module'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': selected_modules,
            'findobj': self._object_find,
            'findfields': self._fields_find,
        }
