# Copyright (C) 2020  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import models


class ICMSRelief(models.Model):
    _name = "l10n_br_fiscal.icms.relief"
    _inherit = "l10n_br_fiscal.data.abstract"
    _description = "Tax ICMS Relief"
