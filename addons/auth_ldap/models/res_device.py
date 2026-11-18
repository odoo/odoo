from odoo import fields, models


class ResSession(models.Model):
    _inherit = 'res.session'

    auth_method = fields.Selection(selection_add=[('ldap', 'LDAP')])
