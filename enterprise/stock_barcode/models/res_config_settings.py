from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    barcode_nomenclature_id = fields.Many2one('barcode.nomenclature', related='company_id.nomenclature_id', readonly=False)
    stock_barcode_demo_active = fields.Boolean("Demo Data Active", compute='_compute_stock_barcode_demo_active')
    show_barcode_nomenclature = fields.Boolean(compute='_compute_show_barcode_nomenclature')
    stock_barcode_mute_sound_notifications = fields.Boolean(
        "Mute Barcode application sounds",
        config_parameter="stock_barcode.mute_sound_notifications",
    )
    barcode_max_time_between_keys_in_ms = fields.Integer(
        "Max time between each key",
        help="Maximum delay between each key in ms (100 ms by default)",
        default=100,
        config_parameter="barcode.max_time_between_keys_in_ms",
    )
    barcode_rfid_batch_time = fields.Integer(
        "RFID Timer", config_parameter="stock_barcode.barcode_rfid_batch_time"
    )
    group_barcode_show_quantity_count = fields.Boolean('Show Quantity to Count', implied_group='stock_barcode.group_barcode_show_quantity_count')
    group_barcode_count_entire_location = fields.Boolean('Count Entire Locations', implied_group='stock_barcode.group_barcode_count_entire_location')
    barcode_separator_regex = fields.Char(
        "Multiscan Separator", config_parameter="stock_barcode.barcode_separator_regex",
        help="This regex is used in the Barcode application to separate individual barcodes when "
        "an aggregate barcode (i.e. single barcode consisting of multiple barcode encodings) is scanned.")

    @api.depends('company_id')
    def _compute_show_barcode_nomenclature(self):
        barcode_nomenclature_count = self.env['barcode.nomenclature'].search_count([])
        for rec in self:
            rec.show_barcode_nomenclature = rec.module_stock_barcode and barcode_nomenclature_count > 1

    @api.depends('company_id')
    def _compute_stock_barcode_demo_active(self):
        for rec in self:
            rec.stock_barcode_demo_active = bool(self.env['ir.module.module'].search([('name', '=', 'stock_barcode'), ('demo', '=', True)]))
