# -*- coding: utf-8 -*-
from odoo import models


class EdiFormat(models.Model):
    _inherit = 'edi.format'

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_proxy_user(self, company):
        '''Returns the proxy_user associated with this edi format.
        '''
        self.ensure_one()
        return company.edi_proxy_client_ids.filtered(lambda u: u.edi_format_id == self)

    # -------------------------------------------------------------------------
    # To override
    # -------------------------------------------------------------------------

    def _get_proxy_identification(self, company):
        '''Returns the key that will identify company uniquely for this edi format (for example, the vat)
        or raises a UserError (if the user didn't fill the related field).
        TO OVERRIDE
        '''
        return False
