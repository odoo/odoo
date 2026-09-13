from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ldaps = fields.One2many(
        comodel_name="res.company.ldap",
        inverse_name="company",
        string="LDAP Parameters",
        copy=True,
        groups="base.group_system",
    )
