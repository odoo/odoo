from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    peppol_contract_document_reference = fields.Char(
        string="Contract Document Reference",
        help="A reference to the contract document.",
    )
    peppol_project_reference = fields.Char(
        string="Project Reference",
        help="A reference to the project.",
    )
    peppol_originator_document_reference = fields.Char(
        string="Originator Document Reference",
        help="A reference to the document that originated the order.",
    )
    peppol_despatch_document_reference = fields.Char(
        string="Despatch Document Reference",
        help="A reference to the despatch document.",
    )
    peppol_additional_document_reference = fields.Char(
        string="Additional Document Reference",
        help="A reference to an additional supporting document. Only one document can be referenced.",
    )
    peppol_accounting_cost = fields.Char(
        string="Accounting Cost",
        help="A textual description or a code to identify the accounting cost.",
    )
    peppol_delivery_location_id = fields.Char(
        string="Delivery Location GLN",
        help="The Global Location Number (GLN) of the delivery location.",
    )
