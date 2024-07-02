from odoo import fields, models


class L10nRoETransportCustoms(models.Model):
    _name = 'l10n_ro.edi.etransport.customs'
    _description = "eTransport customs"

    code = fields.Char(required=True)
    name = fields.Char(required=True)
