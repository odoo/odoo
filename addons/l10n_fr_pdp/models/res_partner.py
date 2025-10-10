from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ubl_cii_format = fields.Selection(
        selection_add=[
            ('ubl_en16931', "PDP EN16931"),
            ('ubl_en16931_extended', "PDP EN16931 Extended"),
        ]
    )

    def _get_edi_builder(self):
        if self.ubl_cii_format == 'ubl_en16931':
            return self.env['account.edi.xml.ubl_en16931']
        if self.ubl_cii_format == 'ubl_en16931_extended':
            return self.env['account.edi.xml.ubl_en16931_extended']
        return super()._get_edi_builder()
