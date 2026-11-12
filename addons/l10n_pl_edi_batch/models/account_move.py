from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _cron_l10n_pl_edi_download_bills(self):
        self.env['l10n_pl_edi_batch.download']._cron_request_today()

    def action_l10n_pl_edi_import_from_ksef(self):
        # Request the latest bills of this company: the batch crons then import them, and fill the half-fetched ones
        self.env['l10n_pl_edi_batch.download'].sudo()._request_today(self.env.company)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
