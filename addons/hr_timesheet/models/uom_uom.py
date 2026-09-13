from odoo import fields, models


class UomUom(models.Model):
    _inherit = "uom.uom"

    def _unprotected_uom_xml_ids(self):
        return [
            xml_id
            for xml_id in super()._unprotected_uom_xml_ids()
            if xml_id != "product_uom_hour"
        ]

    timesheet_widget = fields.Char(
        string="Widget",
        export_string_translation=False,
    )
