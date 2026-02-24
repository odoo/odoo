# -*- coding: utf-8 -*-

from odoo import models, fields


class Partner(models.Model):
    _inherit = 'res.partner'

    is_owner = fields.Boolean('Owner')
    is_agent_consultant = fields.Boolean('Agent/Consultant')

