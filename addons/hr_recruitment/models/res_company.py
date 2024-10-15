# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import hr


class ResCompany(hr.ResCompany):

    candidate_properties_definition = fields.PropertiesDefinition('Candidate Properties')
    job_properties_definition = fields.PropertiesDefinition("Job Properties")
