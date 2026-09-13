from odoo import _, api, fields, models


class L10nInEwaybillType(models.Model):
    _name = "l10n.in.ewaybill.type"
    _description = "E-Waybill Document Type"

    name = fields.Char(string="Type")
    code = fields.Char(string="Type Code")
    sub_type = fields.Char(string="Sub-type")
    sub_type_code = fields.Char(string="Sub-type Code")
    allowed_supply_type = fields.Selection(
        selection=[
            ("both", "Incoming and Outgoing"),
            ("out", "Outgoing"),
            ("in", "Incoming"),
        ],
        string="Allowed for supply type",
    )
    active = fields.Boolean(default=True)

    @api.depends("sub_type")
    def _compute_display_name(self):
        """Show name and sub_type in name"""
        for ewaybill_type in self:
            ewaybill_type.display_name = _(
                "%(name)s (Sub-Type: %(type)s)",
                name=ewaybill_type.name,
                type=ewaybill_type.sub_type,
            )
