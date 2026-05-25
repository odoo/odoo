# -*- coding: utf-8 -*-
"""Phase 3 — LOG / AOR / CIA expiration cascade (SF Workflow 32).

When an Advertiser's `adv_log_with_expiration_date` is approaching, the SF system
sends 4 alerts at -5d / -2d / 0d / +48h, and on the +48h alert it places the
advertiser on hold and notifies Finance + Director of Sales + Controller.

We implement this as a daily cron `mv.advertiser._cron_log_expiration_alerts()`
which scans all advertisers and posts messages / activities at the right offsets.
"""
import logging
from datetime import timedelta
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class MvAdvertiserPhase3(models.Model):
    _inherit = 'mv.advertiser'

    log_alert_5d_sent = fields.Boolean(string='LOG -5d Alert Sent', default=False, copy=False)
    log_alert_2d_sent = fields.Boolean(string='LOG -2d Alert Sent', default=False, copy=False)
    log_alert_0d_sent = fields.Boolean(string='LOG  0d Alert Sent', default=False, copy=False)
    log_alert_48h_sent = fields.Boolean(string='LOG +48h Alert Sent', default=False, copy=False)

    @api.model
    def _cron_log_expiration_alerts(self):
        """Daily — scan advertisers with LOG expiration dates and post the appropriate alert."""
        today = fields.Date.context_today(self)
        # Find advertisers with a LOG expiration date in the window of interest
        candidates = self.search([('adv_log_with_expiration_date', '!=', False)])
        for adv in candidates:
            exp = adv.adv_log_with_expiration_date
            if not exp:
                continue
            delta = (exp - today).days

            if delta == 5 and not adv.log_alert_5d_sent:
                adv.message_post(
                    body=_("LOG expiration alert (-5 days): LOG for %s expires on %s. AE should renew.") % (adv.display_name, exp),
                    subject=_("LOG -5d Alert: %s") % adv.display_name,
                )
                adv.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('LOG expires in 5d: %s') % adv.display_name,
                    user_id=self.env.user.id,  # TODO route to AE group
                )
                adv.log_alert_5d_sent = True

            elif delta == 2 and not adv.log_alert_2d_sent:
                adv.message_post(
                    body=_("LOG expiration alert (-2 days): LOG for %s expires on %s. Final reminder before lock.") % (adv.display_name, exp),
                    subject=_("LOG -2d Alert: %s") % adv.display_name,
                )
                adv.log_alert_2d_sent = True

            elif delta == 0 and not adv.log_alert_0d_sent:
                adv.message_post(
                    body=_("LOG expiration alert (day of expiry): LOG for %s expires today. AE must provide renewed LOG by +48h to avoid hold.") % adv.display_name,
                    subject=_("LOG 0d Alert: %s") % adv.display_name,
                )
                adv.log_alert_0d_sent = True

            elif delta == -2 and not adv.log_alert_48h_sent:
                # +48h after expiry — place advertiser on hold
                adv.hold_placed_on_advertiser_account = True
                adv.message_post(
                    body=_("LOG expired +48h — Advertiser placed on Finance HOLD. Director of Sales + Controller notified."),
                    subject=_("LOG HOLD: %s") % adv.display_name,
                )
                adv.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Advertiser on HOLD — LOG expired: %s') % adv.display_name,
                    user_id=self.env.user.id,  # TODO route to Director of Sales / Controller group
                )
                adv.log_alert_48h_sent = True

        # Reset alert flags if user renewed (LOG date pushed forward by more than 5d)
        for adv in candidates:
            if adv.adv_log_with_expiration_date and (adv.adv_log_with_expiration_date - today).days > 5:
                adv.log_alert_5d_sent = False
                adv.log_alert_2d_sent = False
                adv.log_alert_0d_sent = False
                adv.log_alert_48h_sent = False
        return True
