# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models
from odoo.tools import populate
from odoo.addons.stock.populate.stock import COMPANY_NB_WITH_STOCK

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = "product.category"
    _populate_sizes = {"small": 50, "medium": 500, "large": 30000}

    def _populate_factories(self):
        def get_name(values=None, counter=0, complete=False, **kwargs):
            return "%s_%s_%s" % ("product_category", int(complete), counter)

        # quid of parent_id ???

        return [("name", populate.compute(get_name))]


class ProductProduct(models.Model):
    _inherit = "product.product"
    _populate_sizes = {"small": 150, "medium": 5000, "large": 60000}

    def _populate_factories(self):

        return [
            ("name", populate.constant('product_template_name_{counter}')),
            ("sequence", populate.randomize([False] + [i for i in range(1, 101)])),
            ("description", populate.constant('product_template_description_{counter}')),
            ("default_code", populate.constant('product_default_code_{counter}')),
            ("active", populate.randomize([True, False], [0.8, 0.2])),
        ]


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    _populate_sizes = {'small': 450, 'medium': 15_000, 'large': 180_000}
    _populate_dependencies = ['res.partner']

    def _populate_factories(self):
        random = populate.Random('product_with_supplierinfo')
        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK] + [False]
        partner_ids = self.env.registry.populated_models['res.partner']
        product_templates_ids = self.env['product.product'].browse(self.env.registry.populated_models['product.product']).product_tmpl_id.ids
        product_templates_ids = random.sample(product_templates_ids, int(len(product_templates_ids) * 0.95))

        def get_company_id(values, counter, random):
            partner = self.env['res.partner'].browse(values['name'])
            if partner.company_id:
                return partner.company_id.id
            return random.choice(company_ids)

        return [
            ('name', populate.randomize(partner_ids)),
            ('company_id', populate.compute(get_company_id)),
            ('product_tmpl_id', populate.iterate(product_templates_ids)),
            ('product_name', populate.constant("SI-{counter}")),
            ('sequence', populate.randint(1, 10)),
            ('min_qty', populate.randint(0, 10)),
            ('price',  populate.randint(10, 100)),
            ('delay',  populate.randint(1, 10)),
        ]
