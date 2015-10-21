# -*- coding: utf-8 -*-
from openerp import http
from openerp.http import request
from openerp.addons.web_editor.controllers.main import Web_Editor


class WebEditorPointOfSale(Web_Editor):
    @http.route('/point_of_sale/field/customer_facing_display_template', type='http', auth="user")
    def get_field_text_html(self, model=None, res_id=None, field=None, callback=None, **kwargs):
        kwargs['snippets'] = '/point_of_sale/snippets'
        kwargs['template'] = 'point_of_sale.FieldTextHtml'
        extra_head = request.registry["ir.ui.view"].render(request.cr, request.uid, 'point_of_sale.extra_head', None, context=request.context)

        return self.FieldTextHtml(model, res_id, field, callback, head=extra_head, **kwargs)

    @http.route(['/point_of_sale/snippets'], type='json', auth="user", website=True)
    def get_snippets(self):
        return request.registry["ir.ui.view"].render(request.cr, request.uid, 'point_of_sale.customer_facing_display_snippets', None, context=request.context)
