import re
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import SQL, float_repr
from odoo.tools.misc import format_date

from odoo.addons.l10n_pt_certification.const import PT_DOCUMENT_TYPE_DESIGNATIONS
from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils

L10N_PT_DOCUMENT_NUMBER_RE = r'^[^ ]+ [^/^ ]+/[0-9]+$'
INTEGRITY_HASH_BATCH_SIZE = 1000


class L10nPtDocumentMixin(models.AbstractModel):
    """
    Shared numbering & identity layer for Portuguese documents subject to AT requirements.

    Groups the mechanisms that are common to every AT-regulated document
    (``account.move``, ``account.payment``, ``sale.order``, ``stock.picking``):
    the document type, the AT series, the unique document number, the ATCUD and the print version.

    Models mixing this in must implement the hooks:
      - ``_l10n_pt_get_document_date``: the document's issuing date/datetime.
      - ``_l10n_pt_get_document_type``: the AT type the document is issued as.
    Models that are signed may also override ``_l10n_pt_get_gross_total``, which defaults to 0.
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
    # Who issued the document, and when and by whom it was cancelled: the SAF-T (PT) reports the
    # current status of every document with its date and user (Portaria 302/2016 4.1.4.3.2,
    # 4.1.4.3.4, 4.1.4.12; FAQ 2763).
    l10n_pt_issue_user_id = fields.Many2one(
        comodel_name='res.users',
        string="Issued By",
        copy=False,
        readonly=True,
        help="User who issued this document, i.e. gave it its number.",
    )
    # The SystemEntryDate of a document that is not signed (a receipt); signed ones record it when signed.
    l10n_pt_issued_on = fields.Datetime(string="Issued On", copy=False, readonly=True)
    l10n_pt_cancel_date = fields.Datetime(string="Cancelled On", copy=False, readonly=True)
    l10n_pt_cancel_user_id = fields.Many2one(
        comodel_name='res.users',
        string="Cancelled By",
        copy=False,
        readonly=True,
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

    def _l10n_pt_is_cancelled(self):
        """Whether the document is cancelled (annulled), as its prints and QR code must say."""
        self.ensure_one()
        return self.state == 'cancel'

    def _l10n_pt_document_is_open(self):
        """Whether the document can still be edited, i.e. a date warning is still actionable."""
        self.ensure_one()
        return self.state == 'draft'

    def _l10n_pt_get_document_number(self):
        """The document number to be signed. Split out to allow patching in tests."""
        self.ensure_one()
        return self.l10n_pt_document_number

    def _l10n_pt_get_gross_total(self):
        """Gross total signed in the hash (0 for documents without a monetary total, e.g. transfers)."""
        return 0.0

    ####################################
    # SHARED LOGIC
    ####################################

    def _l10n_pt_get_hash_values(self):
        """
        The exact values this document is signed over.

        Signing and verification both read this, so they cannot drift apart: changing what a
        document is signed over means changing it here, which changes both sides at once. Rendering
        the values into the signed message is ``pt_hash_utils.format_hash_values``, equally shared.
        """
        self.ensure_one()
        return {
            'date': self._l10n_pt_get_document_date(),
            'system_entry_date': self.l10n_pt_hashed_on,
            'document_number': self._l10n_pt_get_document_number(),
            'gross_total': self._l10n_pt_get_gross_total(),
        }

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
        # A number makes the document issued, and its ATCUD needs the series' AT validation code.
        if series_without_code := records.l10n_pt_at_series_id.filtered(lambda s: not s.at_code):
            raise series_without_code[:1]._l10n_pt_missing_at_code_warning()
        records.company_id._l10n_pt_check_system_clock()
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
        records.write({'l10n_pt_issue_user_id': self.env.uid, 'l10n_pt_issued_on': fields.Datetime.now()})
        self._check_l10n_pt_document_number()

    def _l10n_pt_record_cancellation(self):
        """Record when and by whom the issued documents of ``self`` were cancelled."""
        self.filtered(lambda r: r.l10n_pt_document_number and r._l10n_pt_country_ok()).write({
            'l10n_pt_cancel_date': fields.Datetime.now(),
            'l10n_pt_cancel_user_id': self.env.uid,
        })

    def _l10n_pt_get_first_print_copy_labels(self):
        """The copies the document's first print is made of, by their print-version label."""
        self.ensure_one()
        return ['Original']

    def _l10n_pt_get_document_type_designation(self):
        """The document type as printed: its AT designation, in Portuguese whatever the language."""
        self.ensure_one()
        return PT_DOCUMENT_TYPE_DESIGNATIONS.get(self.l10n_pt_document_type, '')

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

    @api.ondelete(at_uninstall=False)
    def _unlink_except_l10n_pt_issued(self):
        # An issued document stays in the database, annulled ones included, so that its series has
        # no gap (DL 28/2019 art. 7(4)-(5), Despacho 8632/2014 1.9). Core leaves some of them
        # deletable: an unsigned cancelled invoice, any receipt, a quotation.
        if issued := self.filtered(lambda r: r.l10n_pt_document_number and r._l10n_pt_country_ok()):
            raise UserError(self.env._(
                "Documents issued in Portugal cannot be deleted (%(documents)s). Cancel them instead: "
                "a cancelled document stays in its series.",
                documents=", ".join(issued.mapped('l10n_pt_document_number')),
            ))


class L10nPtQrDocumentMixin(models.AbstractModel):
    """
    Shared QR-code layer for Portuguese documents that carry a signature.

    Every AT-regulated document prints an informational QR code built from the same fields, and the
    signature's short form is one of them (``Q:``). Which field holds that signature differs:
    ``sale.order`` and ``stock.picking`` sign into ``l10n_pt_inalterable_hash``, while
    ``account.move`` rides core accounting's ``inalterable_hash``. ``_l10n_pt_hash_field`` names it,
    so the builder can be shared without moving any model off the hash it already uses.

    Models mixing this in must implement:
      - ``_l10n_pt_get_saft_doc_type``: the SAF-T (PT) type code printed in ``D:``.
    They may override:
      - ``_l10n_pt_qr_get_totals``: the ``N:`` and ``O:`` amounts, 0 by default.
      - ``_l10n_pt_get_tax_details_by_region``: the base and VAT per tax region and category,
        filled from ``tax_totals`` by default and overridden to nothing by documents that carry
        no amounts.
      - ``_l10n_pt_qr_get_withholding_amount``: the ``P:`` amount, 0 by default.
      - ``_l10n_pt_qr_rate_date``: the date whose exchange rate converts amounts to EUR.
    """
    _name = 'l10n.pt.qr.document.mixin'
    _description = "Portuguese AT Document (QR code)"
    _inherit = ['l10n.pt.document.mixin']

    # Field holding the document's signature. Overridden per model, as `_l10n_pt_date_field` is.
    _l10n_pt_hash_field = 'l10n_pt_inalterable_hash'

    l10n_pt_qr_code_str = fields.Char(
        string="Portuguese QR Code",
        compute='_compute_l10n_pt_qr_code_str',
        store=True,
    )
    l10n_pt_inalterable_hash_short = fields.Char(
        string="Short version of the Portuguese hash",
        compute='_compute_l10n_pt_inalterable_hash_info',
    )
    l10n_pt_inalterable_hash_version = fields.Integer(
        string="Portuguese hash version",
        compute='_compute_l10n_pt_inalterable_hash_info',
    )

    ####################################
    # HOOKS (to be implemented by models)
    ####################################

    def _l10n_pt_get_saft_doc_type(self):
        """SAF-T (PT) document type code used in the QR code ``D:`` field."""
        raise NotImplementedError

    def _l10n_pt_qr_get_totals(self):
        """The ``(N, O)`` amounts (tax total, grand total), formatted for the QR code."""
        self.ensure_one()
        return "0.00", "0.00"

    def _l10n_pt_qr_get_withholding_amount(self):
        """The tax withheld at source on the document, in document currency, for the ``P:`` field."""
        self.ensure_one()
        return 0.0

    def _l10n_pt_qr_rate_date(self):
        """
        The date whose exchange rate converts the QR amounts to EUR.

        Defaults to the document date, which is also what the signature and the ``F:`` field use.
        """
        self.ensure_one()
        return self._l10n_pt_get_document_date()

    ####################################
    # SHARED LOGIC
    ####################################

    def _l10n_pt_get_inalterable_hash(self):
        """The document's signature, wherever this model happens to keep it."""
        self.ensure_one()
        return self[self._l10n_pt_hash_field]

    @api.depends(lambda self: (self._l10n_pt_hash_field,))
    def _compute_l10n_pt_inalterable_hash_info(self):
        for record in self:
            if inalterable_hash := record._l10n_pt_get_inalterable_hash():
                hash_version, hash_str = inalterable_hash.split("$")[1:]
                record.l10n_pt_inalterable_hash_version = int(hash_version)
                record.l10n_pt_inalterable_hash_short = hash_str[0] + hash_str[10] + hash_str[20] + hash_str[30]
            else:
                record.l10n_pt_inalterable_hash_version = False
                record.l10n_pt_inalterable_hash_short = False

    def _l10n_pt_amount_to_eur(self, amount):
        """
        Convert an amount to EUR at the rate of `_l10n_pt_qr_rate_date`. A document in another
        currency is signed, coded in the QR and exported in EUR (Despacho 8632/2014 2.1.7), all
        converted here.
        """
        self.ensure_one()
        return self.currency_id._convert(
            amount, self.env.ref('base.EUR'), self.company_id, self._l10n_pt_qr_rate_date(),
        )

    def _l10n_pt_qr_format_amount(self, amount):
        """Convert an amount to EUR, and format it to 2 decimals as SAF-T (PT) requires."""
        self.ensure_one()
        return float_repr(self._l10n_pt_amount_to_eur(amount), 2)

    def _l10n_pt_get_tax_region(self, tax_group):
        """The region a tax of ``tax_group`` is levied in: a tax valid in all regions (PT, PT-AC,
        PT-MA) is levied in the company's own."""
        region = tax_group.l10n_pt_tax_region
        return self.company_id.l10n_pt_region_code if not region or region == 'PT-ALL' else region

    def _l10n_pt_get_tax_details_by_region(self):
        """
        The document's base and VAT amounts, per tax region and AT tax category, in document
        currency. The company's own region comes first, as the QR code's I block.

        :return: {tax_region: {tax_category: {'base': base, 'vat': vat}}}
        """
        self.ensure_one()
        company_region = self.company_id.l10n_pt_region_code
        res = defaultdict(lambda: defaultdict(lambda: {'base': 0.0, 'vat': 0.0}))
        for subtotal in self.tax_totals['subtotals']:
            for group in subtotal['tax_groups']:
                tax_group = self.env['account.tax.group'].browse(group['id'])
                details = res[self._l10n_pt_get_tax_region(tax_group)][tax_group.l10n_pt_tax_category]
                details['base'] += group['base_amount_currency']
                details['vat'] += group['tax_amount_currency']
        # `sorted` is stable: the other regions keep the order of the tax groups.
        return {
            region: dict(details)
            for region, details in sorted(res.items(), key=lambda item: item[0] != company_region)
        }

    def _l10n_pt_qr_add_tax_details(self, qr_code_dict):
        """
        Add one block per tax region to the QR code: its region, then its base and VAT per tax
        category, in the I, J and K blocks; a document without VAT has the single entry ``I1:0``
        (QR code specification v1.1, sections 3 and 4). Tax groups know three regions (PT, PT-AC,
        PT-MA), the three blocks the QR code has room for. The bases not subject to VAT (category
        ``L``, see ``PT_QR_NOT_SUBJECT_EXEMPTION_REASONS``) are added up over the regions into
        ``L:``.
        """
        self.ensure_one()
        details_by_region = self._l10n_pt_get_tax_details_by_region()
        if not details_by_region:
            qr_code_dict['I1:'] = "0*"
            return
        not_subject_base = 0.0
        for letter, (region, details) in zip('IJK', details_by_region.items()):
            qr_code_dict[f'{letter}1:'] = f"{region}*"
            if details.get('E'):
                qr_code_dict[f'{letter}2:'] = f"{self._l10n_pt_qr_format_amount(details['E']['base'])}*"
            for i, tax_category in enumerate(('R', 'I', 'N')):
                if category_details := details.get(tax_category):
                    qr_code_dict[f'{letter}{i * 2 + 3}:'] = f"{self._l10n_pt_qr_format_amount(category_details['base'])}*"
                    qr_code_dict[f'{letter}{i * 2 + 4}:'] = f"{self._l10n_pt_qr_format_amount(category_details['vat'])}*"
            if details.get('L'):
                not_subject_base += details['L']['base']
        if not_subject_base:
            qr_code_dict['L:'] = f"{self._l10n_pt_qr_format_amount(not_subject_base)}*"

    def l10n_pt_verify_prerequisites_qr_code(self):
        self.ensure_one()
        if self._l10n_pt_country_ok():
            return pt_hash_utils.verify_prerequisites_qr_code(
                self, self._l10n_pt_get_inalterable_hash(), self.l10n_pt_atcud,
            )
        return None

    @api.depends(lambda self: (self._l10n_pt_hash_field,))
    def _compute_l10n_pt_qr_code_str(self):
        """
        Generate the informational QR code for Portugal.
        E.g.: A:509445535*B:123456823*C:BE*D:FT*E:N*F:20220103*G:FT 01P2022/1*H:0*I1:PT*I7:325.20*I8:74.80*N:74.80*O:400.00*P:0.00*Q:P0FE*R:2230
        """
        for record in self.filtered(lambda r: (
            r._l10n_pt_country_ok()
            and r._l10n_pt_get_inalterable_hash()
            and not r.l10n_pt_qr_code_str  # Skip if already computed
        )):
            record.l10n_pt_verify_prerequisites_qr_code()
            # Most of the values needed to create the QR code string are filled in pt_hash_utils
            qr_code_dict = pt_hash_utils.l10n_pt_common_qr_code_str(record, self.env, record._l10n_pt_get_document_date())
            qr_code_dict['D:'] = f"{record._l10n_pt_get_saft_doc_type()}*"
            qr_code_dict['H:'] = f"{record.l10n_pt_atcud}*"
            record._l10n_pt_qr_add_tax_details(qr_code_dict)
            n_amount, o_amount = record._l10n_pt_qr_get_totals()
            qr_code_dict['N:'] = f"{n_amount}*"
            qr_code_dict['O:'] = f"{o_amount}*"
            if withholding_amount := record._l10n_pt_qr_get_withholding_amount():
                qr_code_dict['P:'] = f"{record._l10n_pt_qr_format_amount(withholding_amount)}*"
            qr_code_dict['Q:'] = f"{record.l10n_pt_inalterable_hash_short}*"
            # Create QR code string from dictionary. It is stored as is, the content the QR code encodes
            # (the PoS encodes it client-side): it is URL-encoded only where it goes into a URL.
            record.l10n_pt_qr_code_str = ''.join(f"{key}{value}" for key, value in sorted(qr_code_dict.items()))


class L10nPtHashedDocumentMixin(models.AbstractModel):
    """
    Shared signing & QR-code layer for Portuguese documents that must be cryptographically
    secured (``sale.order`` and ``stock.picking``; ``account.move`` keeps riding the base
    ``account`` hashing framework and is intentionally not built on this mixin).

    On top of the numbering and QR layers, this groups: the inalterability hash (RSA signature
    chained with the previous document), the write-lock protecting hashed fields, the batch signing
    routine and the chain-walking integrity report.

    Models mixing this in must implement, in addition to ``_l10n_pt_get_document_date``:
      - ``_l10n_pt_get_unhashed_records`` / ``_l10n_pt_find_last_hashed``: chain boundaries.
      - ``_l10n_pt_document_label``: how the integrity report names this document family.
    They may override the hooks ``_l10n_pt_get_gross_total``, ``_l10n_pt_post_hash_hook`` and
    ``_l10n_pt_chain_domain``, plus those of ``l10n.pt.qr.document.mixin``.
    """
    _name = 'l10n.pt.hashed.document.mixin'
    _description = "Portuguese AT Document (signed & QR code)"
    _inherit = ['l10n.pt.qr.document.mixin']

    l10n_pt_inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    # Indexed for the latest SystemEntryDate, read before issuing any document (`_l10n_pt_check_system_clock`).
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True, index='btree_not_null')
    # The chain follows this integer, never the document-number string, which sorts .../100000
    # before .../99999 (`account.move` chains on core's `sequence_number` instead).
    l10n_pt_sequence_number = fields.Integer(
        string="Number in Series",
        compute='_compute_l10n_pt_sequence_number',
        store=True,
        copy=False,
    )

    _l10n_pt_series_sequence_idx = models.Index('(l10n_pt_at_series_id, l10n_pt_sequence_number)')

    ####################################
    # HOOKS (to be implemented by models)
    ####################################

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

    @api.depends('l10n_pt_document_number')
    def _compute_l10n_pt_sequence_number(self):
        for record in self:
            record.l10n_pt_sequence_number = record._l10n_pt_get_sequence_number() if record.l10n_pt_document_number else 0

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
            **pt_hash_utils.format_hash_values(record._l10n_pt_get_hash_values()),
            'previous_signature': previous_hash,
        } for record in self]
        return pt_hash_utils.sign_records(self.env, docs_to_sign, self._name)

    def _l10n_pt_compute_missing_hashes(self, company=None):
        """
        Compute the hash/ATCUD for all records that do not have one yet
        (because they were not printed/previewed yet).

        Called on records (a print, a send), it signs the series of each record's own company,
        whichever company is active; called on the model, those of ``company``, the active one by
        default.
        """
        companies = company or self.company_id or self.env.company

        # Get all AT series that apply to this model to find unhashed records per series
        # `active` on l10n_pt.at.series is a validity window (date_end >= today), not an archive
        # flag, but the ORM still injects it into every search. Expired series must stay visible
        # here: documents issued before a series ended still have to be signed and verified.
        at_series_model = self.env['l10n_pt.at.series'].with_context(active_test=False)
        at_series_records = at_series_model.browse()
        for company in companies:
            at_series_records |= at_series_model.search([
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
    # INTEGRITY REPORT
    ####################################

    def _l10n_pt_chain_domain(self, at_series):
        """The hashed records of ``at_series`` that make up this model's signature chain."""
        return [
            ('l10n_pt_at_series_id', '=', at_series.id),
            ('l10n_pt_inalterable_hash', '!=', False),
        ]

    def _l10n_pt_document_label(self, at_series):
        """
        How this document family is named in the integrity report, as
        ``(singular, plural, sentence_plural)`` -- e.g. ``("sales order", "sales orders", "Sales Orders")``.

        A series can hold more than one family on the same model (a ``sale.order`` is a quotation or
        a sales order depending on its series), hence the argument.
        """
        raise NotImplementedError

    def _l10n_pt_verify_hashed_document(self, record, previous_hash, versioning_list, current_versioning_index):
        """Whether ``record``'s signature still matches the values it was signed over."""
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        try:
            message = pt_hash_utils.get_message_to_hash(record._l10n_pt_get_hash_values(), previous_hash)
            return pt_hash_utils.verify_integrity(
                message, record.l10n_pt_inalterable_hash, versioning_list[current_versioning_index],
            )
        except AccessError as e:
            raise UserError(self.env._(
                "This company has AT Series shared across branches, and other companies also have hashed documents under this series. "
                "To generate the report, please also select %s in the company selector.", e.context['suggested_company']['display_name']))

    def _l10n_pt_check_hash_integrity(self, company):
        """
        Walk every AT series chain of this model for ``company`` and report each one's integrity.

        One walker for every signed document family: the walk, the batching and the report keys are
        identical, and only the chain domain and the wording differ, through the two hooks above.
        Called from the thin per-model entry points on ``res.company``, which the server actions,
        the report handlers and the tests address.
        """
        self.env[self._name]._l10n_pt_compute_missing_hashes(company)

        results = []

        # `active` on l10n_pt.at.series is a validity window (date_end >= today), not an archive
        # flag, but the ORM still injects it into every search. Expired series must stay visible
        # here: documents issued before a series ended still have to be signed and verified.
        at_series_model = self.env['l10n_pt.at.series']
        at_series_records = at_series_model.with_context(active_test=False).search([
            *at_series_model._l10n_pt_company_domain(company),
            ('document_type', 'in', self._l10n_pt_series_document_types()),
        ])

        for at_series in at_series_records:
            singular, plural, sentence_plural = self._l10n_pt_document_label(at_series)
            query = self.sudo()._search(
                domain=self._l10n_pt_chain_domain(at_series),
                order="l10n_pt_sequence_number",
            )

            first_record = last_record = corrupted_record = self.browse()

            self.env.execute_query(SQL("DECLARE l10n_pt_hashed_documents CURSOR FOR %s", query.select()))
            while record_ids := self.env.execute_query(SQL("FETCH %s FROM l10n_pt_hashed_documents", INTEGRITY_HASH_BATCH_SIZE)):
                self.env.invalidate_all()
                records = self.browse([record_id[0] for record_id in record_ids])
                if not records and not last_record:
                    # Unreachable: the loop body only runs on a non-empty fetch, so `records` is
                    # never empty here, and a series with nothing hashed reports nothing at all.
                    # Carried over as it stands rather than repaired, so that folding the two
                    # walkers into one changes no report output.
                    results.append({
                        'series_at_code': at_series.at_code,
                        'status': 'no_data',
                        'msg_cover': self.env._('No %(doc_type)s found for this AT series.', doc_type=plural),
                    })
                    continue

                current_versioning_index = 0
                versioning_list = company._get_hash_versioning_list()
                for record in records:
                    if corrupted_record:
                        continue
                    if not self._l10n_pt_verify_hashed_document(
                        record, last_record.l10n_pt_inalterable_hash, versioning_list, current_versioning_index
                    ):
                        corrupted_record = record
                        continue
                    first_record = first_record or record
                    last_record = record

            self.env.execute_query(SQL("CLOSE l10n_pt_hashed_documents"))
            if corrupted_record:
                results.append({
                    'series_document_identifier': at_series.document_identifier,
                    'series_at_code': at_series._get_at_code(),
                    'status': 'corrupted',
                    'msg_cover': self.env._(
                        "Corrupted data on %(doc_type)s with id %(id)s (%(name)s).",
                        doc_type=singular,
                        id=corrupted_record.id,
                        name=corrupted_record.l10n_pt_document_number,
                    ),
                })
            elif first_record and last_record:
                results.append({
                    'series_document_identifier': at_series.document_identifier,
                    'series_at_code': at_series._get_at_code(),
                    'status': 'verified',
                    'msg_cover': self.env._("%(doc_type)s are correctly hashed", doc_type=sentence_plural),
                    'first_hash': first_record.l10n_pt_inalterable_hash,
                    'first_name': first_record.name,
                    'first_document_number': first_record.l10n_pt_document_number,
                    'first_date': first_record._l10n_pt_get_document_date(),
                    'last_hash': last_record.l10n_pt_inalterable_hash,
                    'last_name': last_record.name,
                    'last_document_number': last_record.l10n_pt_document_number,
                    'last_date': last_record._l10n_pt_get_document_date(),
                })

        return {
            'results': results,
            'printing_date': format_date(self.env, fields.Date.context_today(company)),
        }
