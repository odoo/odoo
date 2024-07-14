# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    journal_id = fields.Many2one(
        'account.journal',
        domain=lambda self: [('type', 'in', ('general', 'sale'))] if self.env.company.country_code != 'CL' else [('type', '=', 'general')])

    def open_ui(self):
        for config in self:
            if not config.company_id.country_id:
                raise UserError(_("You have to set a country in your company setting."))
        return super().open_ui()

    def get_limited_partners_loading(self):
        partner_ids = super().get_limited_partners_loading()
        if (self.env.ref('l10n_cl.par_cfa').id,) not in partner_ids:
            partner_ids.append((self.env.ref('l10n_cl.par_cfa').id,))
        return partner_ids
