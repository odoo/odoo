# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LinkTrackerClick(models.Model):
    _inherit = "link.tracker.click"

    sms_number = fields.Char("Phone Number", related="mailing_trace_id.sms_number")
