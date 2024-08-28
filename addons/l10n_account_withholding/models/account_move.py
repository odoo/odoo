# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_account_withholding_certificate_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string='Withholding Certificates',
        relation='res_id',
        domain=[('res_model', '=', 'account.move')],
        copy=False,
    )

    # --------------
    # Action methods
    # --------------

    def action_download_withholding_certificates(self):
        """ Returns the action to download all withholding certificates in the records in self. """
        return {
            'type': 'ir.actions.act_url',
            'url': f'/l10n_account_withholding/download_invoice_withholding_certificate/{",".join(map(str, self.l10n_account_withholding_certificate_ids.ids))}',
        }
