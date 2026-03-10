# Copyright (C) 2025  Marcel Savegnago <https://escodoo.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class OperationIndicator(models.Model):
    """Operation Indicator

    This model stores the Operation Indicators (cIndOp) table according to
    Annex VII of Technical Note No. 004/2025 from NFS-e Nacional, which is
    part of the Brazilian Tax Reform (Reforma Tributária do Consumo).

    The cIndOp field is used in the Service Provision Declaration (DPS)
    to categorize consumption operations, as required by Art. 11 of
    Complementary Law No. 214/2025.

    This table will become mandatory from January 1, 2026.
    """

    _name = "l10n_br_fiscal.operation.indicator"
    _inherit = "l10n_br_fiscal.data.abstract"
    _description = "Operation Indicator"
    _order = "code"

    code = fields.Char(
        string="Operation Indicator Code",
        required=True,
        index=True,
        size=6,
        help="Operation indicator code according to Annex VII of NT 004/2025 "
        "(e.g., 020101, 030101)",
    )

    operation_type = fields.Text(
        required=True,
        help="Type of operation according to Art. 11 of Complementary Law "
        "No. 214/2025",
    )

    operation_location = fields.Text(
        string="Operation Location Consideration",
        help="Where the operation is considered to take place according to "
        "the legislation",
    )

    supply_characteristic = fields.Text(
        help="Specific characteristic of the supply execution that determines "
        "the place of supply",
    )

    supply_location = fields.Text(
        string="DFe Supply Location",
        required=True,
        help="Place of supply to be identified in the Digital Fiscal Document "
        "(DFe), such as supplier establishment, acquirer address, "
        "recipient address, or other locations depending on the operation",
    )
