# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        model_id = self.env.context.get('object_id')
        if model_id:
            model = self.env['ir.model'].browse(model_id).model
            args.append(('model', '=', model))
        return super(IrActionsReport, self).search(args, offset=offset, limit=limit, order=order, count=count)
