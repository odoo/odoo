from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _find_record_check_access(self, record, access_token):
        if record._name == "hr.employee.public":
            return record
        return super()._find_record_check_access(record, access_token)

    def _record_to_stream(self, record, field_name):
        if record._name == "hr.employee.public" and field_name == 'avatar_128':
            record = record.sudo()
        return super()._record_to_stream(record, field_name)
