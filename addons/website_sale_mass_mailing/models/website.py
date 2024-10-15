# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import website_sale


class Website(website_sale.Website):

    newsletter_id = fields.Many2one(string="Newsletter List", comodel_name='mailing.list')
