# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUBL21Zatca(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_21.zatca"

    def _l10n_sa_get_payment_means_code(self, invoice):
        """
            Return payment means code to be used to set the value on the XML file
        """
        res = super()._l10n_sa_get_payment_means_code(invoice)
        if invoice._l10n_sa_is_simplified() and invoice.pos_order_ids:
            res = invoice.pos_order_ids.payment_ids[0].payment_method_id.type
        return res
