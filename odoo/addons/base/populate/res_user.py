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

    _populate_dependencies = ["res.groups", "res.partner"]

    def _populate_factories(self):
        group_internal_user = self.env.ref('base.group_user').id
        group_portal_user = self.env.ref('base.group_portal').id

        def generate_partner_id(iterator, *args):
            partner_factories = self.env['res.partner']._populate_factories()
            partner_generator = populate.chain_factories(partner_factories, self._name)
            for dependant_values in partner_generator:
                values = next(iterator)
                yield {**dependant_values, **values, '__complete': values['__complete']}

        def get_company_ids(values, **kwargs):
            return [(6, 0, [values['company_id']])]

        def get_groups_id(values, counter, random):
            return random.choices([group_internal_user, group_portal_user], [0.8, 0.2])

        return [
            ('active', populate.cartesian([True, False], [0.9, 0.1])),
            ('partner_id', generate_partner_id),
            ('company_id', populate.randomize(self.env.registry.populated_models['res.company'])),
            ('company_ids', populate.compute(get_company_ids)),
            ('login', populate.constant('user_login_{counter}')),
            ('name', populate.constant('user_{counter}')),
            ('groups_id', populate.compute(get_groups_id))
        ]

    def _populate(self, size):
        self = self.with_context(no_reset_password=True)  # avoid sending reset password email
        return super(Users, self)._populate(size)
