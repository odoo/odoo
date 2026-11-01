# -*- coding: utf-8 -*-
"""ทะเบียนทรัพย์สิน — Odoo 19 port of the legacy ``asset_card_report``.

Legacy source: ``dtr_fixed_assets_report/report/asset_card_report.py``
(model ``asset.card.report``).  A multi-asset listing scoped by an optional
asset-reference (``asset.code``) range.

Odoo 19 adaptations applied to ``jrxml/asset_card_report.jrxml``:

* ``account_asset_asset`` -> ``account_asset``.
* ``res_currency.currency_unit_label_en`` (column removed) -> ``res_currency.name``.
* ``company_address_header_report.company_name_thai`` / ``_en`` -> ``res_company.name``.
* ``account_asset_depreciation_line.depreciation_date`` ->
  ``account_asset_line.line_date``.
* ``serial_no`` / ``warranty`` / ``freight_charge`` / ``transportation_charge`` /
  ``installation_charge`` / ``other_expenses`` / ``initial_depreciation`` print as
  literals (the corresponding legacy custom fields are gone).

The wizard avoids any dependency on ``account_asset_management``: the scope is
expression by plain Char reference bounds, not by a Many2one to ``account.asset``.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class AssetCardReport(models.TransientModel):
    _name = "asset.card.report"
    _description = "Asset Card Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Asset Card Report")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Language",
        default="thai",
        required=True,
    )
    date_type = fields.Selection(
        [("AD", "AD"), ("BE", "BE")],
        string="Date Type",
        default="AD",
        required=True,
        help="AD = คริสตศักราช\nBE = พุทธศักราช",
    )
    date_format = fields.Selection(
        [(value, value) for value in DATE_FORMATS],
        string="Date Format",
        default="dd-MM-yyyy",
        required=True,
    )
    p_from_reference = fields.Char(string="From Reference")
    p_to_reference = fields.Char(string="To Reference")

    def get_locale(self):
        """Faithful to the legacy ``asset_card_report.get_locale()``."""
        return "en_EN"

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        where = "WHERE asset.state != 'draft'"
        references = []
        if self.p_from_reference:
            references.append(self.p_from_reference)
            where += " AND asset.code >= '%s'" % self.p_from_reference.replace("'", "''")
        if self.p_to_reference:
            references.append(self.p_to_reference)
            where += " AND asset.code <= '%s'" % self.p_to_reference.replace("'", "''")
        if references:
            reference_display = " - ".join(references)
        else:
            reference_display = "All" if self.p_language == "english" else "ทั้งหมด"
        self.name = "Asset Card Report"
        return {
            "p_Print_By": self._legacy_print_by(),
            "p_Where": where,
            "p_DateFormat": str(self.date_format),
            "p_language": self.p_language,
            "p_reference_display": reference_display,
            "p_locale": "th" if self.date_type == "BE" else "en",
        }
