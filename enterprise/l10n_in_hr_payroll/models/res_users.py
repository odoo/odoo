# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class User(models.Model):
    _inherit = 'res.users'

    l10n_in_relationship = fields.Char(related='employee_id.l10n_in_relationship', readonly=False, related_sudo=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['l10n_in_relationship']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['l10n_in_relationship']
