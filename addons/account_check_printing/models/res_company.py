# -*- coding: utf-8 -*-

from openerp import models, api, fields

class res_company(models.Model):
    _inherit = "res.company"

    account_check_printing_layout = fields.Selection(string="Check Layout", required=True,
        help="Select the format corresponding to the check paper you will be printing your checks on.\n"
             "In order to disable the printing feature, select 'None'.",
        selection=[
            ('disabled', 'None'),
            ('action_print_check_top', 'check on top'),
            ('action_print_check_middle', 'check in middle'),
            ('action_print_check_bottom', 'check on bottom')
        ],
        default="action_print_check_top")

    account_check_printing_date_label = fields.Boolean('Print Date Label', default=True,
        help="This option allows you to print the date label on the check as per CPA. Disable this if your pre-printed check includes the date label.")

    account_check_printing_multi_stub = fields.Boolean('Multi-Pages Check Stub',
        help="This option allows you to print check details (stub) on multiple pages if they don't fit on a single page.")

    account_check_printing_margin_top = fields.Float('Check Top Margin', default=0.25,
        help="Adjust the margins of generated checks to make it fit your printer's settings.")

    account_check_printing_margin_left = fields.Float('Check Left Margin', default=0.25,
        help="Adjust the margins of generated checks to make it fit your printer's settings.")

    account_check_printing_margin_right = fields.Float('Right Margin', default=0.25,
        help="Adjust the margins of generated checks to make it fit your printer's settings.")
