# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_my_edi_mode = fields.Selection(related="company_id.l10n_my_edi_mode", readonly=False)
    l10n_my_edi_default_import_journal_id = fields.Many2one(related="company_id.l10n_my_edi_default_import_journal_id", readonly=False)
    l10n_my_edi_proxy_user_id = fields.Many2one(related="company_id.l10n_my_edi_proxy_user_id")
    l10n_my_edi_company_vat = fields.Char(related="company_id.vat")
    l10n_my_accept_processing = fields.Boolean()

    # ----------------
    # Onchange methods
    # ----------------

    @api.onchange('l10n_my_edi_mode')
    def _onchange_l10n_my_edi_mode(self):
        """ This onchange is mostly here to improve usability by avoiding the need to save when changing the mode. """
        self.l10n_my_edi_proxy_user_id = self.company_id.account_edi_proxy_client_ids.filtered(
            lambda u: u.proxy_type == 'l10n_my_edi' and u.edi_mode == self.l10n_my_edi_mode
        )

    # --------------
    # Action methods
    # --------------

    def action_l10n_my_edi_allow_processing(self):
        """ We always expect the user to give his consent by pressing the button, in any mode, to enable the edi. """
        self.company_id._l10n_my_edi_create_proxy_user()

    def action_l10n_my_edi_unregister(self):
        """ Send a notification to the proxy to free the ID (vat) of the user, and archive the local proxy user.
        Useful if there has been a misconfiguration or the user wishes to use a new database/...
        """
        proxy_user = self.env.company.l10n_my_edi_proxy_user_id
        if not proxy_user:
            return

        # Start by notifying the proxy that we wish to deregister.
        result = proxy_user._l10n_my_edi_contact_proxy('api/l10n_my_edi/1/unregister', {})

        if not result.get('success'):
            # If we get a result, it should always be successful as we only archive. If for any reason it is not, we will raise an error.
            raise UserError(proxy_user.env._("An unexpected error occurred while unregistering. Please try again later."))

        # If all goes well we can deactivate the local user.
        proxy_user.active = False

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
