# Copyright (C) 2020  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import models


class TaxIpiGuidelineClass(models.Model):
    _name = "l10n_br_fiscal.tax.ipi.guideline.class"
    _description = "IPI Guidelines Class"
    _inherit = "l10n_br_fiscal.data.abstract"
