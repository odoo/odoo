from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ro_edi_client_id = fields.Char(related='company_id.l10n_ro_edi_client_id', readonly=False)
    l10n_ro_edi_client_secret = fields.Char(related='company_id.l10n_ro_edi_client_secret', readonly=False)
    l10n_ro_edi_access_token = fields.Char(related='company_id.l10n_ro_edi_access_token', readonly=False)  # TODO remove readonly=False
    l10n_ro_edi_refresh_token = fields.Char(related='company_id.l10n_ro_edi_refresh_token', readonly=False)
    l10n_ro_edi_access_expiry_date = fields.Date(related='company_id.l10n_ro_edi_access_expiry_date', readonly=False)
    l10n_ro_edi_refresh_expiry_date = fields.Date(related='company_id.l10n_ro_edi_refresh_expiry_date', readonly=False)
    l10n_ro_edi_callback_url = fields.Char(related='company_id.l10n_ro_edi_callback_url')
    l10n_ro_edi_test_env = fields.Boolean(related='company_id.l10n_ro_edi_test_env', readonly=False)
    l10n_ro_edi_anaf_imported_inv_journal = fields.Many2one(
        comodel_name='account.journal',
        related='company_id.l10n_ro_edi_anaf_imported_inv_journal',
        string='Import Vendor Bills in : ',
        readonly=False,
        domain='[("type", "=", "purchase")]',
        default=lambda self: self.env['account.journal'].search([('type', '=', 'purchase')], limit=1))

    def button_l10n_ro_edi_generate_token(self):
        """ Redirects to controllers/main.py ~ `authorize` method """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/l10n_ro_edi/authorize/%s' % self.company_id.id,
            'target': 'new',
        }
