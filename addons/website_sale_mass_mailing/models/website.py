# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import website

from odoo import fields, models


class Website(models.Model, website.Website):

    newsletter_id = fields.Many2one(string="Newsletter List", comodel_name='mailing.list')
