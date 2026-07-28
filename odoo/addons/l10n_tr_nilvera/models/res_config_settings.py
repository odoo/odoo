from odoo import fields, models, _
from odoo.addons.l10n_tr_nilvera.lib.nilvera_client import _get_nilvera_client


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_tr_nilvera_api_key = fields.Char(
        related='company_id.l10n_tr_nilvera_api_key',
        string="Nilvera API key",
        readonly=False,
    )
    l10n_tr_nilvera_environment = fields.Selection(
        related='company_id.l10n_tr_nilvera_environment',
        string="Nilvera Environment",
        required=True,
        readonly=False,
    )
    l10n_tr_nilvera_purchase_journal_id = fields.Many2one(
        related='company_id.l10n_tr_nilvera_purchase_journal_id',
        readonly=False,
    )

    def nilvera_ping(self):
        """ Test the connection and the API key. """
        self.check_access_rule('read')  # To make sure not everyone can call this method as it's public.
        with _get_nilvera_client(self.env.company) as client:
            # As there is no endpoint to ping Nilvera to make sure the connection works, try an endpoint to get the
            # company's data and this way we can verify the connection and the tax ID in the same step.
            response = client.request("GET", "/general/Company", handle_response=False)
            if response.status_code == 200:
                nilvera_registered_tax_number = response.json().get('TaxNumber')
                if self.env.company.vat == nilvera_registered_tax_number:
                    self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                        'type': 'success',
                        'message': _("Nilvera connection successful!"),
                    })
                else:
                    self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                        'type': 'success',
                        'message': _("Nilvera connection successful but the tax number on Nilvera and Odoo doesn't match. Check Nilvera."),
                    })
            elif response.status_code == 401:
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'danger',
                    'message': _("Nilvera connection was unsuccessful, check the API key."),
                })
            else:
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'danger',
                    'message': _("An error occurred. Try again later."),
                })
