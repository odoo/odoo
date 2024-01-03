# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    def _get_preview_template(self):
        if (
            self.env.context.get('active_model') == 'sale.order'
            and self.env.context.get('active_id')
        ):
            return 'sale.quote_document_layout_preview'
        return super()._get_preview_template()

    def _get_render_information(self, styles):
        res = super()._get_render_information(styles)
        if (
            self.env.context.get('active_model') == 'sale.order'
            and self.env.context.get('active_id')
        ):
            res['doc'] = self.env['sale.order'].browse(self.env.context.get('active_id'))
        return res
