# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrActionsReportXML(models.Model):
    _inherit = 'ir.actions.report.xml'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        model_id = self._context.get('object_id')
        if model_id:
            args.append(('model', '=', self.env['ir.model'].browse(model_id).model))
        return super(IrActionsReportXML, self).search(args, offset=offset, limit=limit, order=order, count=count)
