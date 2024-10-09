# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    # The classification is too precise to be able to do any kind of guessing, so we need it set.
    # See https://docs.peppol.eu/poac/sg/2024-Q2/pint-sg/bis/#_goods_and_services_tax_gst
    ubl_cii_tax_category_code = fields.Selection(
        selection_add=[
            ('SR', "SG - Local supply of goods and services"),
            ('SRCA-S', "SG - Customer accounting supply made by the supplier"),
            ('SRCA-C', "SG - Customer accounting supply made by the customer on supplier’s behalf"),
            ('SROVR-RS', "SG - Supply of remote services accountable by the electronic marketplace under the Overseas Vendor Registration Regime"),
            ('SROVR-LVG', "SG - Supply of low-value goods accountable by the redeliverer or electronic marketplace on behalf of third-party suppliers"),
            ('SRLVG', "SG - Own supply of low-value goods"),
            ('ZR', "SG - Supplies involving goods for export/ provision of international services"),
            ('ES33', "SG - Specific categories of exempt supplies listed under regulation 33 of the GST (General) Regulations"),
            ('ESN33', "SG - Exempt supplies other than those listed under regulation 33 of the GST (General) Regulations"),
            ('DS', "SG - Supplies required to be reported pursuant to the GST legislation"),
            ('OS', "SG - Supplies outside the scope of the GST Act"),
            ('NG', "SG - Supplies from a company which is not registered for GST"),
            ('NA', "SG - Taxable supplies where GST need not be charged"),
        ],
    )
