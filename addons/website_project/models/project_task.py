# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Need this field to check there is no email loops when Odoo reply automatically
    email_from = fields.Char('Email From')
