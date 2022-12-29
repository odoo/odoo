from odoo import api, fields, models


class ExceptionReason(models.Model):
    _name = 'l10n_tr.exception_reason'
    _description = 'Tax exemption/withdrawal reason'

    name = fields.Char()
    code = fields.Char()

    @api.depends('code', 'name')
    def name_get(self):
        return [(reason.id, "%s - %s" % (reason.code, reason.name)) for reason in self]
