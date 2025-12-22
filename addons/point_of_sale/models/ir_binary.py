from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _find_record_check_access(self, record, access_token, field):
        if record._name == "product.product" and field == "image_128":
            return record.sudo()
        return super()._find_record_check_access(record, access_token, field)
