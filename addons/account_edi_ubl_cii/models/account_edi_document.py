# -*- coding: utf-8 -*-

from odoo import models


class AccountEdiDocument(models.Model):
    _inherit = "account.edi.document"

    def _filter_edi_attachments_for_mailing(self):
        self.ensure_one()
        # Avoid having factur-x.xml in the 'send & print' wizard
        if self.edi_format_id.code == 'facturx_1_0_05':
            return {}
        return super()._filter_edi_attachments_for_mailing()
