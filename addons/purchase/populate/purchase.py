# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime, timedelta

from odoo import models
from odoo.tools import populate, groupby
from odoo.addons.stock.populate.stock import COMPANY_NB_WITH_STOCK

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _populate_factories(self):
        return super()._populate_factories() + [
            ('po_lead', populate.randint(0, 2))
        ]


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    _populate_sizes = {'small': 100, 'medium': 1_500, 'large': 25_000}
    _populate_dependencies = ['res.partner']

    def _populate_factories(self):
        now = datetime.now()

        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]
        all_partners = self.env['res.partner'].browse(self.env.registry.populated_models['res.partner'])
        partners_by_company = dict(groupby(all_partners, key=lambda par: par.company_id.id))
        partners_inter_company = self.env['res.partner'].concat(*partners_by_company.get(False, []))
        partners_by_company = {com: self.env['res.partner'].concat(*partners) | partners_inter_company for com, partners in partners_by_company.items() if com}

        def get_date_order(values, counter, random):
            # 95.45 % of picking scheduled between (-5, 10) days and follow a gauss distribution (only +-15% PO is late)
            delta = random.gauss(5, 5)
            return now + timedelta(days=delta)

        def get_date_planned(values, counter, random):
            # 95 % of PO Receipt Date between (1, 16) days after the order deadline and follow a exponential distribution
            delta = random.expovariate(5) + 1
            return values['date_order'] + timedelta(days=delta)

        def get_partner_id(values, counter, random):
            return random.choice(partners_by_company[values['company_id']]).id

        def get_currency_id(values, counter, random):
            company = self.env['res.company'].browse(values['company_id'])
            return company.currency_id.id

        return [
            ('company_id', populate.randomize(company_ids)),
            ('date_order', populate.compute(get_date_order)),
            ('date_planned', populate.compute(get_date_planned)),
            ('partner_id', populate.compute(get_partner_id)),
            ('currency_id', populate.compute(get_currency_id)),
        ]


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    _populate_sizes = {'small': 500, 'medium': 7_500, 'large': 125_000}
    _populate_dependencies = ['purchase.order', 'product.product']

    def _populate_factories(self):

        purchase_order_ids = self.env.registry.populated_models['purchase.order']
        product_ids = self.env.registry.populated_models['product.product']

        def get_product_uom(values, counter, random):
            product = self.env['product.product'].browse(values['product_id'])
            return product.uom_id.id

        def get_date_planned(values, counter, random):
            po = self.env['purchase.order'].browse(values['order_id'])
            return po.date_planned

        return [
            ('order_id', populate.iterate(purchase_order_ids)),
            ('name', populate.constant("PO-line-{counter}")),
            ('product_id', populate.randomize(product_ids)),
            ('product_uom', populate.compute(get_product_uom)),
            ('taxes_id', populate.constant(False)),  # to avoid slow _prepare_add_missing_fields
            ('date_planned', populate.compute(get_date_planned)),
            ('product_qty', populate.randint(1, 10)),
            ('price_unit', populate.randint(10, 100)),
        ]
