#    Copyright (C) 2016 MultidadosTI (http://www.multidadosti.com.br)
#    @author Michell Stuttgart <michellstut@gmail.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class ResBank(models.Model):
    _inherit = "res.bank"

    short_name = fields.Char()

    code_bc = fields.Char(
        string="Brazilian Bank Code",
        size=3,
        help="Brazilian Bank Code ex.: 001 is the code of Banco do Brasil",
    )

    ispb_number = fields.Char(
        string="ISPB Number",
        size=8,
    )

    compe_member = fields.Boolean(
        string="COMPE Member",
        default=False,
    )
