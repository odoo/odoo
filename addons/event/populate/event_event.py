# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import models
from odoo.tools import populate


class Eventevent(models.Model):
    _inherit = 'event.event'
    _populate_sizes = {
        'small': 5,
        'medium': 150,
        'large': 400
    }
    _populate_dependencies = [
        'res.company',  # MC setup
        'res.partner',  # organizer / address
    ]

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company']

        def _get_date_begin(random=None, **kwargs):
            delta = random.randint(-364, 364)
            return datetime.now() + timedelta(days=delta)

        def _get_date_end(random=None, values=None, counter=0, **kwargs):
            date_begin = values['date_begin']
            delta = random.randint(0, 10)
            return date_begin + timedelta(days=delta)

        return [
            ('name', populate.constant('event_{counter}')),
            ('company_id', populate.iterate(
                [False, self.env.ref('base.main_company').id] + company_ids,
                [1, 1] + [2/(len(company_ids) or 1)]*len(company_ids))
             ),
            ('date_begin', populate.compute(_get_date_begin)),
            ('date_end', populate.compute(_get_date_end)),
            # ('organizer_id', populate.randomize(
            #     [False] + self.env['res.partner.title'].search([]).ids)
            #  ),
        ]
