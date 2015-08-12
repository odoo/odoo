# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, models


class ReportXml(models.Model):
    _inherit = 'ir.actions.report.xml'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        object_id = self.env.context.get('object_id')
        if object_id:
            model = self.env['ir.model'].browse(object_id).model
            args.append(('model', '=', model))
        return super(ReportXml, self).search(args, offset=offset, limit=limit, order=order, count=count)
