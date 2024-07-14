# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_ec_get_ats_latam_document_type_code(self):
        self.ensure_one()
        doc_type_code = self.l10n_latam_document_type_id.code
        if not doc_type_code and self.l10n_ec_withhold_type == 'in_withhold':
            doc_type_code = '07'
        return doc_type_code
