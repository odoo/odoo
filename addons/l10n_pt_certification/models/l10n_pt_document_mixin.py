import re
import urllib.parse

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr

from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils

L10N_PT_DOCUMENT_NUMBER_RE = r'^[^ ]+ [^/^ ]+/[0-9]+$'


class L10nPtDocumentMixin(models.AbstractModel):
    """
    Shared numbering & identity layer for Portuguese documents subject to AT requirements.

    Groups the mechanisms that are common to every AT-regulated document
    (``account.move``, ``account.payment``, ``sale.order``, ``stock.picking``):
    the document type, the AT series, the unique document number, the ATCUD and the print version.

    Models mixing this in must implement the hooks:
      - ``_l10n_pt_get_document_date``: the document's issuing date/datetime.
      - ``_l10n_pt_get_document_type``: the AT type the document is issued as.
    They must also extend ``l10n_pt_document_type`` with the types they own, via ``selection_add``,
    and list in ``_l10n_pt_document_type_depends`` the fields that determine that type.
    """
    _name = 'l10n.pt.document.mixin'
    _description = "Portuguese AT Document (numbering & identity)"

    # Field holding the document's issuing date, for series-wide aggregates and the date warning.
    # Overridden per model, as `sequence.mixin` does with `_sequence_date_field`.
    _l10n_pt_date_field = "date"

    # Fields whose change may still alter the document type, before the document is issued.
    # Overridden per model, and fed to `_compute_l10n_pt_document_type`'s dynamic `depends`.
    _l10n_pt_document_type_depends = ()

    l10n_pt_document_type = fields.Selection(
        # To be extended by each model with the document types it owns, via `selection_add`.
        selection=[],
        string="Portuguese Document Type",
        compute='_compute_l10n_pt_document_type',
        store=True,
        help="Type of Portuguese document, as recognized by the AT. It selects the AT series, is "
             "encoded in the document number and in the QR code, and is printed on every page.",
    )
    l10n_pt_at_series_id = fields.Many2one(
        comodel_name="l10n_pt.at.series",
        string="AT Series",
        copy=False,
    )
    l10n_pt_document_number = fields.Char(
        string="Unique Document Number",
        copy=False,
        # Allocated by `_set_l10n_pt_document_number`; never editable by hand, on any model.
        readonly=True,
        help="Internal identifier for Portuguese documents, made up of the document type code, "
             "the series name, and the number of the document within the series.",
    )
    l10n_pt_atcud = fields.Char(
        string='Portuguese ATCUD',
        compute='_compute_l10n_pt_atcud',
        store=True,
        help="Unique document code formed by the AT series validation code and the number of the document.",
    )
    l10n_pt_print_version = fields.Selection(
        selection=[
            ('original', 'Original print'),
            ('reprint', 'Reprint'),
        ],
        string="Version of Printed Document",
        copy=False,
    )
    l10n_pt_cancel_reason = fields.Char(
        string="Reason for Cancellation",
        copy=False,
        readonly=True,
        help="Reason given by the user for cancelling this document.",
    )
    l10n_pt_show_future_date_warning = fields.Boolean(compute='_compute_l10n_pt_show_future_date_warning')
    l10n_pt_at_series_missing_at_code = fields.Boolean(
        string='AT Series missing validation code',
        compute='_compute_l10n_pt_at_series_missing_at_code',
        help="The AT Series used does not have a validation code. It must be registered with the AT before sending/printing.",
    )

    ####################################
    # HOOKS (to be implemented by models)
    ####################################

    def _l10n_pt_country_ok(self):
        """Whether the record requires Portuguese AT handling."""
        self.ensure_one()
        return self.company_id.account_fiscal_country_id.code == 'PT'

    def _l10n_pt_get_document_date(self):
        """The document's issuing date/datetime (move.date, sale.date_order, picking.date_done, ...)."""
        raise NotImplementedError

    def _l10n_pt_get_document_type(self):
        """
        The AT document type this record is issued as, taken from the model's own selection.

        Only called for records that pass ``_l10n_pt_country_ok`` and are not issued yet.
        """
        raise NotImplementedError

    def _l10n_pt_document_is_open(self):
        """Whether the document can still be edited, i.e. a date warning is still actionable."""
        self.ensure_one()
        return self.state == 'draft'

    def _l10n_pt_get_document_number(self):
        """The document number to be signed. Split out to allow patching in tests."""
        self.ensure_one()
        return self.l10n_pt_document_number

    ####################################
    # SHARED LOGIC
    ####################################

    @api.depends(lambda self: self._l10n_pt_document_type_depends)
    def _compute_l10n_pt_document_type(self):
        for record in self:
            current_type = record.l10n_pt_document_type
            if record.l10n_pt_document_number and current_type:
                record.l10n_pt_document_type = current_type
            elif record._l10n_pt_country_ok():
                record.l10n_pt_document_type = record._l10n_pt_get_document_type()
            else:
                record.l10n_pt_document_type = False

    def _l10n_pt_series_document_types(self):
        """
        AT series document types owned by this model.

        Defaults to the model's own ``l10n_pt_document_type`` selection, which each module extends
        in lockstep with ``l10n_pt.at.series.document_type``.
        """
        return self._fields['l10n_pt_document_type'].get_values(self.env)

    @api.depends('l10n_pt_document_number')
    def _compute_l10n_pt_atcud(self):
        for record in self:
            if record._l10n_pt_country_ok() and not record.l10n_pt_atcud and record.l10n_pt_document_number:
                record.l10n_pt_atcud = f"{record.l10n_pt_at_series_id._get_at_code()}-{record._l10n_pt_get_sequence_number()}"
            else:
                record.l10n_pt_atcud = record.l10n_pt_atcud or False

    @api.depends('l10n_pt_at_series_id.at_code')
    def _compute_l10n_pt_at_series_missing_at_code(self):
        for record in self:
            record.l10n_pt_at_series_missing_at_code = (
                record._l10n_pt_country_ok()
                and record.l10n_pt_at_series_id
                and not record.l10n_pt_at_series_id.at_code
            )

    def _l10n_pt_assign_document_number(self, number):
        """Store a freshly allocated number. Overridden where the number also lives elsewhere."""
        self.ensure_one()
        self.l10n_pt_document_number = number

    def _set_l10n_pt_document_number(self):
        """
        Allocate the next document number of the AT series, in chronological order.

        Allocating consumes a ``no_gap`` sequence, so it is deliberately an explicit action rather
        than a compute: it must happen once, at the exact point the document is issued.
        """
        records = self.filtered(
            lambda r: r._l10n_pt_country_ok() and r.l10n_pt_at_series_id and not r.l10n_pt_document_number
        )
        # `sorted` is stable, so pre-sorting on `id` deterministically breaks ties between documents
        # sharing a date. Documents with no date yet (a transport document is numbered before it
        # moves) keep that `id` order.
        records = records.sorted('id')
        undated = records.filtered(lambda r: not r._l10n_pt_get_document_date())
        ordered = list((records - undated).sorted(key=lambda r: r._l10n_pt_get_document_date())) + list(undated)
        for record in ordered:
            record._l10n_pt_assign_document_number(
                record.l10n_pt_at_series_id._l10n_pt_get_document_number_sequence().next_by_id()
            )
        self._check_l10n_pt_document_number()

    def _l10n_pt_get_sequence_number(self):
        """The document's position within its series -- the order the signature chain must follow."""
        self.ensure_one()
        return int(self.l10n_pt_document_number.split('/')[-1])

    def _check_l10n_pt_document_number(self):
        for record in self.filtered(lambda r: r._l10n_pt_country_ok() and r.l10n_pt_at_series_id):
            number = record.l10n_pt_document_number
            if number and not re.match(L10N_PT_DOCUMENT_NUMBER_RE, number):
                raise ValidationError(self.env._(
                    "The document number (%s) is invalid. It must start with the internal code "
                    "of the document type, a space, the name of the series followed by a slash and the number of the "
                    "document within the series (e.g. NE 2025A/1). Please check if the series selected fulfill these "
                    "requirements.", number
                ))

    def update_l10n_pt_print_version(self):
        for record in self.filtered(lambda r: r._l10n_pt_country_ok()):
            record.l10n_pt_print_version = 'reprint' if record.l10n_pt_print_version else 'original'

    @api.depends(lambda self: ('state', self._l10n_pt_date_field))
    def _compute_l10n_pt_show_future_date_warning(self):
        """
        No other document may be issued with the current or previous date within the same series as
        a document issued in the future, so warn as soon as a future date is entered.
        """
        today = fields.Date.today()
        for record in self:
            document_date = record._l10n_pt_country_ok() and record._l10n_pt_get_document_date()
            record.l10n_pt_show_future_date_warning = bool(
                document_date
                and record._l10n_pt_document_is_open()
                and fields.Date.to_date(document_date) > today
            )

    def _check_l10n_pt_dates(self):
        """
        According to the Portuguese tax authority:
        "When the document issuing date is later than the current date, or superior than the date on the system,
        no other document may be issued with the current or previous date within the same series"

        Documents therefore have to be issued in chronological order within their series: a document may
        never be dated before the latest document already issued in the same series.
        """
        records = self.filtered(lambda r: r._l10n_pt_country_ok() and r.l10n_pt_at_series_id)
        series = records.l10n_pt_at_series_id
        if not series:
            return

        # A document occupies a position in its series as soon as it is numbered; cancelled documents
        # keep the number they consumed, so they still count towards the series' latest date.
        # sudo: the series' chronology must be evaluated over every document it contains, regardless
        # of which companies the current user has selected.
        max_date_per_series = dict(self.env[self._name].sudo()._read_group(
            domain=[
                ('l10n_pt_at_series_id', 'in', series.ids),
                ('l10n_pt_document_number', '!=', False),
                # Exclude the documents being checked, so the rule holds whether they are numbered
                # before or after the check.
                ('id', 'not in', records.ids),
            ],
            groupby=['l10n_pt_at_series_id'],
            aggregates=[f'{self._l10n_pt_date_field}:max'],
        ))

        for record in records:
            max_document_date = max_date_per_series.get(record.l10n_pt_at_series_id)
            document_date = record._l10n_pt_get_document_date()
            if max_document_date and document_date and document_date < max_document_date:
                raise UserError(self.env._(
                    "You cannot issue a document dated earlier than the last document issued in this "
                    "AT series (%(series)s).",
                    series=record.l10n_pt_at_series_id.display_name,
                ))

    def _check_l10n_pt_at_series_id(self):
        for record in self.filtered(lambda r: r._l10n_pt_country_ok()):
            if not record.l10n_pt_at_series_id:
                raise UserError(self.env._("Please select a series for this document."))
            series = record.l10n_pt_at_series_id
            if record.l10n_pt_document_type and record.l10n_pt_document_type != series.document_type:
                raise UserError(self.env._("The series does not match the document type."))
            record_date = fields.Date.to_date(record._l10n_pt_get_document_date())
            if not series.active or not series._l10n_pt_is_valid_on(record_date):
                raise UserError(self.env._("An inactive series cannot be used."))


class L10nPtHashedDocumentMixin(models.AbstractModel):
    """
    Shared signing & QR-code layer for Portuguese documents that must be cryptographically
    secured (``sale.order`` and ``stock.picking``; ``account.move`` keeps riding the base
    ``account`` hashing framework and is intentionally not built on this mixin).

    On top of the numbering layer, this groups: the inalterability hash (RSA signature chained
    with the previous document), the hash version/short helpers, the informational QR code, the
    write-lock protecting hashed fields, and the batch signing routine.

    Models mixing this in must implement, in addition to ``_l10n_pt_get_document_date``:
      - ``_l10n_pt_get_saft_doc_type``: the SAF-T document type code used in the QR code (``D:``).
      - ``_l10n_pt_get_unhashed_records`` / ``_l10n_pt_find_last_hashed``: chain boundaries.
    They may override the hooks ``_l10n_pt_get_gross_total``, ``_l10n_pt_post_hash_hook``,
    ``_l10n_pt_qr_add_tax_details`` and ``_l10n_pt_qr_get_totals``.
    """
    _name = 'l10n.pt.hashed.document.mixin'
    _description = "Portuguese AT Document (signed & QR code)"
    _inherit = ['l10n.pt.document.mixin']

    l10n_pt_inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True)
    l10n_pt_inalterable_hash_short = fields.Char(
        string="Short version of the Portuguese hash",
        compute='_compute_l10n_pt_inalterable_hash_info',
    )
    l10n_pt_inalterable_hash_version = fields.Integer(
        string="Portuguese hash version",
        compute='_compute_l10n_pt_inalterable_hash_info',
    )
    l10n_pt_qr_code_str = fields.Char(
        string="Portuguese QR Code",
        compute='_compute_l10n_pt_qr_code_str',
        store=True,
    )

    ####################################
    # HOOKS (to be implemented by models)
    ####################################

    def _l10n_pt_get_gross_total(self):
        """Gross total signed in the hash (0 for documents without a monetary total, e.g. transfers)."""
        return 0.0

    def _l10n_pt_get_saft_doc_type(self):
        """SAF-T (PT) document type code used in the QR code ``D:`` field."""
        raise NotImplementedError

    def _l10n_pt_get_unhashed_records(self, at_series):
        """Records of the given series still missing a hash, in chain order."""
        raise NotImplementedError

    def _l10n_pt_find_last_hashed(self, at_series):
        """The last already-hashed record of the given series (the chain's previous link)."""
        raise NotImplementedError

    def _l10n_pt_post_hash_hook(self):
        """Per-recordset action to run right after the hash has been assigned."""

    def _l10n_pt_validate_before_hash(self):
        """Per-recordset validation to run right before signing."""

    def _l10n_pt_qr_add_tax_details(self, qr_code_dict, tax_letter):
        """Add the per-tax-category base/VAT entries to the QR code (no-op by default)."""

    def _l10n_pt_qr_get_totals(self):
        """Return the ``(N, O)`` amounts (tax total, grand total) formatted for the QR code."""
        self.ensure_one()
        return "0.00", "0.00"

    ####################################
    # WRITE LOCK
    ####################################

    def _l10n_pt_protected_fields(self):
        """Fields that cannot be modified once the document is hashed."""
        return self._get_integrity_hash_fields() + ['l10n_pt_inalterable_hash']

    def write(self, vals):
        if not vals:
            return super().write(vals)
        for record in self.filtered(lambda r: r._l10n_pt_country_ok() and r.l10n_pt_inalterable_hash):
            violated_fields = set(vals).intersection(record._l10n_pt_protected_fields())
            if violated_fields:
                raise UserError(self.env._(
                    "This document is protected by a hash. "
                    "Therefore, you cannot edit the following fields: %s.",
                    ', '.join(f['string'] for f in self.fields_get(violated_fields).values())
                ))
        return super().write(vals)

    ####################################
    # HASH
    ####################################

    def _get_integrity_hash_fields(self):
        if not self._l10n_pt_country_ok():
            return []
        return ['l10n_pt_hashed_on', 'name', 'l10n_pt_document_number']

    def _calculate_hashes(self, previous_hash=None):
        if not self or not self[0]._l10n_pt_country_ok():
            return {}
        self.l10n_pt_hashed_on = fields.Datetime.now()
        docs_to_sign = [{
            'id': record.id,
            # The chain follows the series' numbering, not the document date: dates tie routinely
            # (a batch of transfers validated together shares one `date_done`).
            'sorting_key': record._l10n_pt_get_sequence_number(),
            'date': record._l10n_pt_get_document_date().strftime('%Y-%m-%d'),
            'system_entry_date': record.l10n_pt_hashed_on.isoformat(timespec='seconds'),
            'name': record._l10n_pt_get_document_number(),
            'gross_total': float_repr(record._l10n_pt_get_gross_total(), precision_digits=2),
            'previous_signature': previous_hash,
        } for record in self]
        return pt_hash_utils.sign_records(self.env, docs_to_sign, self._name)

    @api.depends('l10n_pt_inalterable_hash')
    def _compute_l10n_pt_inalterable_hash_info(self):
        for record in self:
            if record.l10n_pt_inalterable_hash:
                hash_version, hash_str = record.l10n_pt_inalterable_hash.split("$")[1:]
                record.l10n_pt_inalterable_hash_version = int(hash_version)
                record.l10n_pt_inalterable_hash_short = hash_str[0] + hash_str[10] + hash_str[20] + hash_str[30]
            else:
                record.l10n_pt_inalterable_hash_version = False
                record.l10n_pt_inalterable_hash_short = False

    def _l10n_pt_compute_missing_hashes(self, company=None):
        """
        Compute the hash/ATCUD for all records that do not have one yet
        (because they were not printed/previewed yet).
        """
        company = company or self.env.company

        # Get all AT series that apply to this model to find unhashed records per series
        # `active` on l10n_pt.at.series is a validity window (date_end >= today), not an archive
        # flag, but the ORM still injects it into every search. Expired series must stay visible
        # here: documents issued before a series ended still have to be signed and verified.
        at_series_model = self.env['l10n_pt.at.series']
        at_series_records = at_series_model.with_context(active_test=False).search([
            *at_series_model._l10n_pt_company_domain(company),
            ('document_type', 'in', self._l10n_pt_series_document_types()),
        ])
        for at_series in at_series_records:
            records = self._l10n_pt_get_unhashed_records(at_series)
            if not records:
                continue

            records._set_l10n_pt_document_number()

            previous_record = self._l10n_pt_find_last_hashed(at_series)
            try:
                previous_hash = previous_record.l10n_pt_inalterable_hash.split("$")[2] if previous_record.l10n_pt_inalterable_hash else ""
            except IndexError:  # hash is not correctly formatted (it has been altered!)
                previous_hash = "invalid_hash"  # will never be a valid hash

            records._l10n_pt_validate_before_hash()

            records_hashes = records._calculate_hashes(previous_hash)
            hashed_records = self.browse()
            for record, l10n_pt_inalterable_hash in records_hashes.items():
                record.l10n_pt_inalterable_hash = l10n_pt_inalterable_hash
                hashed_records |= record
            hashed_records._l10n_pt_post_hash_hook()

    ####################################
    # QR CODE
    ####################################

    def l10n_pt_verify_prerequisites_qr_code(self):
        self.ensure_one()
        if self._l10n_pt_country_ok():
            return pt_hash_utils.verify_prerequisites_qr_code(self, self.l10n_pt_inalterable_hash, self.l10n_pt_atcud)
        return None

    @api.depends('l10n_pt_inalterable_hash')
    def _compute_l10n_pt_qr_code_str(self):
        """
        Generate the informational QR code for Portugal.
        E.g.: A:509445535*B:123456823*C:BE*D:FT*E:N*F:20220103*G:FT 01P2022/1*H:0*I1:PT*I7:325.20*I8:74.80*N:74.80*O:400.00*P:0.00*Q:P0FE*R:2230
        """
        for record in self.filtered(lambda r: (
            r._l10n_pt_country_ok()
            and r.l10n_pt_inalterable_hash
            and not r.l10n_pt_qr_code_str  # Skip if already computed
        )):
            record.l10n_pt_verify_prerequisites_qr_code()
            # Most of the values needed to create the QR code string are filled in pt_hash_utils
            qr_code_dict, tax_letter = pt_hash_utils.l10n_pt_common_qr_code_str(record, self.env, record._l10n_pt_get_document_date())
            qr_code_dict['D:'] = f"{record._l10n_pt_get_saft_doc_type()}*"
            qr_code_dict['H:'] = f"{record.l10n_pt_atcud}*"
            record._l10n_pt_qr_add_tax_details(qr_code_dict, tax_letter)
            n_amount, o_amount = record._l10n_pt_qr_get_totals()
            qr_code_dict['N:'] = f"{n_amount}*"
            qr_code_dict['O:'] = f"{o_amount}*"
            qr_code_dict['Q:'] = f"{record.l10n_pt_inalterable_hash_short}*"
            # Create QR code string from dictionary
            qr_code_str = ''.join(f"{key}{value}" for key, value in sorted(qr_code_dict.items()))
            record.l10n_pt_qr_code_str = urllib.parse.quote_plus(qr_code_str)
