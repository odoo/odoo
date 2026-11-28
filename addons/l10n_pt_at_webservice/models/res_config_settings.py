from odoo import fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pt_at_ws_username = fields.Char(
        related='company_id.l10n_pt_at_ws_username',
        readonly=False,
    )
    l10n_pt_at_ws_password = fields.Char(
        related='company_id.l10n_pt_at_ws_password',
        readonly=False,
    )
    l10n_pt_at_ws_env = fields.Selection(
        related='company_id.l10n_pt_at_ws_env',
        readonly=False,
    )

    def action_l10n_pt_at_ws_test_connection(self):
        """
        Check the webservice configuration (credentials, the AT's public key shipped with Odoo) and the
        way to the AT through Odoo's proxy with a harmless call: the series registered today, which only reads.
        """
        self.ensure_one()
        company = self.company_id.root_id
        if company.l10n_pt_at_ws_env == 'offline':
            raise UserError(self.env._("The AT webservice is offline: choose its test or production environment first."))
        company._l10n_pt_at_ws_call('query', {'dataRegistoDe': self.env['l10n_pt.at.series']._l10n_pt_at_ws_today()})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': self.env._("AT webservice"),
                'message': self.env._(
                    "Connected to the AT's %(environment)s webservice as %(username)s: the credentials are accepted.",
                    environment=dict(company._fields['l10n_pt_at_ws_env']._description_selection(self.env))[company.l10n_pt_at_ws_env],
                    username=company.l10n_pt_at_ws_username,
                ),
            },
        }
