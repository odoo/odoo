# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    double_check_on_web_service = fields.Boolean(
        "Double Check",
        help="Tick this if you need EDI web service confrim before call\n"
        "This is use full when EDI web service is not accepting re-submition or it's chargeable :p \n"
        "So before submit invoice to goverment user confrim it.\n",
    )
