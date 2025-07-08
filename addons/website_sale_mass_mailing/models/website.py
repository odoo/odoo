# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    is_newsletter_enabled = fields.Boolean()
    newsletter_id = fields.Many2one(string="Newsletter List", comodel_name='mailing.list')
