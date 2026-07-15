import re
import urllib.parse

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr

from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils

L10N_PT_DOCUMENT_NUMBER_RE = r'^[^ ]+ [^/^ ]+/[0-9]+$'


class L10nPtDocumentMixin(models.AbstractModel):
    """
    Shared numbering & identity layer for Portuguese documents subject to AT requirements.

    Groups the mechanisms that are common to every AT-regulated document
    (``account.move``, ``account.payment``, ``sale.order``, ``stock.picking``):
    the AT series, the unique document number, the ATCUD and the print version.

    Models mixing this in must implement the hooks:
      - ``_l10n_pt_get_document_date``: the document's issuing date/datetime.
    """
    _name = 'l10n.pt.document.mixin'
    _description = "Portuguese AT Document (numbering & identity)"

    l10n_pt_at_series_id = fields.Many2one(
        comodel_name="l10n_pt.at.series",
        string="AT Series",
        copy=False,
    )
    l10n_pt_document_number = fields.Char(
        string="Unique Document Number",
        copy=False,
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

    def _l10n_pt_get_document_number(self):
        """The document number to be signed. Split out to allow patching in tests."""
        self.ensure_one()
        return self.l10n_pt_document_number

    ####################################
    # SHARED LOGIC
    ####################################

    @api.depends('l10n_pt_document_number')
    def _compute_l10n_pt_atcud(self):
        for record in self:
            if record._l10n_pt_country_ok() and not record.l10n_pt_atcud and record.l10n_pt_document_number:
                current_seq_number = int(record.l10n_pt_document_number.split('/')[-1])
                record.l10n_pt_atcud = f"{record.l10n_pt_at_series_id._get_at_code()}-{current_seq_number}"
            else:
                record.l10n_pt_atcud = record.l10n_pt_atcud or False

    def _set_l10n_pt_document_number(self):
        """Assign the next document number of the AT series, in chronological order."""
        records = self.filtered(
            lambda r: r._l10n_pt_country_ok() and r.l10n_pt_at_series_id and not r.l10n_pt_document_number
        )
        for record in records.sorted(key=lambda r: r._l10n_pt_get_document_date() or fields.Datetime.now()):
            record.l10n_pt_document_number = record.l10n_pt_at_series_id._l10n_pt_get_document_number_sequence().next_by_id()
        self._check_l10n_pt_document_number()

    def _check_l10n_pt_document_number(self):
        for record in self.filtered(lambda r: r._l10n_pt_country_ok() and r.l10n_pt_at_series_id):
            number = record.l10n_pt_document_number
            if number and not re.match(L10N_PT_DOCUMENT_NUMBER_RE, number):
                raise ValidationError(_(
                    "The document number (%s) is invalid. It must start with the internal code "
                    "of the document type, a space, the name of the series followed by a slash and the number of the "
                    "document within the series (e.g. NE 2025A/1). Please check if the series selected fulfill these "
                    "requirements.", number
                ))

    def update_l10n_pt_print_version(self):
        for record in self.filtered(lambda r: r._l10n_pt_country_ok()):
            record.l10n_pt_print_version = 'reprint' if record.l10n_pt_print_version else 'original'


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
      - ``_l10n_pt_series_document_types``: AT series document types owned by the model.
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

    def _l10n_pt_series_document_types(self):
        """AT series document types handled by this model."""
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
                raise UserError(_(
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
            'sorting_key': record._l10n_pt_get_document_date().isoformat(),
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
        at_series_records = self.env['l10n_pt.at.series'].search([
            '|',
            '&',
            ('company_id', '=', company.id),
            ('company_exclusive_series', '=', True),
            '&',
            ('company_id', 'in', company.parent_ids.ids),
            ('company_exclusive_series', '=', False),
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
