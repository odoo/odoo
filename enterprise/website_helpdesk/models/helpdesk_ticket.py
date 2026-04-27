# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    partner_company_name = fields.Char(string='Company Name', related='partner_id.company_name', store=True, readonly=False)
