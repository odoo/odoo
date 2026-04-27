# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Employee(models.Model):
    _inherit = "hr.employee"

    l10n_id_kode_ptkp = fields.Selection(
        selection=[
            ('tk0', "TK/0"),
            ('tk1', "TK/1"),
            ('tk2', "TK/2"),
            ('tk3', "TK/3"),
            ('k0', "K/0"),
            ('k1', "K/1"),
            ('k2', "K/2"),
            ('k3', "K/3")],
        string="PTKP Code",
        default="tk0",
        required=True,
        groups="hr.group_hr_user",
        help="Employee's tax category that depends on their marital status and number of children")
