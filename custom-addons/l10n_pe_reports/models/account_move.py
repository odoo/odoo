# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_pe_detraction_date = fields.Date(
        string="Detraction Date",
        copy=False,
        help="Indicate the date of issuance of the detraction deposit certificate",
    )
    l10n_pe_detraction_number = fields.Char(
        string="Detraction", copy=False, help="Indicate the number of issuance of the detraction deposit certificate"
    )
    l10n_pe_dua_invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="DUA Invoice",
        domain=[
            ("l10n_latam_document_type_id_code", "in", ("50", "52")),
            ("state", "=", "posted"),
        ],
        index='btree_not_null',
        copy=False,
        help="DUA invoice that accredits the tax credit on the importation of goods.",
    )
    l10n_pe_service_modality = fields.Selection(
        selection=[
            ("1", "Service provided entirely in Peru"),
            ("2", "Service provided partly in Peru and part abroad"),
            ("3", "Service provided exclusively abroad"),
        ],
        string="Service Modality",
        help="Indicate the service modality, fill this field if the invoice is for a service. "
        "This will be used on 8.2 report.",
    )
    l10n_pe_usage_type_id = fields.Many2one(
        comodel_name="l10n_pe.ple.usage",
        string="Usage Type",
        help="Service that is reflected in the declared invoice and must be classified according to table 31: Type "
        "of Usage.",
    )
    l10n_pe_sunat_transaction_type = fields.Selection(
        selection=[
            ("opening", "Opening Entry"),
            ("closing", "Closing Entry"),
        ],
        string="PLE Transaction Type",
        help="Please choose the transaction type for the SUNAT reports 5.1, 5.2, and 6.1. It's important to note that "
        "this selection will not impact the account move; its sole purpose is to correctly flag the transaction in "
        "the exported txt file.")

    @api.constrains("l10n_pe_detraction_date", "l10n_pe_detraction_number")
    def _check_l10n_pe_detraction(self):
        for record in self:
            if (record.l10n_pe_detraction_date or record.l10n_pe_detraction_number) and (
                not record.l10n_pe_detraction_date or not record.l10n_pe_detraction_number
            ):
                raise ValidationError(_("If a detraction value is set (date or number), both values must be filled."))
