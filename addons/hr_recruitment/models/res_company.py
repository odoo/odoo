# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import base

from odoo import fields, models


class ResCompany(models.Model, base.ResCompany):

    candidate_properties_definition = fields.PropertiesDefinition('Candidate Properties')
