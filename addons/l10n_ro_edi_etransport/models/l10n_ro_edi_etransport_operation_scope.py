from odoo import fields, models


class L10nRoETransportOperationScope(models.Model):
    _name = 'l10n_ro.edi.etransport.operation.scope'
    _description = "eTransport Operation Scope"

    code = fields.Char(required=True)
    name = fields.Char(required=True, translate=True)
