from odoo import fields, models
from odoo.addons.l10n_tr_nilvera.lib.nilvera_client import NilveraClient


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_default_l10n_tr_nilvera_purchase_journal_id(self):
        return self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company),
            ('type', '=', 'purchase')
        ], limit=1)

    l10n_tr_nilvera_api_key = fields.Char(string='Nilvera API KEY', groups='base.group_system')
    l10n_tr_nilvera_environment = fields.Selection(
        string="Nilvera Environment",
        selection=[
            ('sandbox', 'Sandbox'),
            ('production', 'Production'),
        ],
        required=True,
        default='sandbox',
    )
    l10n_tr_nilvera_purchase_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Nilvera Purchase Journal',
        domain=[('type', '=', 'purchase')],
        store=True, readonly=False,
        default=_get_default_l10n_tr_nilvera_purchase_journal_id,
    )

    def _get_nilvera_client(self):
        self.ensure_one()
        client = NilveraClient(
            environment=self.l10n_tr_nilvera_environment,
            api_key=self.l10n_tr_nilvera_api_key,
        )
        return client
