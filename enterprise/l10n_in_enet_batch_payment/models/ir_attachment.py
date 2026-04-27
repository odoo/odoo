from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    can_be_deleted = fields.Boolean(string="Can Be Deleted?", default=True)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_payorder_file(self):
        for attachment in self:
            if not attachment.can_be_deleted:
                raise ValidationError(_("You cannot delete a Pay Order once it has been generated."))
