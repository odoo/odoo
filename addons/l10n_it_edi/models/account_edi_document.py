# -*- coding: utf-8 -*-

from odoo import models


class AccountEdiDocument(models.Model):
    _inherit = "account.edi.document"

    def _filter_edi_attachments_for_mailing(self):
        self.ensure_one()
        if self.edi_format_id.code == 'fattura_pa':
            return {}
        return super()._filter_edi_attachments_for_mailing()
