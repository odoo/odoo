# -*- coding: utf-8 -*-

from openerp import fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    ldaps = fields.One2many('res.company.ldap', 'company', string='LDAP Parameters', copy=True, groups="base.group_system")