from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_pe_operation_type = fields.Selection(
        [
            ('1', 'National Sale'),
            ('2', 'National Purchase'),
            ('3', 'Consignation Received'),
            ('4', 'Consignation Delivered'),
            ('5', 'Return Received'),
            ('6', 'Return Delivered'),
            ('7', 'Bonus'),
            ('8', 'Prize'),
            ('9', 'Donation'),
            ('10', 'Production Output'),
            ('11', 'Transfer Between Warehouses'),
            ('12', 'Withdrawal'),
            ('13', 'Shrinkage'),
            ('14', 'Deterioration'),
            ('15', 'Destruction'),
            ('16', 'Opening Balance'),
            ('17', 'Export'),
            ('18', 'Import'),
            ('19', 'Production Entry'),
            ('20', 'Return from Production'),
            ('21', 'Transfer Entry Between Warehouses'),
            ('22', 'Entry for Misidentification'),
            ('23', 'Output for Misidentification'),
            ('24', 'Entry from Customer Return'),
            ('25', 'Return to Supplier'),
            ('26', 'Entry for Production Service'),
            ('27', 'Output for Production Service'),
            ('28', 'Adjustment for Inventory Difference'),
            ('29', 'Loan Goods Entry'),
            ('30', 'Loan Goods Exit'),
            ('31', 'Custody Goods Entry'),
            ('32', 'Custody Goods Exit'),
            ('33', 'Medical Samples'),
            ('34', 'Advertising'),
            ('35', 'Representation Expenses'),
            ('36', 'Withdrawal for Workers Delivery'),
            ('37', 'Collective Agreement Withdrawal'),
            ('38', 'Withdrawal for Replacement of Damaged Goods'),
            ('91', 'Others 1'),
            ('92', 'Others 2'),
            ('93', 'Others 3'),
            ('94', 'Others 4'),
            ('95', 'Others 5'),
            ('96', 'Others 6'),
            ('97', 'Others 7'),
            ('98', 'Others 8'),
            ('99', 'Others'),
        ],
        string='Type of Operation (PE)',
        compute='_compute_l10n_pe_operation_type',
        store=True,
        readonly=False,
        help="Select the type of operation performed according to SUNAT's Table 12 for permanent inventory reporting.",
    )

    @api.depends('picking_type_id')
    def _compute_l10n_pe_operation_type(self):
        for record in self.filtered(lambda picking: picking.country_code == 'PE'):
            record.l10n_pe_operation_type = {'outgoing': '1', 'incoming': '2', 'internal': '21'}.get(record.picking_type_code)
