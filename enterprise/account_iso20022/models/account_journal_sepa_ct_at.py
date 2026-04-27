from lxml import etree
from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_InitgPty(self, payment_method_code):
        if payment_method_code == 'sepa_ct' and self.sepa_pain_version == 'pain.001.001.03.austrian.004':
            InitgPty = etree.Element("InitgPty")
            InitgPty.extend(self._get_company_PartyIdentification32(postal_address=False, issr=False, payment_method_code=payment_method_code))
            return InitgPty
        return super()._get_InitgPty(payment_method_code)
