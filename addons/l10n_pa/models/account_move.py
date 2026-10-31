# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models
from odoo.tools import SQL


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_sequence_format_param(self, previous):
        # EXTENDS 'account'
        format_string, format_values = super()._get_sequence_format_param(previous)
        if self.country_code == 'PA' and self.l10n_latam_use_documents:
            # DGI Ficha Técnica B07: 10 digits, the fixed regex leaves a 10th digit in prefix1
            prefix = format_values['prefix1'].rstrip('0')
            format_values.update(prefix1=prefix, seq_length=10 - len(re.search(r'[0-9]*$', prefix).group()))
        return format_string, format_values

    def _get_last_sequence_domain(self, relaxed=False):
        # EXTENDS 'l10n_latam_invoice_document'
        condition = super()._get_last_sequence_domain(relaxed)
        if self.country_code == 'PA' and self.l10n_latam_use_documents:
            condition = SQL("%s AND l10n_latam_document_type_id = %s", condition, self.l10n_latam_document_type_id.id or 0)
        return condition

    def _get_l10n_latam_documents_domain(self):
        # EXTENDS 'l10n_latam_invoice_document'
        domain = super()._get_l10n_latam_documents_domain()
        if self.country_code == 'PA' and self.is_sale_document() and not (self.reversed_entry_id or self.debit_origin_id):
            # DGI: 04 and 05 reference an invoice
            domain.append(('code', 'not in', ['04', '05']))
        return domain
