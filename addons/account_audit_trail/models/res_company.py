# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    check_account_audit_trail = fields.Boolean(string='Audit Trail')

    def cache_invalidation_fields(self):
        # EXTENDS base
        fields = super().cache_invalidation_fields()
        fields.add('check_account_audit_trail')
        return fields
