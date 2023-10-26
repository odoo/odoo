# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class Users(models.Model):
    _inherit = "res.users"

    _populate_sizes = {"small": 10, "medium": 2000, "large": 10000}

    _populate_dependencies = ["res.partner"]

    def _populate_factories(self):
        last_id = self.env["res.users"].search([], order="id desc", limit=1).id

        partner_ids = list(self.env.registry.populated_models["res.partner"])

        def get_partner_id(random=None, **kwargs):
            partner_id = random.choice(partner_ids)
            partner_ids.remove(partner_id)
            return partner_id

        def compute_login(values=None, counter=0, **kwargs):
            return f'user_login_{last_id + counter + 1}'

        def compute_name(values=None, counter=0, **kwargs):
            return f'user_{last_id + counter + 1}'

        return [
            ("active", populate.cartesian([True, False], [0.9, 0.1])),
            ("partner_id", populate.compute(get_partner_id)),
            ('login', populate.compute(compute_login)),
            ('name', populate.compute(compute_name)),
        ]

    def _populate(self, scale):
        self = self.with_context(no_reset_password=True)  # avoid sending reset password email
        return super(Users, self)._populate(scale)
