from odoo import fields, models


class IrExports(models.Model):
    _name = "ir.exports"
    _description = "Exports"
    _order = "name, id"

    name = fields.Char(string="Export Name")
    resource = fields.Char(index=True)
    export_fields = fields.One2many(
        comodel_name="ir.exports.line",
        inverse_name="export_id",
        string="Fields to Export",
        copy=True,
    )


class IrExportsLine(models.Model):
    _name = "ir.exports.line"
    _description = "Exports Line"
    _order = "id"

    name = fields.Char(string="Field Name")
    export_id = fields.Many2one(
        comodel_name="ir.exports",
        index=True,
        ondelete="cascade",
    )
