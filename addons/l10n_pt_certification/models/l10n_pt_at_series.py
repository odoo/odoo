import re

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.exceptions import UserError, ValidationError

AT_SERIES_ACCOUNTING_DOCUMENT_TYPES = [
    ('out_invoice', 'Invoice (FT)'),
    ('out_receipt', 'Simplified Invoice (FS)'),
    ('out_invoice_receipt', 'Invoice/Receipt (FR)'),
    ('out_refund', 'Credit Note (NC)'),
    ('debit_note', 'Debit Note (ND)'),
    ('payment_receipt', 'Payment Receipt (RG)'),
]


class L10nPtATSeries(models.Model):
    """
    This model allows users to add the AT series created in the Portal das Finanças. An AT Series
    """
    _name = "l10n_pt.at.series"
    _description = "Mapping between Odoo Series and the Official Series for the Autoridade Tributária (AT)"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of
    _rec_name = 'document_identifier'

    name = fields.Char(
        required=True,
        help="The name of the series will be part of the document number sequence.",
    )
    training_series = fields.Boolean("Training Series")
    date_start = fields.Date("Start Date", required=True, default=fields.Date.today)
    date_end = fields.Date("End Date")
    active = fields.Boolean(compute='_compute_active', search='_search_active')
    company_exclusive_series = fields.Boolean(
        string="Exclusive Series",
        help="If checked, this series will only be used by one company and not shared across branches",
    )
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    journal_id = fields.Many2one(
        'account.journal',
        help="This series will be available for account moves belonging to this, and only this, journal.",
        check_company=True,
        domain="[('type', 'in', ('sale', 'bank', 'credit', 'cash'))]",
    )

    prefix = fields.Char(
        string="Prefix",
        required=True,
        help="The internal code of the document type that will be combined with the Series Name to form "
             "the unique identification of documents.",
    )
    document_type = fields.Selection(
        string="Document Type",
        selection=AT_SERIES_ACCOUNTING_DOCUMENT_TYPES,
        required=True,
        help="Customer Invoices require an Invoice (FT) series, and Sales Receipts require a Simplified Invoice (FS) series.",
    )
    # Used in _rec_name to display the types of documents within an AT Series (displayed in the list view of AT Series)
    document_type_name = fields.Char("Type Name", compute="_compute_document_type_name")
    at_code = fields.Char("AT Validation Code")
    document_identifier = fields.Char(
        "Document Identifier",
        compute='_compute_document_identifier',
        help="The unique identification of documents of this series and type made up of the document type prefix and "
             "the series name, followed by '/' and the number of the document.",
        store=True,
    )

    _type_per_series_uniq = models.Constraint(
        'unique(document_type, name, company_id)',
        "This document type already exists for this series name in this company.",
    )
    _prefix_per_series_uniq = models.Constraint(
        'unique(prefix, name, company_id)',
        "This prefix has already been used in this series name in this company.",
    )
    _at_code_uniq = models.Constraint(
        'unique(at_code)',
        "The AT code must be unique.",
    )

    def _compute_active(self):
        today = fields.Date.today()
        for at_series in self:
            at_series.active = (
                at_series.date_start <= today
                and (at_series.date_end >= today if at_series.date_end else True)
            )

    def _search_active(self, operator, value):
        if value is None:
            return Domain.FALSE
        if isinstance(value, bool):
            value = {value}
        if operator not in ['not in', 'in', '=', '!=']:
            raise ValueError(_('Operator (%s) is not supported', operator))
        today = fields.Date.today()
        active_domain = Domain.AND([
            Domain('date_start', '<=', today),
            Domain.OR([
                Domain('date_end', '=', False),
                Domain('date_end', '>=', today),
            ]),
        ])
        not_active_domain = Domain.OR([
            Domain('date_start', '>', today),
            Domain.AND([
                Domain('date_end', '=', False),
                Domain('date_end', '<', today),
            ]),
        ])
        if len(value) == 1:
            if (
                (operator in ['=', 'in'] and True in value)             # active = True or active in [True]
                or (operator in ['!=', 'not in'] and False in value)    # active != False or active not in [False]
            ):
                return active_domain
            if (
                (operator in ['=', 'in'] and False in value)            # active = False or active in [False]
                or (operator in ['!=', 'not in'] and True in value)     # active != True or active not in [True]
            ):
                return not_active_domain

        return Domain.OR([active_domain, not_active_domain])

    @api.depends('document_type')
    def _compute_document_type_name(self):
        """ Used to display the types of document included in an AT Series in the list view """
        for series in self:
            series.document_type_name = dict(series._fields['document_type'].selection).get(series.document_type)

    @api.depends('prefix', 'name')
    def _compute_document_identifier(self):
        """
        Creates the prefix of the document number sequence. Also used to display how the document identifier for records
        under the series will show up in the document.
        Ex: AT Series name = 2025, prefix for invoice documents = FT, document number sequence starts at FT 2025/00001
        """
        for series in self:
            series.document_identifier = ' '.join(filter(None, [series.prefix or '', series.name or '']))

    @api.constrains('name')
    def _check_name(self):
        for series in self:
            if not re.match(r'^[a-zA-Z0-9]+$', series.name):
                raise ValidationError(_(
                    "The name of the series (%s) is invalid. It must consist of only letters and numbers (e.g. 2025, 2025B).",
                    series.name
                ))

    @api.constrains('prefix')
    def _check_prefix(self):
        for series in self:
            if not re.match(r'^[a-zA-Z0-9]+$', series.prefix):
                raise ValidationError(_(
                    "The prefix of the series (%s) is invalid. It must consist of only letters and numbers (e.g. INV, RINV).",
                    series.prefix
                ))

    @api.constrains('document_type', 'journal_id', 'journal_id')
    def _check_journal_requirements(self):
        for series in self:
            if series.document_type == 'payment_receipt' and not series.journal_id:
                raise ValidationError(_("A Payment Journal is required when you have Payment Receipt lines."))
            if series.document_type in {'out_receipt', 'out_invoice', 'out_invoice_receipt', 'out_refund', 'debit_note'} and not series.journal_id:
                raise ValidationError(_("A Sales Journal is required for account move document types (FT, FS, NC, ND)."))

    def _get_at_code(self):
        self.ensure_one()
        if not self.active:
            raise UserError(_("The series %(prefix)s is not active.", prefix=self.prefix))
        return self.at_code

    def write(self, vals):
        if any(field in vals for field in ('name', 'training_series', 'company_exclusive_series', 'document_type', 'prefix', 'at_code')):
            for at_series in self:
                if self.env['account.move'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.id),
                    ('state', "in", ('posted', 'cancel')),
                    ('l10n_pt_document_type', '=', at_series.document_type),
                ], limit=1):
                    raise UserError(_("You cannot change the properties of a series that has already been used in a move."))
                if self.env['account.payment'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.id),
                    ('state', "in", ('posted', 'cancel')),
                ], limit=1):
                    raise UserError(_("You cannot change the properties of a series that has already been used in a payment."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used(self):
        for at_series in self:
            if (
                self.env['account.move'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.id),
                    ('state', "in", ('posted', 'cancel')),
                    ('l10n_pt_document_type', '=', at_series.document_type),
                ], limit=1)
                or self.env['account.payment'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.id),
                    ('state', "in", ('paid', 'canceled')),
                ], limit=1)
            ):
                raise UserError(_("You cannot delete a series that is used. It will automatically be archived after the End Date"))

    @api.onchange('company_exclusive_series')
    def _onchange_company_exclusive_series(self):
        """ Reset the company_id field when the company_exclusive_series field is unchecked. """
        if not self.company_exclusive_series:
            self.company_id = self.env.company

    def _l10n_pt_get_document_number_sequence(self):
        """
        Returns the document number sequence for this AT series (company and document type dependent),
        creating it if needed.
        """
        self.ensure_one()

        sequence_code = f'l10n_pt_certification.{self.document_type}_{self.name.lower()}_sequence'

        if not (sequence := self.env['ir.sequence'].search([
            ('code', '=', sequence_code),
            ('company_id', '=', self.company_id.id),
        ])):
            return self.env['ir.sequence'].create({
                'name': f'{self.document_identifier} Sequence',
                'implementation': 'no_gap',
                'padding': 5,
                'prefix': f'{self.document_identifier}/',
                'company_id': self.company_id.id,
                'code': sequence_code,
            })
        return sequence
