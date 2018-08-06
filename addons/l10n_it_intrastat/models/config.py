

from openerp import models, fields, api


class res_company(models.Model):
    _inherit = 'res.company'

    intrastat_uom_kg_id = fields.Many2one(
        'product.uom', string="Unit of measure for Kg",
        )
    intrastat_additional_unit_from = fields.Selection(
        [('quantity', 'Quantity'),('weight', 'Weight'),('none', 'None')],
        string='Additional Unit of Measure FROM', default='weight')
    intrastat_exclude_free_line = fields.Boolean(string='Exclude Free lines')
    intrastat_ua_code = fields.Char(string="User ID (UA Code)", size=4)
    intrastat_delegated_vat = fields.Char(string="Delegated person VAT",
                                          size=16)
    intrastat_delegated_name = fields.Char(string="Delegated person", size=255)
    intrastat_export_file_name = fields.Char(string="File name for export")

    ### default values sale section
    intrastat_sale_statistic_amount = fields.Boolean(
        string='Force Statistic Amount Euro')
    intrastat_sale_transation_nature_id = fields.Many2one(
        'account.intrastat.transation.nature', string='Transation Nature')
    intrastat_sale_delivery_code_id = fields.Many2one(
        'stock.incoterms', string='Delivery')
    intrastat_sale_transport_code_id = fields.Many2one(
        'account.intrastat.transport', string='Transport')
    intrastat_sale_province_origin_id = fields.Many2one(
        'res.country.state', string='Province Origin')

    ### default values purchase section
    intrastat_purchase_statistic_amount = fields.Boolean(
        string='Force Statistic Amount Euro')
    intrastat_purchase_transation_nature_id = fields.Many2one(
        'account.intrastat.transation.nature', string='Transation Nature')
    intrastat_purchase_delivery_code_id = fields.Many2one(
        'stock.incoterms', string='Delivery')
    intrastat_purchase_transport_code_id = fields.Many2one(
        'account.intrastat.transport', string='Transport')
    intrastat_purchase_province_destination_id = fields.Many2one(
        'res.country.state', string='Province Destination')
    intrastat_min_amount = fields.Float(
        string="Min amount", help="In case of invoices < 'min amount', use min"
                                  " amount in intrastat statement",
        default=1
    )
