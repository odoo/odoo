# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


L10N_LT_PAYROLL_WRITABLE_FIELDS = [
    'l10n_lt_working_capacity',
]


class User(models.Model):
    _inherit = ['res.users']

    l10n_lt_working_capacity = fields.Selection(related='employee_ids.l10n_lt_working_capacity', readonly=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + L10N_LT_PAYROLL_WRITABLE_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + L10N_LT_PAYROLL_WRITABLE_FIELDS
