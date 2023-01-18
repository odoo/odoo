# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_proxy_user(self, company):
        '''Returns the proxy_user associated with this edi format.
        '''
        self.ensure_one()
        return company.account_edi_proxy_client_user_ids.filtered(lambda u: u.edi_format_id == self)
