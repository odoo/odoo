# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    # The classification is too precise to be able to do any kind of guessing, so we need it set.
    # See https://docs.peppol.eu/poac/sg/pint-sg/trn-invoice/codelist/Aligned-TaxCategoryCodes/
    ubl_cii_tax_category_code = fields.Selection(
        selection_add=[
            ('SR', "SR - Local supply of goods and services"),
            ('SRCA-S', "SRCA-S - Customer accounting supply made by the supplier"),
            ('SRCA-C', "SRCA-C - Customer accounting supply made by the customer on supplier's behalf"),
            ('SROVR-RS', "SROVR-RS - Supply of remote services accountable by the electronic marketplace under the Overseas Vendor Registration Regime"),
            ('SROVR-LVG', "SROVR-LVG - Supply of low-value goods accountable by the redeliverer or electronic marketplace on behalf of third-party suppliers"),
            ('SRRC', "SRRC - Reverse charge regime for Business-to-Business (\"B2B\") supplies of imported services"),
            ('SRLVG', "SRLVG - Own supply of low-value goods"),
            ('NA', "NA - Taxable supplies where GST need not be charged"),
            ('ZR', "ZR - Supplies involving goods for export/ provision of international services"),
            ('ES33', "ES33 - Specific categories of exempt supplies listed under regulation 33 of the GST (General) Regulations"),
            ('ESN33', "ESN33 - Exempt supplies other than those listed under regulation 33 of the GST (General) Regulations"),
            ('DS', "DS - Supplies required to be reported pursuant to the GST legislation"),
            ('OS', "OS - Supplies outside the scope of the GST Act"),
            ('NG', "NG - Supplies from a company which is not registered for GST"),
            ('TX', "TX - Standard-rated taxable purchase"),
            ('TXCA', "TXCA - Standard-rated purchases of prescribed goods subject to customer accounting"),
            ('TXNA', "TXNA - Purchases made under specific GST schemes, such as Gross Margin Scheme (\"GMS\"), Approved Marine Fuel Trader (\"AMFT\") Scheme, Approved 3rd Party Logistics (\"A3PL\") Scheme"),
            ('ZP', "ZP - Zero-rated purchases"),
            ('IM', "IM - Import of goods (9% GST paid to Singapore Customs on the import of goods into Singapore)"),
            ('ME', "ME - Import of goods under the Major Exporter Scheme (\"MES\"), A3PL Scheme or other approved schemes"),
            ('IGDS', "IGDS - Import of goods under the Import GST Deferment Scheme (\"IGDS\")"),
            ('BL', "BL - Disallowed expenses"),
            ('NR', "NR - Purchases received from non-GST registered suppliers"),
            ('EP', "EP - Exempt purchases"),
            ('OP', "OP - Out-of-scope purchases received from GST-registered suppliers"),
            ('TXRC-TS', "TXRC-TS - Imported services and LVG claimable by the GST-registered customer under reverse charge"),
            ('TX-ESS', "TX-ESS - Standard-rated purchases directly attributable to Regulation 33 exempt supplies"),
            ('TXRC-ESS', "TXRC-ESS - Imported services and LVG claimable by the GST-registered customer under reverse charge that are directly attributable to Regulation 33 exempt supplies"),
            ('IM-ESS', "IM-ESS - Import of goods with GST paid to Singapore Customs that are directly attributable to Regulation 33 exempt supplies"),
            ('TX-N33', "TX-N33 - Standard-rated purchases directly attributable to non-Regulation 33 exempt supplies"),
            ('TXRC-N33', "TXRC-N33 - Imported services and LVG claimable by the GST-registered customer under reverse charge that are directly attributable to non-Regulation 33 exempt supplies"),
            ('IM-N33', "IM-N33 - Import of goods with GST paid to Singapore Customs that are directly attributable to non-Regulation 33 exempt supplies"),
            ('TX-RE', "TX-RE - Purchases from GST-registered suppliers that are subject to GST and are either attributable to the making of both taxable and exempt supplies or incurred for the overall running of the business"),
            ('TXRC-RE', "TXRC-RE - Imported services and LVG claimable by the GST-registered customer under reverse charge that are residual"),
            ('TX-LVG', "TX-LVG - Purchase of low-value goods subject to GST"),
            ('IM-RE', "IM-RE - Import of goods with GST paid to Singapore Customs that are residual"),
        ],
    )
