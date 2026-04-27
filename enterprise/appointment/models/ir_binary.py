from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _find_record_check_access(self, record, access_token, field):
        """ Give the public users access to the unpublished appointment types images when they have an invitation link. """
        if record._name == 'appointment.type' and field in ['image_%s' % size for size in [1920, 1024, 512, 256, 128]]:
            return record.sudo()
        return super()._find_record_check_access(record, access_token, field=field)
