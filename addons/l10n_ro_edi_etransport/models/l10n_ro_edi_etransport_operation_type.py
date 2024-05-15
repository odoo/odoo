from odoo import fields, models


class L10nRoETransportOperationType(models.Model):
    _name = 'l10n_ro.edi.etransport.operation.type'
    _description = "eTransport Operation Type"

    code = fields.Char(required=True)
    name = fields.Char(required=True, translate=True)
