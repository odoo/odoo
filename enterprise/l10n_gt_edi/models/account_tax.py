from odoo import fields, models


NOMBRE_CORTO_KEYS = ('IVA', 'PETROLEO', 'TURISMO HOSPEDAJE', 'TURISMO PASAJES', 'TIMBRE DE PRENSA', 'BOMBEROS',
                     'TASA MUNICIPAL', 'BEBIDAS ALCOHOLICAS', 'TABACO', 'CEMENTO', 'BEBIDAS NO ALCOHOLICAS', 'TARIFA PORTUARIA')


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_gt_edi_taxable_unit_code = fields.Integer(
        string="GT Taxable Unit Code",
        help="This field will be used to fill the CodigoUnidadGravable field in the XML to send to Infile.",
    )
    l10n_gt_edi_short_name = fields.Selection(
        selection=[(nombre_corto_key, nombre_corto_key) for nombre_corto_key in NOMBRE_CORTO_KEYS],
        string="GT Tax Short Name",
    )
