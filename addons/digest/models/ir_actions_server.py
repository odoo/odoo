# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import ValidationError


class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    @api.constrains('code')
    def _check_digest_agg_custom(self):
        kpis = self.env['digest.kpi'].search([('agg_custom', 'in', self.ids)])
        kpis._check_agg_custom()
