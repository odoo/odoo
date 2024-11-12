# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_tracking = fields.Selection(selection_add=[
        ('course', 'Course Access'),
    ], ondelete={'course': 'set default'})

    def _prepare_service_tracking_tooltip(self):
        if self.service_tracking == 'course':
            return _("Grant access to the eLearning course linked to this product.")
        return super()._prepare_service_tracking_tooltip()

    @api.model
    def _get_product_types_allow_zero_price(self):
        return super()._get_product_types_allow_zero_price() + ["course"]

    def _service_tracking_blacklist(self):
        return super()._service_tracking_blacklist() + ['course']
