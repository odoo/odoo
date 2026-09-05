import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.l10n_tr_nilvera_einvoice.const import (
    GIB_INVOICE_SCENARIO_SELECTION,
    GIB_INVOICE_TYPE_SELECTION,
    GIB_RETURN_INVOICE_TYPES,
)

SEQUENCE_NAME_REGEX = re.compile(r"[0-9A-Z]{3}")


class L10nTrNilveraEinvoiceInvoiceSequence(models.Model):
    _name = "l10n_tr_nilvera_einvoice.invoice.sequence"
    _description = "Turkish e-Document Invoice Sequence"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(related='journal_id.company_id', store=True)
    journal_type = fields.Selection(related='journal_id.type')
    name = fields.Char(
        string="Code",
        size=3,
        required=True,
        help="The series code used in place of the journal code when numbering the invoice, "
        "e.g. 'EXP' produces EXP/2026/00001. This is also the series registered with Nilvera, "
        "which requires exactly 3 uppercase letters or digits.",
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer Name",
        help="Restrict this series to a single customer. Leave empty to apply it to every customer.",
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        string="Account Name",
        domain="""[
            ('account_type', 'in', ['asset_receivable', 'liability_payable']),
            ('company_ids', 'parent_of', company_id),
        ]""",
        help="Restrict this series to partners whose receivable account, or payable account on "
        "vendor documents, is this one. Leave empty to apply it whatever their account.",
    )
    l10n_tr_nilvera_customer_status = fields.Selection(
        selection=[
            ('not_checked', "Not Verified"),
            ('earchive', "E-Archive"),
            ('einvoice', "E-Invoice"),
        ],
        compute='_compute_l10n_tr_nilvera_customer_status',
        store=True,
        readonly=False,
        string="Customer Status",
        help="Restrict this series to partners with this Nilvera status. Selecting a customer "
        "fills it in from that customer. Leave both empty to apply the series whatever the "
        "partner's status.",
    )
    l10n_tr_gib_invoice_scenario = fields.Selection(
        selection=GIB_INVOICE_SCENARIO_SELECTION,
        compute='_compute_l10n_tr_gib_invoice_scenario',
        store=True,
        readonly=False,
        string="Invoice Scenario",
        help="The invoice must use this scenario for the series to apply. Leave it empty to "
        "apply the series whatever the scenario. It does not apply to product export invoices "
        "or to e-Archive customers, so it is cleared and ignored on those series.",
    )
    l10n_tr_gib_invoice_type = fields.Selection(
        selection=GIB_INVOICE_TYPE_SELECTION,
        compute='_compute_l10n_tr_gib_invoice_type',
        store=True,
        readonly=False,
        string="Invoice Type",
        help="The invoice must use this GİB type for the series to apply. Leave it empty to apply "
        "the series whatever the type. Product export invoices are always Tax Exempt by "
        "regulation, and vendor bills have no GİB invoice type, so it is set or cleared "
        "accordingly.",
    )
    l10n_tr_is_export_invoice = fields.Boolean(
        string="Product Export Invoice",
        help="When set, the series only applies to product export invoices.",
    )
    l10n_tr_is_credit_note = fields.Boolean(
        compute='_compute_l10n_tr_is_credit_note',
        store=True,
        readonly=False,
        string="Credit Note",
        help="When set, the series only applies to credit notes and vendor refunds, otherwise "
        "only to invoices and bills. It is only a choice on purchase journals: elsewhere the "
        "GİB Invoice Type already says it, a Return type reversing an earlier invoice.",
    )
    l10n_tr_scenario_applies = fields.Boolean(compute='_compute_l10n_tr_scenario_applies')
    l10n_tr_invoice_type_applies = fields.Boolean(compute='_compute_l10n_tr_invoice_type_applies')

    _name_journal_uniq = models.Constraint(
        "UNIQUE(journal_id, name)",
        "A journal cannot have two e-Document sequences with the same code.",
    )

    @api.depends('journal_type', 'l10n_tr_is_export_invoice', 'l10n_tr_nilvera_customer_status')
    def _compute_l10n_tr_scenario_applies(self):
        for record in self:
            record.l10n_tr_scenario_applies = (
                record.journal_type != 'purchase'
                and not record.l10n_tr_is_export_invoice
                and record.l10n_tr_nilvera_customer_status == 'einvoice'
            )

    @api.depends('journal_type', 'l10n_tr_is_export_invoice')
    def _compute_l10n_tr_invoice_type_applies(self):
        for record in self:
            record.l10n_tr_invoice_type_applies = (
                record.journal_type != 'purchase' and not record.l10n_tr_is_export_invoice
            )

    @api.depends('l10n_tr_scenario_applies')
    def _compute_l10n_tr_gib_invoice_scenario(self):
        for record in self:
            if record.l10n_tr_scenario_applies:
                record.l10n_tr_gib_invoice_scenario = record._origin.l10n_tr_gib_invoice_scenario
            else:
                record.l10n_tr_gib_invoice_scenario = False

    @api.depends('l10n_tr_invoice_type_applies', 'l10n_tr_is_export_invoice')
    def _compute_l10n_tr_gib_invoice_type(self):
        for record in self:
            if record.l10n_tr_invoice_type_applies:
                record.l10n_tr_gib_invoice_type = record._origin.l10n_tr_gib_invoice_type
            else:
                record.l10n_tr_gib_invoice_type = 'ISTISNA' if record.l10n_tr_is_export_invoice else False

    @api.depends('journal_type', 'l10n_tr_gib_invoice_type')
    def _compute_l10n_tr_is_credit_note(self):
        for record in self:
            if record.journal_type == 'purchase':
                record.l10n_tr_is_credit_note = record._origin.l10n_tr_is_credit_note
            else:
                record.l10n_tr_is_credit_note = record.l10n_tr_gib_invoice_type in GIB_RETURN_INVOICE_TYPES

    @api.depends('partner_id')
    def _compute_l10n_tr_nilvera_customer_status(self):
        for record in self:
            if record.partner_id:
                record.l10n_tr_nilvera_customer_status = record.partner_id.l10n_tr_nilvera_customer_status
            else:
                record.l10n_tr_nilvera_customer_status = record._origin.l10n_tr_nilvera_customer_status

    @api.constrains(
        'journal_id',
        'partner_id',
        'l10n_tr_nilvera_customer_status',
        'l10n_tr_gib_invoice_scenario',
        'l10n_tr_gib_invoice_type',
        'l10n_tr_is_export_invoice',
    )
    def _check_conditions_apply(self):
        """Reject conditions that contradict what GİB or the customer already determine.

        The computes keep the form consistent, but a value passed explicitly at create time
        bypasses the computes, so this constraints makes sure the data is consistent.
        """
        for record in self:
            if record.partner_id and record.l10n_tr_nilvera_customer_status != record.partner_id.l10n_tr_nilvera_customer_status:
                raise ValidationError(self.env._(
                    "The e-Document sequence %(name)s sets a Customer Status that does not match "
                    "its customer. Leave it empty: it is taken from the customer.",
                    name=record.name,
                ))
            if record.l10n_tr_gib_invoice_scenario and not record.l10n_tr_scenario_applies:
                raise ValidationError(self.env._(
                    "The e-Document sequence %(name)s sets an Invoice Scenario, which only "
                    "applies to e-Invoice customers on a sales journal. Vendor bills, product "
                    "export invoices and e-Archive customers have no GİB scenario.",
                    name=record.name,
                ))
            if not record.l10n_tr_invoice_type_applies:
                expected = 'ISTISNA' if record.l10n_tr_is_export_invoice else False
                if record.l10n_tr_gib_invoice_type != expected:
                    raise ValidationError(self.env._(
                        "The e-Document sequence %(name)s must leave its GIB Invoice Type empty "
                        "on a purchase journal, and set it to Tax Exempt on a product export "
                        "series, as required by the regulation.",
                        name=record.name,
                    ))

    @api.constrains('name')
    def _check_name(self):
        for record in self:
            if not record.name or not SEQUENCE_NAME_REGEX.fullmatch(record.name):
                raise ValidationError(self.env._(
                    "The e-Document sequence %(name)s must be exactly 3 characters long and contain "
                    "only uppercase letters and digits, because Nilvera expects invoice numbers in "
                    "the format ABC/2025/00001.",
                    name=record.name,
                ))

    def _l10n_tr_specificity_key(self):
        """Get the sort key ranking this series against the others matching the same document.

        :return: the conditions this series pins, most significant first.
        """
        self.ensure_one()
        return (
            bool(self.partner_id),
            bool(self.account_id),
            bool(self.l10n_tr_nilvera_customer_status),
            bool(self.l10n_tr_gib_invoice_scenario),
            bool(self.l10n_tr_gib_invoice_type),
        )

    def _l10n_tr_matches_move(self, move):
        """Check whether this series applies to a document.

        :param move: the account.move to test this series against.
        :return: whether every condition of the series holds for that document.
        """
        self.ensure_one()
        return (
            (not self.partner_id or self.partner_id == move.partner_id)
            and (
                not self.account_id
                or self.account_id == move._l10n_tr_get_partner_control_account()
            )
            and (
                not self.l10n_tr_nilvera_customer_status
                or self.l10n_tr_nilvera_customer_status == move.l10n_tr_nilvera_customer_status
            )
            and (
                not self.l10n_tr_scenario_applies
                or not self.l10n_tr_gib_invoice_scenario
                or self.l10n_tr_gib_invoice_scenario == move.l10n_tr_gib_invoice_scenario
            )
            and (
                not self.l10n_tr_invoice_type_applies
                or not self.l10n_tr_gib_invoice_type
                or self.l10n_tr_gib_invoice_type == move.l10n_tr_gib_invoice_type
            )
            and self.l10n_tr_is_export_invoice == move.l10n_tr_is_export_invoice
            and self.l10n_tr_is_credit_note == (move.move_type in {'out_refund', 'in_refund'})
        )
