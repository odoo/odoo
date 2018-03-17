# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ReportQrcodeLable(models.AbstractModel):

    _name = 'report.library.qrcode_label'

    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids',
                                                                []))
        docargs = {
            'doc_ids': docids,
            'doc_model': self.model,
            'docs': docs,
            'get_qr_code': self._get_qr_code,
        }
        render_model = 'library.qrcode_label'
        return self.env['report'].render(render_model, docargs)
