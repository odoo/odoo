# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_cn_edi_mode = fields.Selection(related="company_id.l10n_cn_edi_mode", readonly=False)
    l10n_cn_edi_company_vat = fields.Char(related="company_id.vat")
    l10n_cn_accept_processing = fields.Boolean()

    # ----------------
    # Onchange methods
    # ----------------

    def action_open_company_form(self):
        """ This will be used to ease the configuration by allowing to quickly access the company. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_id': self.env.company.id,
            'res_model': 'res.company',
            'target': 'new',
            'view_mode': 'form',
        }
