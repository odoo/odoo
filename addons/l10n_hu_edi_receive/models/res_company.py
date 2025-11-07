# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection import format_timestamp
from odoo.addons.l10n_hu_edi_receive.models.l10n_hu_edi_connection import L10nHuEdiConnection


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_hu_edi_last_nav_sync = fields.Datetime(
        string='Last NAV Invoice Sync Time',
        default=lambda self: fields.Datetime.now(),
    )
    l10n_hu_edi_receive_from = fields.Datetime()
    l10n_hu_edi_receive_to = fields.Datetime()

    @api.model
    def l10n_hu_edi_show_nav_sync_button(self, company_ids):
        return any(company.l10n_hu_edi_server_mode in ['test', 'production'] for company in self.browse(company_ids))

    @api.model
    def _l10n_hu_edi_cron_query_invoice_digest(self, from_cron=True):
        companies = self._l10n_hu_edi_get_edi_companies(from_cron)
        for company in companies:
            company.with_company(company)._l10n_hu_edi_query_invoice_digest(from_cron)

        self.env.ref('l10n_hu_edi_receive.ir_cron_query_invoice_data')._trigger()

    @api.model
    def _l10n_hu_edi_get_edi_companies(self, from_cron=True):
        domain = [('l10n_hu_edi_server_mode', 'in', ['test', 'production'])]
        if not from_cron:
            domain.extend([('l10n_hu_edi_receive_from', '!=', False), ('l10n_hu_edi_receive_to', '!=', False)])

        return self.search(domain)

    def _l10n_hu_edi_query_invoice_digest(self, from_cron):
        self.ensure_one()

        with L10nHuEdiConnection(self.env) as connection:
            credentials = self._l10n_hu_edi_get_credentials_dict()
            datetime_from = self.l10n_hu_edi_last_nav_sync if from_cron else self.l10n_hu_edi_receive_from
            datetime_to = fields.Datetime.now() if from_cron else self.l10n_hu_edi_receive_to

            response = connection.query_invoice_digest(credentials, format_timestamp(datetime_from), format_timestamp(datetime_to))
            if response == 'OK':
                if from_cron or datetime_to > self.l10n_hu_edi_last_nav_sync >= datetime_from:
                    self.l10n_hu_edi_last_nav_sync = datetime_to

                if not from_cron:
                    self.l10n_hu_edi_receive_from = self.l10n_hu_edi_receive_to = False

    @api.model
    def _l10n_hu_edi_cron_query_invoice_data(self):
        companies = self._l10n_hu_edi_get_edi_companies()
        for company in companies:
            company.with_company(company)._l10n_hu_edi_query_invoice_data()

        self.env.ref('l10n_hu_edi_receive.ir_cron_parse_invoice_data')._trigger()

    def _l10n_hu_edi_query_invoice_data(self):
        self.ensure_one()

        with L10nHuEdiConnection(self.env) as connection:
            credentials = self._l10n_hu_edi_get_credentials_dict()
            moves = self.env['account.move'].search([('company_id', '=', self.id), ('l10n_hu_edi_state', '=', 'digested')])
            connection.query_invoice_data(credentials, moves)
