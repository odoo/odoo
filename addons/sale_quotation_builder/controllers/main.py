# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route
from odoo.addons.http_routing.models.ir_http import unslug


class QuotationBuilderController(Controller):

    @route(["/sale_quotation_builder/template/<string:template_id>"], type='http', auth='user', website=True)
    def sale_quotation_builder_template_view(self, template_id, **post):
        template_id = unslug(template_id)[-1]
        template = request.env['sale.order.template'].browse(template_id).with_context(
            allowed_company_ids=request.env.user.company_ids.ids,
        )
        return request.render('sale_quotation_builder.so_template', {'template': template})
