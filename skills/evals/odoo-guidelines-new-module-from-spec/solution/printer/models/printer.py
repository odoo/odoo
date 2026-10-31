from odoo import api, models, fields


class Printer(models.Model):
    _name = "printer.printer"
    _description = "External Printer"

    name = fields.Char(required=True)
    ip_address = fields.Char(string="IP Address")
    report_ids = fields.Many2many("ir.actions.report", string="Linked Reports")
    type = fields.Selection([
            ("zpl", "ZPL"),
            ('epos', 'ePOS'),
        ],
        default="zpl", required=True, string="Type"
    )

    @api.depends('name', 'type')
    @api.depends_context('formatted_display_name')
    def _compute_display_name(self):
        for printer in self:
            type_label = next(label for value, label in printer._fields["type"].selection if value == printer.type)
            if printer.env.context.get("formatted_display_name"):
                printer.display_name = f"{type_label} - {printer.name}"
            else:
                printer.display_name = printer.name
