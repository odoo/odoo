from odoo import models


class AccountEdiXmlUBLFrEN16931(models.AbstractModel):
    _name = 'account.edi.xml.ubl_fr_pdp_en16931'
    _inherit = 'account.edi.xml.ubl_bis3'
    _description = 'FR PDP UBL EN16931'
