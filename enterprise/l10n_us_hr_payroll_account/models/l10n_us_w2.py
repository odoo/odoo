# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import AND


class L10nUsW2(models.Model):
    _inherit = 'l10n.us.w2'

    def _get_allowed_payslips_domain(self):
        self.ensure_one()
        return AND([
            super()._get_allowed_payslips_domain(),
            [('move_id', '!=', False)],
        ])
