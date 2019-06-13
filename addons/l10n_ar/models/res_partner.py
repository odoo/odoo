# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResPartner(models.Model):

    _inherit = 'res.partner'

    l10n_ar_gross_income_number = fields.Char(
        'Gross Income Number',
    )
    l10n_ar_gross_income_type = fields.Selection([
        ('multilateral', 'Multilateral'),
        ('local', 'Local'),
        ('no_liquida', 'No Liquida')],
        'Gross Income Type',
        help='Type of gross income: exempt, local, multilateral',
    )
    l10n_ar_afip_responsability_type_id = fields.Many2one(
        'l10n_ar.afip.responsability.type',
        string='AFIP Responsability Type',
        index=True,
        help='Defined by AFIP to identify the type of responsabilities that a'
        ' person or a legal entity could have and that impacts in the type of'
        ' operations and requirements they need.',
    )
    l10n_ar_special_purchase_document_type_ids = fields.Many2many(
        'l10n_latam.document.type',
        'res_partner_document_type_rel',
        'partner_id', 'document_type_id',
        string='Other Purchase Documents',
        help='Set here if this partner can issue other documents further '
        'than invoices, credit notes and debit notes',
    )

    def _get_afip_responsabilities(self):
        """ Return the list of values of the selection field. """
        return [
            ('1', 'IVA Responsable Inscripto'),
            ('3', 'IVA no Responsable'),
            ('4', 'IVA Sujeto Exento'),
            ('5', 'Consumidor Final'),
            ('6', 'Responsable Monotributo'),
            ('8', 'Proveedor del Exterior'),
            ('9', 'Cliente del Exterior'),
            ('10', 'IVA Liberado – Ley Nº 19.640'),
            ('13', 'Monotributista Social'),
        ]
