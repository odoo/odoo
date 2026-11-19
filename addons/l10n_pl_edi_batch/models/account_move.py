from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_pl_edi_batch.models.batch_download import CRON_REQUEST_TODAY, TODAY_REQUEST_DELAY


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_l10n_pl_edi_import_from_ksef(self):
        """ Request the latest bills of this company: the batch crons then
            import them, and fill the half-fetched ones. Holding the lock of the
            "request recent bills" cron, a click never runs with the cron or
            another click. Nothing is requested within TODAY_REQUEST_DELAY of
            the last request, nor while a today batch is still in progress.
        """
        def notification(notification_type, message):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'type': notification_type, 'message': message},
            }

        busy = notification('info', self.env._("Bills were just requested from KSeF."))
        try:
            self.env.ref(CRON_REQUEST_TODAY).sudo()._try_lock()
        except UserError:
            return busy

        Batch = self.env['l10n_pl_edi_batch.download'].sudo()
        recently_requested = Batch.search_count([
            ('company_id', '=', self.env.company.id),
            ('date_to', '>', fields.Datetime.now() - TODAY_REQUEST_DELAY),
        ], limit=1)
        if recently_requested or Batch._get_today_in_progress(self.env.company):
            return busy

        Batch._request_today(self.env.company)
        return notification('success', self.env._("Bills requested from KSeF."))
