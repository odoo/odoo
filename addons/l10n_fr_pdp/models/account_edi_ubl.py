import re

from odoo import models
from odoo.tools import html_escape

ALLOWED_CODES = ["PMT", "AAB", "PMD", "TXD", "ACC", "AAI", "SUR", "ABL", "CUS", "BLU", "PAI"]
ALLOWED_CODES_PATTERN = re.compile(r"#(?:%s)#" % "|".join(ALLOWED_CODES))


class AccountEdiUBL(models.AbstractModel):
    _inherit = 'account.edi.ubl'

    def _import_ubl_invoice_add_narration(self, collected_values):
        if collected_values.get('company')._get_peppol_proxy_type() != 'pdp':
            return super()._import_ubl_invoice_add_narration(collected_values)

        collected_values['to_write']['narration'] = ''.join(
            f'<p>{html_escape(ALLOWED_CODES_PATTERN.sub("", note).strip())}</p>'
            for note in self._get_notes(collected_values)
        )
