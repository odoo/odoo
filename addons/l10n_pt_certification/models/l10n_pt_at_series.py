import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

AT_SERIES_ACCOUNTING_DOCUMENT_TYPES = [
    ('out_invoice', 'Invoice (FT)'),
    ('out_receipt', 'Simplified Invoice (FS)'),
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
    _rec_name = 'name'

    name = fields.Char(
        "Name of the Series",
        required=True,
        help="The name of the series will be part of the document number sequence.",
    )
    training_series = fields.Boolean("Training Series")
    date_end = fields.Date("End Date")
    active = fields.Boolean(compute='_compute_active', search='_search_active')
    company_exclusive_series = fields.Boolean(
        string="Exclusive Series",
        help="If checked, this series will only be used by one company and not shared across branches",
    )
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    at_series_line_ids = fields.One2many(
        'l10n_pt.at.series.line',
        'at_series_id',
        string='Document Types',
        copy=True,
    )
    sale_journal_id = fields.Many2one(
        'account.journal',
        string='Sales Journal',
        help="This series will be available for account moves belonging to this, and only this, journal.",
        check_company=True,
        domain="[('type', '=', 'sale')]",
    )
    payment_journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        help="This series will be available for payments belonging to this, and only this, journal.",
        check_company=True,
        domain="[('type', 'in', ('bank', 'credit', 'cash'))]",
    )

    _sql_constraints = [
        ('name_company_uniq', 'unique(company_id, name)', "The AT Series name must be unique."),
    ]

    def _compute_active(self):
        for at_series in self:
            at_series.active = at_series.date_end >= fields.Date.today() if at_series.date_end else True

    def _search_active(self, operator, value):
        if operator not in ['in', '=', '!=']:
            raise ValueError(_('This operator is not supported'))
        today = fields.Date.today()
        if (operator == '=' and value) or (operator == '!=' and not value):
            domain = ['|', ('date_end', '=', False), ('date_end', '>=', today)]
        else:
            domain = ['|', ('date_end', '=', False), ('date_end', '<', today)]
        return domain

    @api.constrains('name')
    def _check_name(self):
        for series in self:
            if not re.match(r'^[a-zA-Z0-9]+$', series.name):
                raise ValidationError(_(
                    "The name of the series (%s) is invalid. It must consist of only letters and numbers (e.g. 2025, 2025B).",
                    series.name
                ))

    @api.constrains('at_series_line_ids', 'payment_journal_id', 'sale_journal_id')
    def _check_journal_requirements(self):
        for series in self:
            at_line_types = set(series.at_series_line_ids.mapped('type'))
            if 'payment_receipt' in at_line_types and not series.payment_journal_id:
                raise ValidationError(_("A Payment Journal is required when you have Payment Receipt lines."))
            if at_line_types & {'out_receipt', 'out_invoice', 'out_refund', 'debit_note'} and not series.sale_journal_id:
                raise ValidationError(_("A Sales Journal is required for account move document types (FT, FS, NC, ND)."))

    def write(self, vals):
        if 'name' in vals or 'training_series' in vals or 'company_exclusive_series' in vals:
            for at_series in self:
                if self.env['account.move'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.id),
                    ('state', 'in', ('posted', 'cancel')),
                ], limit=1):
                    raise UserError(_("You cannot change the name, training status or exclusivity setting of a series that has already been used."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used(self):
        for at_series in self:
            if self.env['account.move'].search_count([
                ('l10n_pt_at_series_id', '=', at_series.id),
                ('state', 'in', ('posted', 'cancel')),
            ], limit=1):
                raise UserError(_("You cannot delete a series that is used. It will automatically be archived after the End Date"))

    def _get_line_for_type(self, document_type):
        self.ensure_one()
        return self.at_series_line_ids.filtered(lambda l: l.type == document_type)

    @api.onchange('company_exclusive_series')
    def _onchange_company_exclusive_series(self):
        """ Reset the company_id field when the company_exclusive_series field is unchecked. """
        if not self.company_exclusive_series:
            self.company_id = self.env.company


class L10nPtATSeriesLine(models.Model):
    _name = "l10n_pt.at.series.line"
    _description = "Document-specific Autoridade Tributária (AT) Series"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of
    _rec_name = 'type_name'

    prefix = fields.Char(
        string="Document-specific Series Prefix",
        required=True,
        help="The internal code of the document type that will be combined with the Series Name to form "
             "the unique identification of documents.",
    )
    type = fields.Selection(
        string="Document Type",
        selection=AT_SERIES_ACCOUNTING_DOCUMENT_TYPES,
        required=True,
        help="Customer Invoices require an Invoice (FT) series, and Sales Receipts require a Simplified Invoice (FS) series.",
    )
    # Used in _rec_name to display the types of documents within an AT Series (displayed in the list view of AT Series)
    type_name = fields.Char("Type Name", compute="_compute_type_name")
    at_code = fields.Char("AT Validation Code", required=True)
    at_series_id = fields.Many2one(
        'l10n_pt.at.series',
        string='AT Series',
        required=True,
        readonly=True,
        ondelete="cascade",
        check_company=True,
    )
    document_identifier = fields.Char(
        "Document Identifier",
        compute='_compute_document_identifier',
        help="The unique identification of documents of this series and type made up of the document type prefix and "
             "the series name, followed by '/' and the number of the document.",
    )
    company_exclusive_series = fields.Boolean(related='at_series_id.company_exclusive_series')
    company_id = fields.Many2one(
        related='at_series_id.company_id', store=True, readonly=True, precompute=True,
        index=True,
    )
    at_series_active = fields.Boolean(related="at_series_id.active")

    _sql_constraints = [
        ('type_per_series_uniq', 'unique(type, at_series_id)', "This document type already exists for this series."),
        ('prefix_per_series_uniq', 'unique(prefix, at_series_id)', "This prefix has already been used in this series."),
        ('at_code_uniq', 'unique(at_code)', "The AT code must be unique."),
    ]

    @api.depends('prefix', 'at_series_id.name')
    def _compute_type_name(self):
        """ Used to display the types of document included in an AT Series in the list view """
        for series in self:
            series.type_name = dict(series._fields['type'].selection).get(series.type)

    @api.depends('prefix', 'at_series_id.name')
    def _compute_document_identifier(self):
        """
        Creates the prefix of the document number sequence. Also used to display how the document identifier for records
        under the series will show up in the document.
        Ex: AT Series name = 2025, prefix for invoice documents = FT, document number sequence starts at FT 2025/00001
        """
        for series in self:
            series.document_identifier = ' '.join(filter(None, [series.prefix or '', series.at_series_id.name or '']))

    @api.constrains('prefix')
    def _check_prefix(self):
        for series in self:
            if not re.match(r'^[a-zA-Z0-9]+$', series.prefix):
                raise ValidationError(_(
                    "The prefix of the series (%s) is invalid. It must consist of only letters and numbers (e.g. INV, RINV).",
                    series.prefix
                ))

    def _get_at_code(self):
        self.ensure_one()
        if not self.at_series_active:
            raise UserError(_("The series %(prefix)s is not active.", prefix=self.prefix))
        return self.at_code

    def write(self, vals):
        if 'type' in vals or 'prefix' in vals or 'at_code' in vals:
            for at_series in self:
                if self.env['account.move'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.at_series_id.id),
                    ('state', "in", ('posted', 'cancel')),
                    ('move_type', '=', at_series.type),
                ], limit=1):
                    raise UserError(_("You cannot change the type, prefix or AT code of a series that has already been used in a move."))
                if self.env['account.payment'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.at_series_id.id),
                    ('state', "in", ('posted', 'cancel')),
                ], limit=1):
                    raise UserError(_("You cannot change the type, prefix or AT code of a series that has already been used in a payment."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used(self):
        for at_series in self:
            if (
                self.env['account.move'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.at_series_id.id),
                    ('state', "in", ('posted', 'cancel')),
                    ('move_type', '=', at_series.type),
                ], limit=1)
                or self.env['account.payment'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.at_series_id.id),
                    ('state', "in", ('paid', 'canceled')),
                ], limit=1)
            ):
                raise UserError(_("You cannot delete a series that is used. It will automatically be archived after the End Date"))

    def _l10n_pt_get_document_number_sequence(self):
        """
        Returns the document number sequence for this AT series line (company and document type dependent),
        creating it if needed.
        """
        self.ensure_one()

        sequence_code = f'l10n_pt_certification.{self.type}_{self.at_series_id.name.lower()}_sequence'

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
