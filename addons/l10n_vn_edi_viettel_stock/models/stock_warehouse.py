# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    l10n_vn_edi_sinvoice_symbol_id = fields.Many2one(
        comodel_name='l10n_vn_edi_viettel.sinvoice.symbol',
        string="Default Warehouse Symbol",
        help="Used only for this Warehouse. Leave it blank to use global default symbol.",
    )
    l10n_vn_edi_country_code = fields.Char(
        string="Country",
        related='company_id.country_code',
    )
