from odoo import models


class AccountEdiXmlCiiFranceCiusExtended(models.AbstractModel):
    _name = 'account.edi.xml.cii_france_cius_extended'
    _inherit = 'account.edi.xml.cii_france_cius'
    _description = 'UN/CEFACT CII France CIUS (EN16931) Extended CTC FR'
