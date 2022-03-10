# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class Users(models.Model):
    _inherit = "res.users"

    _populate_sizes = {
        'small': 10,
        'medium': 1000,
        'large': 10000,
    }

    _populate_dependencies = ["res.partner"]

    def _populate_factories(self):
        def get_company_ids(values, **kwargs):
            return [(6, 0, [values['company_id']])]

        return [
            ('active', populate.cartesian([True, False], [0.9, 0.1])),
            ('company_id', populate.randomize(self.env.registry.populated_models['res.company'])),
            ('company_ids', populate.compute(get_company_ids)),
            ('login', populate.constant('user_login_{counter}')),
            ('name', populate.constant('user_{counter}')),
            ('tz', populate.randomize([tz for tz in self.env['res.partner']._fields['tz'].get_values(self.env)])),
        ]

    def _populate(self, size):
        self = self.with_context(no_reset_password=True)  # avoid sending reset password email
        return super(Users, self)._populate(size)
