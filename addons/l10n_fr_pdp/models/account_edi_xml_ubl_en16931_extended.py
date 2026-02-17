from odoo import models
from odoo.tools import str2bool


class AccountEdiXmlUBLFrEN16931Extended(models.AbstractModel):
    _name = 'account.edi.xml.ubl_fr_pdp_en16931_extended'
    _inherit = 'account.edi.xml.ubl_bis3'
    _description = 'FR PDP UBL EN16931 extended'

    def _export_invoice(self, invoice, convert_fixed_taxes=True):
        # Just like bis 3.0 if the 'account_edi_ubl_cii.use_new_dict_to_xml_helpers' param is set,
        # use the new dict_to_xml helpers.
        if (
            self._name == 'account.edi.xml.ubl_fr_pdp_en16931_extended'
            and str2bool(
                self.env['ir.config_parameter'].sudo().get_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True),
                default=True,
            )
        ):
            return self._export_invoice_new(invoice)

        return super()._export_invoice(invoice, convert_fixed_taxes=convert_fixed_taxes)
