from odoo import fields, models, _
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_in_upi_id = fields.Char(string="UPI Id")
    l10n_in_active_audit_trail = fields.Boolean(string="Audit Trail", default=False, help="Once you activate audit trail it can't be deactivated.")

    def write(self, vals):
        if 'l10n_in_active_audit_trail' in vals:
            for company in self:
                if company.l10n_in_active_audit_trail and not vals['l10n_in_active_audit_trail']:
                    raise UserError(_("Deactivation of Audit Trail will not be allowed as per Government Mandate."))
        return super(ResCompany, self).write(vals)
