from odoo import models
from odoo.addons import base


class IrBinary(models.AbstractModel, base.IrBinary):

    def _find_record_check_access(self, record, access_token, field):
        if record._name in ["product.product", "pos.category"] and field in ["image_128", "image_512"]:
            return record.sudo()
        return super()._find_record_check_access(record, access_token, field)
