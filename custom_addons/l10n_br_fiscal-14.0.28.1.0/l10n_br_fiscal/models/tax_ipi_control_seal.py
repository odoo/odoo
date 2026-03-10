# Copyright (C) 2020  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import models


class TaxIpiControlSeal(models.Model):
    _name = "l10n_br_fiscal.tax.ipi.control.seal"
    _description = "IPI Control Seal"
    _inherit = "l10n_br_fiscal.data.abstract"
