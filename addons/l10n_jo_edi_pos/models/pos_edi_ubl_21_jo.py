from odoo import models


class PosEdiXmlUBL21Jo(models.AbstractModel):
    _name = 'pos.edi.xml.ubl_21.jo'
    _inherit = 'pos.edi.xml.ubl_21'
    _description = 'UBL 2.1 (JoFotara) for PoS Orders'
