# -*- coding: utf-8 -*-
from odoo import fields, models


class View(models.Model):
    _inherit = 'ir.ui.view'

    # add activity view
    type = fields.Selection(selection_add=[('activity', 'Activity')])
    # views used for notification and mailing
    is_mail_template = fields.Boolean("Used as mail template body")
