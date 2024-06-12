# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    check_account_audit_trail = fields.Boolean(string='Audit Trail', related='company_id.check_account_audit_trail', readonly=False)

    @api.constrains('check_account_audit_trail')
    def _check_audit_trail_records(self):
        if not self.check_account_audit_trail:
            move_count = self.env['account.move'].search_count([('company_id', '=', self.company_id.id)], limit=1)
            if move_count > 0:
                raise UserError(_("Can't disable audit trail when there are existing records."))
