from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _find_record_check_access(self, record, access_token):
        if record._name == "slide.slide":
            record.check_access_rights('read')
            record.check_access_rule('read')
        return super()._find_record_check_access(record, access_token)
