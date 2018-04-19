# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountInalterabilityCheckWizard(models.TransientModel):
    _inherit = 'account.inalterability.check'

    @api.multi
    def action_get_l10n_fr_certification(self):
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.odoo.com/my/contract/french-certification/db/%s' % db_uuid,
            'target': 'new',
        }
