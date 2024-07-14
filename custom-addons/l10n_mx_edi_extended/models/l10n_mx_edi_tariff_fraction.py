# coding: utf-8

from odoo import fields, models, api
from odoo.osv import expression


class L10nMXEdiTariffFraction(models.Model):
    _name = 'l10n_mx_edi.tariff.fraction'
    _description = "Mexican EDI Tariff Fraction"
    _rec_names_search = ['name', 'code']

    code = fields.Char(
        help="Code defined in the SAT to this record.")
    name = fields.Char(
        help="Name defined in the SAT catalog to this record.")
    uom_code = fields.Char(
        help="UoM code related with this tariff fraction. This value is defined in the SAT catalog and will be "
             "assigned in the attribute 'UnidadAduana' in the merchandise.")
    active = fields.Boolean(
        help="If the tariff fraction has expired it could be disabled to do not allow select the record.", default=True)

    @api.depends('code')
    def _compute_display_name(self):
        # OVERRIDE
        for tariff in self:
            tariff.display_name = f"{tariff.code} {tariff.name or ''}"
