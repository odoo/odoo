import re

from odoo import api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.fields import Domain
from odoo.tools.misc import format_date


AT_SERIES_ACCOUNTING_DOCUMENT_TYPES = [
    ('out_invoice', 'Invoice (FT)'),
    ('out_receipt', 'Simplified Invoice (FS)'),
    ('out_invoice_receipt', 'Invoice/Receipt (FR)'),
    ('out_refund', 'Credit Note (NC)'),
    ('debit_note', 'Debit Note (ND)'),
    ('payment_receipt', 'Payment Receipt (RG)'),
]


class L10nPtATSeries(models.Model):
    """An AT series registered with the Portal das Finanças, in which one type of document is numbered."""
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
    document_type_name = fields.Char("Type Name", compute="_compute_document_type_name")
    # Whitelist for the `filterable_selection` widget on `document_type`.
    available_document_types = fields.Json(compute='_compute_available_document_types')
    at_code = fields.Char("AT Validation Code")
    document_identifier = fields.Char(
        "Document Identifier",
        compute='_compute_document_identifier',
        help="The unique identification of documents of this series and type made up of the document type prefix and "
             "the series name, followed by '/' and the number of the document.",
        store=True,
    )

    # Case-insensitive, as the series' number sequence is keyed on its lowercased name
    # (`_l10n_pt_get_document_number_sequence`).
    _type_per_series_name_uniq = models.UniqueIndex(
        '(document_type, lower(name), company_id)',
        "This document type already exists for this series name in this company (names are not case-sensitive).",
    )
    _prefix_per_series_uniq = models.Constraint(
        'unique(prefix, name, company_id)',
        "This prefix has already been used in this series name in this company.",
    )
    _at_code_uniq = models.Constraint(
        'unique(at_code)',
        "The AT code must be unique.",
    )

    @api.depends('date_end')
    def _compute_active(self):
        today = fields.Date.today()
        for at_series in self:
            at_series.active = at_series.date_end >= today if at_series.date_end else True

    def _search_active(self, operator, value):
        if operator != 'in':
            return NotImplemented
        return Domain('date_end', '=', False) | Domain('date_end', '>=', fields.Date.today())

    def _l10n_pt_is_valid_on(self, date):
        """
        Whether the series' validity window covers ``date``.

        Unlike ``active``, which only checks that the window is still open today.
        """
        if not self:
            return False
        self.ensure_one()
        return (
            (not self.date_start or self.date_start <= date)
            and (not self.date_end or self.date_end >= date)
        )

    @api.model
    def _l10n_pt_validity_domain(self, date, prefix=''):
        """
        ``_l10n_pt_is_valid_on`` as a domain.

        ``prefix`` traverses to the series from a related model, e.g. ``'l10n_pt_at_series_id.'``.
        """
        return (
            (Domain(f'{prefix}date_start', '=', False) | Domain(f'{prefix}date_start', '<=', date))
            & (Domain(f'{prefix}date_end', '=', False) | Domain(f'{prefix}date_end', '>=', date))
        )

    @api.model
    def _l10n_pt_company_domain(self, company):
        """The series ``company`` may use: its own exclusive ones, and the shared ones of its parents (itself included)."""
        return (
            (Domain('company_id', '=', company.id) & Domain('company_exclusive_series', '=', True))
            | (Domain('company_id', 'in', company.parent_ids.ids) & Domain('company_exclusive_series', '=', False))
        )

    @api.depends('document_type')
    def _compute_document_type_name(self):
        for series in self:
            series.document_type_name = dict(series._fields['document_type'].selection).get(series.document_type)

    @api.depends_context('l10n_pt_series_document_types')
    def _compute_available_document_types(self):
        self.available_document_types = (
            self.env.context.get('l10n_pt_series_document_types')
            or self._fields['document_type'].get_values(self.env)
        )

    @api.depends('prefix', 'name')
    def _compute_document_identifier(self):
        """
        The prefix of the series' document numbers, e.g. "FT 2025" for a series 2025 of prefix FT,
        whose first document is FT 2025/00001.
        """
        for series in self:
            series.document_identifier = ' '.join(filter(None, [series.prefix or '', series.name or '']))

    @api.constrains('name')
    def _check_name(self):
        for series in self:
            if not re.match(r'^[a-zA-Z0-9]+$', series.name):
                raise ValidationError(self.env._(
                    "The name of the series (%s) is invalid. It must consist of only letters and numbers (e.g. 2025, 2025B).",
                    series.name
                ))

    @api.constrains('prefix')
    def _check_prefix(self):
        for series in self:
            if not re.match(r'^[a-zA-Z0-9]+$', series.prefix):
                raise ValidationError(self.env._(
                    "The prefix of the series (%s) is invalid. It must consist of only letters and numbers (e.g. INV, RINV).",
                    series.prefix
                ))

    @api.constrains('document_type', 'journal_id')
    def _check_journal_requirements(self):
        for series in self:
            if series.document_type == 'payment_receipt' and not series.journal_id:
                raise ValidationError(self.env._("A Payment Journal is required when you have Payment Receipt lines."))
            if series.document_type in {'out_receipt', 'out_invoice', 'out_invoice_receipt', 'out_refund', 'debit_note'} and not series.journal_id:
                raise ValidationError(self.env._("A Sales Journal is required for account move document types (FT, FS, NC, ND)."))

    def _get_at_code(self):
        """
        The AT validation code of the series, for the ATCUD of a document numbered in it. Whether the
        series may still number documents is checked where they take their number
        (`_check_l10n_pt_at_series_id`): a document numbered while the series was valid keeps its
        code after the series has ended, e.g. an invoice posted on its last day and issued later.
        """
        self.ensure_one()
        if not self.at_code:
            raise self._l10n_pt_missing_at_code_warning()
        return self.at_code

    def _l10n_pt_missing_at_code_warning(self):
        """
        No document may be issued in a series before the AT has validated it (Portaria 195/2020):
        its validation code is part of every document's ATCUD. Opens the series to register it.
        """
        self.ensure_one()
        return RedirectWarning(
            self.env._(
                "The AT series %(series)s has no AT validation code yet. Register it with the AT, or enter "
                "the code obtained from the Portal das Finanças, before issuing documents in it.",
                series=self.document_identifier,
            ),
            {
                'name': self.env._('AT Series'),
                'type': 'ir.actions.act_window',
                'res_model': 'l10n_pt.at.series',
                'res_id': self.id,
                'view_mode': 'form',
                'views': [(self.env.ref('l10n_pt_certification.view_l10n_pt_at_series_form').id, 'form')],
                'target': 'new',
            },
            self.env._('Open the AT Series'),
        )

    def _l10n_pt_get_document_number_sequence(self):
        """
        Returns the document number sequence for this AT series (company and document type dependent),
        creating it if needed.
        """
        self.ensure_one()

        sequence_code = f'l10n_pt_certification.{self.document_type}_{self.name.lower()}_sequence'

        sequence_sudo = self.env['ir.sequence'].sudo()
        if not (sequence := sequence_sudo.search([
            ('code', '=', sequence_code),
            ('company_id', '=', self.company_id.id),
        ])):
            sequence = sequence_sudo.create({
                'name': f'{self.document_identifier} Sequence',
                'implementation': 'no_gap',
                'padding': 5,
                'prefix': f'{self.document_identifier}/',
                'company_id': self.company_id.id,
                'code': sequence_code,
            })
        return sequence.sudo(False)

    @api.onchange('company_exclusive_series')
    def _onchange_company_exclusive_series(self):
        if not self.company_exclusive_series:
            self.company_id = self.env.company

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        # A document asking for one type of series gets that type preset.
        document_types = self.env.context.get('l10n_pt_series_document_types') or []
        if 'document_type' in fields and not defaults.get('document_type') and len(document_types) == 1:
            defaults['document_type'] = document_types[0]
        return defaults

    @api.model
    def _l10n_pt_document_models(self):
        """The models of the documents issued in AT series: every concrete model built on the document mixin."""
        return [
            model_name
            for model_name in self.env.registry.descendants(['l10n.pt.document.mixin'], '_inherit')
            if not self.env[model_name]._abstract
        ]

    def _l10n_pt_get_used(self):
        """
        The series of ``self`` in which a document was numbered, issued or not, whatever its state
        now: such a series is frozen and kept (FAQ 4327, Despacho 8632/2014 1.9).
        """
        used_ids = set()
        for model_name in self._l10n_pt_document_models():
            # sudo: a series shared across branches holds documents of companies the user may not see.
            documents = self.env[model_name].sudo()
            [(series,)] = documents._read_group(
                [('l10n_pt_at_series_id', 'in', self.ids), *documents._l10n_pt_numbered_domain()],
                aggregates=['l10n_pt_at_series_id:recordset'],
            )
            used_ids.update(series.ids)
        return self.filtered(lambda s: s.id in used_ids)

    def _l10n_pt_check_closing(self, date_end):
        """
        A series in use is discontinued by ending it (Despacho 8632/2014 1.9, 2.5.1): from its end date
        on, no document can be issued in it. It can be ended at any date from its last document on,
        moved while it is still open, but never reopened once it has ended, nor left without an end.
        """
        date_end = fields.Date.to_date(date_end)
        last_document_dates = {}
        for model_name in self._l10n_pt_document_models():
            # sudo: a series shared across branches holds documents of companies the user may not see.
            documents = self.env[model_name].sudo()
            for series, last_date in documents._read_group(
                [('l10n_pt_at_series_id', 'in', self.ids), *documents._l10n_pt_numbered_domain()],
                groupby=['l10n_pt_at_series_id'],
                aggregates=[f'{documents._l10n_pt_date_field}:max'],
            ):
                if last_date := fields.Date.to_date(last_date):
                    last_document_dates[series.id] = max(last_document_dates.get(series.id, last_date), last_date)
        for at_series in self:
            if not at_series.active:
                raise UserError(self.env._("The series %(series)s has ended and cannot be reopened.", series=at_series.document_identifier))
            if not date_end and at_series.date_end:
                raise UserError(self.env._("The end date of the series %(series)s cannot be removed.", series=at_series.document_identifier))
            last_date = last_document_dates.get(at_series.id)
            if date_end and last_date and date_end < last_date:
                raise UserError(self.env._(
                    "The series %(series)s cannot end before its last document, dated %(date)s.",
                    series=at_series.document_identifier,
                    date=format_date(self.env, last_date),
                ))

    def write(self, vals):
        # Its end date is how a series in use is closed, so it stays writable (see `_l10n_pt_check_closing`).
        protected_fields = {'prefix', 'name', 'document_type', 'date_start', 'training_series', 'journal_id', 'company_exclusive_series', 'company_id'}
        if protected_fields & vals.keys() or {'at_code', 'date_end'} & vals.keys():
            used_series = self._l10n_pt_get_used()
            if used_series and protected_fields & vals.keys():
                raise UserError(self.env._("You cannot change the properties of a series in which documents were already issued."))
            if 'at_code' in vals and used_series.filtered('at_code'):
                raise UserError(self.env._("You cannot change the AT Validation Code of a series in which documents were already issued."))
            if 'date_end' in vals:
                used_series._l10n_pt_check_closing(vals['date_end'])
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used(self):
        if used_series := self._l10n_pt_get_used():
            raise UserError(self.env._(
                "You cannot delete a series in which documents were already issued (%(series)s). "
                "Set its End Date to close it.",
                series=", ".join(used_series.mapped('document_identifier')),
            ))

    def get_formview_action(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'l10n_pt_certification.action_open_l10n_pt_at_series_series_list_view'
        )
        action['domain'] = [('journal_id', '=', self.journal_id.id)]
        return action
