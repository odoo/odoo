# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from dateutil.relativedelta import relativedelta
from itertools import groupby

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class LunchProductCategory(models.Model):
    _inherit = 'lunch.product.category'
    _populate_sizes = {'small': 5, 'medium': 150, 'large': 400}
    _populate_dependencies = ['res.company']

    def _populate_factories(self):
        # TODO topping_ids_{1,2,3}, toppping_label_{1,2,3}, topping_quantity{1,2,3}
        company_ids = self.env.registry.populated_models['res.company']

        return [
            ('name', populate.constant('lunch_product_category_{counter}')),
            ('company_id', populate.iterate(
                [False, self.env.ref('base.main_company').id] + company_ids,
                [1, 1] + [2/(len(company_ids) or 1)]*len(company_ids))),
        ]


class LunchProduct(models.Model):
    _inherit = 'lunch.product'
    _populate_sizes = {'small': 10, 'medium': 150, 'large': 10000}
    _populate_dependencies = ['lunch.product.category', 'lunch.supplier']

    def _populate_factories(self):
        category_ids = self.env.registry.populated_models['lunch.product.category']
        category_records = self.env['lunch.product.category'].browse(category_ids)
        category_by_company = {k: list(v) for k, v in groupby(category_records, key=lambda rec: rec['company_id'].id)}

        supplier_ids = self.env.registry.populated_models['lunch.supplier']
        company_by_supplier = {rec.id: rec.company_id.id for rec in self.env['lunch.supplier'].browse(supplier_ids)}

        def get_category(random=None, values=None, **kwargs):
            company_id = company_by_supplier[values['supplier_id']]
            return random.choice(category_by_company[company_id]).id

        return [
            ('active', populate.iterate([True, False], [0.9, 0.1])),
            ('name', populate.constant('lunch_product_{counter}')),
            ('price', populate.randfloat(0.1, 50)),
            ('supplier_id', populate.randomize(supplier_ids)),
            ('category_id', populate.compute(get_category)),
        ]


class LunchLocation(models.Model):
    _inherit = 'lunch.location'

    _populate_sizes = {'small': 3, 'medium': 50, 'large': 500}
    _populate_dependencies = ['res.company']

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company']

        return [
            ('name', populate.constant('lunch_location_{counter}')),
            ('address', populate.constant('lunch_address_location_{counter}')),
            ('company_id', populate.randomize(company_ids))
        ]


class LunchSupplier(models.Model):
    _inherit = 'lunch.supplier'

    _populate_sizes = {'small': 3, 'medium': 50, 'large': 1500}

    _populate_dependencies = ['lunch.location', 'res.partner', 'res.users']

    def _populate_factories(self):

        location_ids = self.env.registry.populated_models['lunch.location']
        partner_ids = self.env.registry.populated_models['res.partner']
        user_ids = self.env.registry.populated_models['res.users']

        def get_location_ids(random=None, **kwargs):
            nb_locations = random.randint(0, len(location_ids))
            return [(6, 0, random.choices(location_ids, k=nb_locations))]

        return [

            ('active', populate.cartesian([True, False])),
            ('send_by', populate.cartesian(['phone', 'mail'])),
            ('delivery', populate.cartesian(['delivery', 'no_delivery'])),
            ('mon', populate.iterate([True, False], [0.9, 0.1])),
            ('tue', populate.iterate([True, False], [0.9, 0.1])),
            ('wed', populate.iterate([True, False], [0.9, 0.1])),
            ('thu', populate.iterate([True, False], [0.9, 0.1])),
            ('fri', populate.iterate([True, False], [0.9, 0.1])),
            ('sat', populate.iterate([False, True], [0.9, 0.1])),
            ('sun', populate.iterate([False, True], [0.9, 0.1])),
            ('available_location_ids', populate.iterate(
                [[], [(6, 0, location_ids)]],
                then=populate.compute(get_location_ids))),
            ('partner_id', populate.randomize(partner_ids)),
            ('responsible_id', populate.randomize(user_ids)),
            ('moment', populate.iterate(['am', 'pm'])),
            ('automatic_email_time', populate.randfloat(0, 12)),
        ]


class LunchOrder(models.Model):
    _inherit = 'lunch.order'
    _populate_sizes = {'small': 20, 'medium': 3000, 'large': 15000}
    _populate_dependencies = ['lunch.product', 'res.users', 'res.company']

    def _populate_factories(self):
        # TODO topping_ids_{1,2,3}, topping_label_{1,3}, topping_quantity_{1,3}
        user_ids = self.env.registry.populated_models['res.users']
        product_ids = self.env.registry.populated_models['lunch.product']
        company_ids = self.env.registry.populated_models['res.company']

        return [
            ('active', populate.cartesian([True, False])),
            ('state', populate.cartesian(['new', 'confirmed', 'ordered', 'cancelled'])),
            ('product_id', populate.randomize(product_ids)),
            ('user_id', populate.randomize(user_ids)),
            ('note', populate.constant('lunch_note_{counter}')),
            ('company_id', populate.randomize(company_ids)),
            ('quantity', populate.randint(0, 10)),
        ]


class LunchAlert(models.Model):
    _inherit = 'lunch.alert'
    _populate_sizes = {'small': 10, 'medium': 40, 'large': 150}

    _populate_dependencies = ['lunch.location']

    def _populate_factories(self):

        location_ids = self.env.registry.populated_models['lunch.location']

        def get_location_ids(random=None, **kwargs):
            nb_max = len(location_ids)
            start = random.randint(0, nb_max)
            end = random.randint(start, nb_max)
            return location_ids[start:end]

        return [
            ('active', populate.cartesian([True, False])),
            ('recipients', populate.cartesian(['everyone', 'last_week', 'last_month', 'last_year'])),
            ('mode', populate.iterate(['alert', 'chat'])),
            ('mon', populate.iterate([True, False], [0.9, 0.1])),
            ('tue', populate.iterate([True, False], [0.9, 0.1])),
            ('wed', populate.iterate([True, False], [0.9, 0.1])),
            ('thu', populate.iterate([True, False], [0.9, 0.1])),
            ('fri', populate.iterate([True, False], [0.9, 0.1])),
            ('sat', populate.iterate([False, True], [0.9, 0.1])),
            ('sun', populate.iterate([False, True], [0.9, 0.1])),
            ('name', populate.constant('alert_{counter}')),
            ('message', populate.constant('<strong>alert message {counter}</strong>')),
            ('notification_time', populate.randfloat(0, 12)),
            ('notification_moment', populate.iterate(['am', 'pm'])),
            ('until', populate.randdatetime(relative_before=relativedelta(years=-2), relative_after=relativedelta(years=2))),
            ('location_ids', populate.compute(get_location_ids))
        ]
