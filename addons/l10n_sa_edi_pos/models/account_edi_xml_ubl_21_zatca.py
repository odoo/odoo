from odoo import models


class AccountEdiXmlUBL21Zatca(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_21.zatca"

    def _l10n_sa_get_payment_means_code(self, invoice):
        """
            Return payment means code to be used to set the value on the XML file
        """
        res = super()._l10n_sa_get_payment_means_code(invoice)
<<<<<<< fd443ac3492a67abeed41bf81f95f48f63f0ce96
        if invoice._l10n_sa_is_simplified() and invoice.pos_order_ids.payment_ids:
            res = invoice.pos_order_ids.payment_ids[0].payment_method_id.type
||||||| 160278d39eaffc343d23520a4d966fd3cbb4013c
        if invoice._l10n_sa_is_simplified() and invoice.sudo().pos_order_ids:
            res = invoice.sudo().pos_order_ids.payment_ids[0].payment_method_id.type
=======
        if invoice._l10n_sa_is_simplified() and invoice.sudo().pos_order_ids.payment_ids:
            res = invoice.sudo().pos_order_ids.payment_ids[0].payment_method_id.type
>>>>>>> ab4841e4124e3ec7eebf19a5d0aa8b4eba371a9d
        return res
