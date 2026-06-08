# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection import format_timestamp
from odoo.addons.l10n_hu_edi_receive.models.l10n_hu_edi_connection import L10nHuEdiConnection


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def l10n_hu_edi_show_nav_sync_button(self):
        return bool({'test', 'production'} & set(self.env.companies.mapped('l10n_hu_edi_server_mode')))

    def l10n_hu_edi_receive_inbound_invoices(self, datetime_from, datetime_to):
        self.ensure_one()

        credentials = self.sudo()._l10n_hu_edi_get_credentials_dict()
        datetime_from = format_timestamp(datetime_from)
        datetime_to = format_timestamp(datetime_to)
        fetch_next_page = True
        page = 1
        all_moves = self.env['account.move']

        with L10nHuEdiConnection(self.env) as connection:
            while fetch_next_page:
                digests, fetch_next_page = connection.query_invoice_digest(credentials, datetime_from, datetime_to, page, self)
                moves_vals_list, post_process_data_list = connection.query_invoice_data(credentials, digests, self)
                moves = self.env['account.move'].create(moves_vals_list)
                self.env['account.move']._l10n_hu_edi_post_process_data(moves, post_process_data_list)
                all_moves += moves
                page += 1

        return all_moves
