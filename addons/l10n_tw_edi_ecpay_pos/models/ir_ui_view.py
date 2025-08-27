from odoo import api, models


class IrUiView(models.Model):
    _name = 'ir.ui.view'
    _inherit = 'ir.ui.view'

    @api.model
    def _get_xml_ids_to_load(self):
        res = super()._get_xml_ids_to_load()
        res += [
            'l10n_tw_edi_ecpay_pos.ecpay_certificate_receipt',
            'l10n_tw_edi_ecpay_pos.ecpay_transaction_receipt',
        ]
        return res
