# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class Eventevent(models.Model):
    _inherit = 'event.event'
    _populate_sizes = {'small': 5, 'medium': 150, 'large': 400}
    _populate_dependencies = ['res.company']

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company']

        return [
            ('name', populate.constant('lunch_product_category_{counter}')),
            ('company_id', populate.iterate(
                [False, self.env.ref('base.main_company').id] + company_ids,
                [1, 1] + [2/(len(company_ids) or 1)]*len(company_ids))),
        ]
