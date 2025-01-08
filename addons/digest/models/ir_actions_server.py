# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    @api.constrains('code')
    def _check_digest_agg_custom(self):
        kpis = self.env['digest.kpi'].search([('agg_custom', 'in', self.ids)])
        kpis._check_agg_custom()
