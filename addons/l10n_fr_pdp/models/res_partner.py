from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ubl_cii_format = fields.Selection(
        selection_add=[
            ('ubl_en16931', "PDP EN16931"),
            ('ubl_en16931_extended', "PDP EN16931 Extended"),
            ('cii_france_cius', "PDP France CIUS"),
            ('cii_france_cius_extended', "PDP France CIUS Extended"),
        ]
    )

    def _get_edi_builder(self):
        if self.ubl_cii_format == 'ubl_en16931':
            return self.env['account.edi.xml.ubl_en16931']
        if self.ubl_cii_format == 'ubl_en16931_extended':
            return self.env['account.edi.xml.ubl_en16931_extended']
        if self.ubl_cii_format == 'cii_france_cius':
            return self.env['account.edi.xml.cii_france_cius']
        if self.ubl_cii_format == 'cii_france_cius_extended':
            return self.env['account.edi.xml.cii_france_cius_extended']
        return super()._get_edi_builder()
