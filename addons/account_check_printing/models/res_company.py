# -*- coding: utf-8 -*-

from odoo import models, fields


class res_company(models.Model):
    _inherit = "res.company"

    # This field needs to be overridden with `selection_add` in the modules which intends to add report layouts.
    # The xmlID of all the report actions which are actually Check Layouts has to be kept as key of the selection.
    account_check_printing_layout = fields.Selection(
        string="Check Layout",
        selection=[
            ('disabled', 'None'),
        ],
        default='disabled',
        help="Select the format corresponding to the check paper you will be printing your checks on.\n"
             "In order to disable the printing feature, select 'None'.",
    )
    account_check_printing_date_label = fields.Boolean(
        string='Print Date Label',
        default=True,
        help="This option allows you to print the date label on the check as per CPA.\n"
             "Disable this if your pre-printed check includes the date label.",
    )
    account_check_printing_multi_stub = fields.Boolean(
        string='Multi-Pages Check Stub',
        help="This option allows you to print check details (stub) on multiple pages if they don't fit on a single page.",
    )
    account_check_printing_margin_top = fields.Float(
        string='Check Top Margin',
        default=0.25,
        help="Adjust the margins of generated checks to make it fit your printer's settings.",
    )
    account_check_printing_margin_left = fields.Float(
        string='Check Left Margin',
        default=0.25,
        help="Adjust the margins of generated checks to make it fit your printer's settings.",
    )
    account_check_printing_margin_right = fields.Float(
        string='Right Margin',
        default=0.25,
        help="Adjust the margins of generated checks to make it fit your printer's settings.",
    )
