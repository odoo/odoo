# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AutoVacuum(models.AbstractModel):
    _inherit = 'ir.autovacuum'

    @api.model
    def power_on(self, *args, **kwargs):
        self.env['survey.user_input'].do_clean_emptys()
        return super(AutoVacuum, self).power_on(*args, **kwargs)
