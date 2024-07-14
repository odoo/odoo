# -*- coding: utf-8 -*-
import logging
from odoo import models, _, fields
from odoo.addons.l10n_be_codabox.const import raise_deprecated


class AccountJournal(models.Model):
    _inherit = "account.journal"

    ############################
    # COMMON METHODS
    ############################

    def _l10n_be_codabox_fetch_transactions_from_iap(self, session, company, file_type, date_from=None, ibans=None):
        raise_deprecated(self.env)

    def _l10n_be_codabox_fetch_coda_transactions(self, company):
        raise_deprecated(self.env)

    def _l10n_be_codabox_fetch_soda_transactions(self, company):
        raise_deprecated(self.env)

    def l10n_be_codabox_manually_fetch_soda_transactions(self):
        raise_deprecated(self.env)

    def _l10n_be_codabox_cron_fetch_soda_transactions(self):
        raise_deprecated(self.env)
