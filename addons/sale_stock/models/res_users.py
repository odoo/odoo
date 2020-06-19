# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class Users(models.Model):
    _inherit = ['res.users']

    property_warehouse_id = fields.Many2one('stock.warehouse', string='Default Warehouse', company_dependent=True, check_company=True)

    def _get_default_warehouse_id(self):
        if self.property_warehouse_id:
            return self.property_warehouse_id
        # !!! Any change to the following search domain should probably
        # be also applied in sale_stock/models/sale_order.py/_init_column.
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights.
            Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """

        sale_stock_writeable_fields = [
            'property_warehouse_id',
        ]

        init_res = super().__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = type(self).SELF_READABLE_FIELDS + sale_stock_writeable_fields
        type(self).SELF_WRITEABLE_FIELDS = type(self).SELF_WRITEABLE_FIELDS + sale_stock_writeable_fields
        return init_res
