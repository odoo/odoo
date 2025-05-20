from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _find_record_check_access(self, record, access_token, field):
        if record._name == "slide.slide":
            record.check_access('read')
        return super()._find_record_check_access(record, access_token, field)
