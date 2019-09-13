# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class AccountTaxGroup(models.Model):

    _inherit = 'account.tax.group'

    # values from http://www.afip.gob.ar/fe/documentos/otros_Tributos.xlsx
    l10n_ar_tribute_afip_code = fields.Selection([
        ('01', '01 - Impuestos nacionales'),
        ('02', '02 - Impuestos provinciales'),
        ('03', '03 - Impuestos municipales'),
        ('04', '04 - Impuestos internos'),
        ('06', '06 - Percepción de IVA'),
        ('07', '07 - Percepción de IIBB'),
        ('08', '08 - Percepciones por Impuestos Municipales'),
        ('09', '09 - Otras Percepciones'),
        ('99', '99 - Otros'),
    ], string='Tribute AFIP Code', index=True, readonly=True)
    # values from http://www.afip.gob.ar/fe/documentos/OperacionCondicionIVA.xls
    l10n_ar_vat_afip_code = fields.Selection([
        ('0', 'No Corresponde'),
        ('1', 'No Gravado'),
        ('2', 'Exento'),
        ('3', '0%'),
        ('4', '10.5%'),
        ('5', '21%'),
        ('6', '27%'),
        ('8', '5%'),
        ('9', '2,5%'),
    ], string='VAT AFIP Code', index=True, readonly=True)
