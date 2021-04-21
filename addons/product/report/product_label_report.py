# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError

def _prepare_data(env, data):
    # change product ids by actual product object to get access to fields in xml template
    # we needed to pass ids because reports only accepts native python types (int, float, strings, ...)
    if data.get('active_model') == 'product.template':
        quantity_by_product = {env['product.template'].with_context(display_default_code=False).browse(int(p)): q for p, q in data.get('quantity_by_product').items()}
    elif data.get('active_model') == 'product.product':
        quantity_by_product = {env['product.product'].with_context(display_default_code=False).browse(int(p)): q for p, q in data.get('quantity_by_product').items()}
    else:
        raise UserError(_('Product model not defined, Please contact your administrator.'))
    layout_wizard = env['product.label.layout'].browse(data.get('layout_wizard'))
    if not layout_wizard:
        return {}

    return {
        'quantity': quantity_by_product,
        'rows': layout_wizard.rows,
        'columns': layout_wizard.columns,
        'page_numbers': (sum(quantity_by_product.values()) - 1) // (layout_wizard.rows * layout_wizard.columns) + 1,
        'price_included': data.get('price_included'),
        'extra_html': layout_wizard.extra_html,
    }

class ReportProductTemplateLabel(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel'
    _description = 'Product Label Report'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, data)

class ReportProductTemplateLabelDymo(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel_dymo'
    _description = 'Product Label Report'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, data)
