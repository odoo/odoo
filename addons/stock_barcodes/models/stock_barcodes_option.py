# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class StockBarcodesOptionGroup(models.Model):
    _name = "stock.barcodes.option.group"
    _description = "Options group for barcode interface"

    name = fields.Char()
    code = fields.Char()
    option_ids = fields.One2many(
        comodel_name="stock.barcodes.option", inverse_name="option_group_id", copy=True
    )
    barcode_guided_mode = fields.Selection(
        [("guided", "Guided")],
        string="Mode",
        help="When guided mode is selected, information will appear with the "
        "movement to be processed",
    )
    manual_entry = fields.Boolean(
        string="Manual entry",
        help="Default value when open scan interface",
    )
    manual_entry_field_focus = fields.Char(
        help="Set field to set focus when manual entry mode is enabled",
        default="location_id",
    )
    confirmed_moves = fields.Boolean(
        string="Confirmed moves",
        help="It allows to work with movements without reservation "
        "(Without detailed operations)",
    )
    show_pending_moves = fields.Boolean(
        string="Show pending moves", help="Shows a list of movements to process"
    )
    source_pending_moves = fields.Selection(
        [("move_line_ids", "Detailed operations"), ("move_ids", "Operations")],
        default="move_line_ids",
        help="Origin of the data to generate the movements to process",
    )
    ignore_filled_fields = fields.Boolean(
        string="Ignore filled fields",
    )
    auto_put_in_pack = fields.Boolean(
        string="Auto put in pack", help="Auto put in pack before picking validation"
    )
    is_manual_qty = fields.Boolean(
        help="If it is checked, it always shows the product quantity field in edit mode"
    )
    is_manual_confirm = fields.Boolean(
        help="If it is marked, the movement must always be confirmed from a button"
    )
    allow_negative_quant = fields.Boolean(
        help="If it is checked, it will allow the creation of movements that "
        "generate negative stock"
    )
    fill_fields_from_lot = fields.Boolean(
        help="If checked, the fields in the interface will be filled from "
        "the scanned lot"
    )
    ignore_quant_location = fields.Boolean(
        help="If it is checked, quant location will be ignored when reading lot/package",
    )
    group_key_for_todo_records = fields.Char(
        help="You can establish a list of fields that will act as a grouping "
        "key to generate the movements to be process.\n"
        "The object variable is used to refer to the source record\n"
        "For example, object.location_id,object.product_id,object.lot_id"
    )
    auto_lot = fields.Boolean(
        string="Get lots automatically",
        help="If checked the lot will be set automatically with the same "
        "removal startegy",
    )
    create_lot = fields.Boolean(
        string="Create lots if not match",
        help="If checked the lot will created automatically with the scanned barcode "
        "if not exists ",
    )
    show_detailed_operations = fields.Boolean(
        help="If checked the picking detailed operations are displayed",
    )
    keep_screen_values = fields.Boolean(
        help="If checked the wizard values are kept until the pending move is completed",
    )
    accumulate_read_quantity = fields.Boolean(
        help="If checked quantity will be accumulated to the existing record instead of "
        "overwrite it with the new quantity value",
    )
    display_notification = fields.Boolean(
        string="Display Odoo notifications",
    )
    use_location_dest_putaway = fields.Boolean(
        string="Use location dest. putaway",
    )
    location_field_to_sort = fields.Selection(
        selection=[
            ("location_id", "Origin Location"),
            ("location_dest_id", "Destination Location"),
        ]
    )
    display_read_quant = fields.Boolean(string="Read items on inventory mode")

    def get_option_value(self, field_name, attribute):
        option = self.option_ids.filtered(lambda op: op.field_name == field_name)[:1]
        return option[attribute]


class StockBarcodesOption(models.Model):
    _name = "stock.barcodes.option"
    _description = "Options for barcode interface"
    _order = "step, sequence, id"

    sequence = fields.Integer(default=100)
    name = fields.Char()
    option_group_id = fields.Many2one(
        comodel_name="stock.barcodes.option.group", ondelete="cascade"
    )
    field_name = fields.Char()
    filled_default = fields.Boolean()
    forced = fields.Boolean()
    to_scan = fields.Boolean()
    required = fields.Boolean()
    clean_after_done = fields.Boolean()
    message = fields.Char()
    step = fields.Integer()
