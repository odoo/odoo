# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _work_entry_generation_date_to(self):
        return self.l10n_fr_date_to or super()._work_entry_generation_date_to()
