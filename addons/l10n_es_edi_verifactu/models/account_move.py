from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_edi_verifactu_required = fields.Boolean(
        string="Veri*Factu Required",
        compute='_compute_l10n_es_edi_verifactu_required',
    )
    l10n_es_edi_verifactu_document_ids = fields.One2many(
        comodel_name='l10n_es_edi_verifactu.document',
        inverse_name='res_id',
        string="Veri*Factu Documents",
    )
    l10n_es_edi_verifactu_state = fields.Selection(
        string="Veri*Factu Status",
        selection=[
            ('rejected', "Rejected"),
            ('registered_with_errors', "Registered with Errors"),
            ('accepted', "Accepted"),
            ('cancelled', "Cancelled"),
        ],
        compute='_compute_l10n_es_edi_verifactu_info_from_document_ids',
        help="""- Rejected: Successfully sent to the AEAT, but it was rejected during validation
                - Registered with Errors: Registered at the AEAT, but the AEAT has some issues with the sent document
                - Accepted: Registered by the AEAT without errors
                - Cancelled: Registered by the AEAT as cancelled""",
        store=True,
        tracking=True,
    )
    l10n_es_edi_verifactu_last_erroneous_document_id = fields.Many2one(
        comodel_name='l10n_es_edi_verifactu.document',
        compute='_compute_l10n_es_edi_verifactu_info_from_document_ids',
        string="Last Erroneous Veri*Factu Document",
        help="This QR code is mandatory for Veri*Factu invoices.",
        store=True,
    )
    l10n_es_edi_verifactu_error_level = fields.Selection(
        string="Veri*Factu Error Level",
        related="l10n_es_edi_verifactu_last_erroneous_document_id.state",
        store=True,
    )
    l10n_es_edi_verifactu_errors = fields.Html(
        string="Veri*Factu Errors",
        related="l10n_es_edi_verifactu_last_erroneous_document_id.errors",
    )
    l10n_es_edi_verifactu_qr_code = fields.Char(
        string="Veri*Factu QR Code",
        compute='_compute_l10n_es_edi_verifactu_qr_code',
        help="This QR code is mandatory for Veri*Factu invoices.",
    )
    l10n_es_edi_verifactu_show_cancel_button = fields.Boolean(
        string="Show Veri*Factu Cancel Button",
        compute='_compute_l10n_es_edi_verifactu_show_cancel_button',
    )

    @api.depends('country_code')
    def _compute_l10n_es_edi_verifactu_required(self):
        for move in self:
            move.l10n_es_edi_verifactu_required = move.country_code == 'ES' and move.company_id.l10n_es_edi_verifactu_required

    @api.depends('l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.state')
    def _compute_l10n_es_edi_verifactu_info_from_document_ids(self):
        for record in self:
            documents_info = self.env['l10n_es_edi_verifactu.document']._analyze_record_documents(record)
            record.l10n_es_edi_verifactu_last_erroneous_document_id = documents_info['last_erroneous_document']
            record.l10n_es_edi_verifactu_state = documents_info['state']

    @api.depends('l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.record_identifier')
    def _compute_l10n_es_edi_verifactu_qr_code(self):
        for record in self:
            url = self.env['l10n_es_edi_verifactu.document']._get_qr_code_img_url(record)
            record.l10n_es_edi_verifactu_qr_code = url

    @api.depends('l10n_es_edi_verifactu_state')
    def _compute_l10n_es_edi_verifactu_show_cancel_button(self):
        for move in self:
            move.l10n_es_edi_verifactu_show_cancel_button = move.l10n_es_edi_verifactu_state in ('registered_with_errors', 'accepted')

    @api.depends('l10n_es_edi_verifactu_state', 'l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.state')
    def _compute_show_reset_to_draft_button(self):
        """
        Disallow resetting to draft in the following cases:
        * The move is registered with the AEAT
        * We are waiting to sent a document (registration) to the AEAT
        """
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_es_edi_verifactu_state in ('registered_with_errors', 'accepted'):
                move.show_reset_to_draft_button = False
                continue
            waiting_documents = move.l10n_es_edi_verifactu_document_ids.filtered(lambda rd: not rd.state)
            if waiting_documents:
                move.show_reset_to_draft_button = False

    def _l10n_es_edi_verifactu_record_identifier(self):
        self.ensure_one()
        last_submission_document = self.l10n_es_edi_verifactu_document_ids.filtered(
            lambda rd: rd.document_type == 'submission'
        ).sorted()[:1]
        return last_submission_document.record_identifier

    def l10n_es_edi_verifactu_button_cancel(self):
        created_documents = self.env['l10n_es_edi_verifactu.document'].mark_records_for_next_batch(self, cancellation=True)
        skipped_moves = self.filtered(lambda move: not created_documents.get(move))
        if skipped_moves and len(self) == 1:
            raise UserError(_("We are waiting to send a Veri*Factu record to the AEAT already."))
        # In other cases we just silently skip them

    def _l10n_es_edi_verifactu_get_record_values(self, cancellation=False):
        self.ensure_one()
        errors = []

        if self.state != 'posted':
            errors.append(_("The journal entry has to be posted."))
            return {}, errors

        documents_info = self.env['l10n_es_edi_verifactu.document']._analyze_record_documents(self)
        document_type = 'cancellation' if cancellation else 'submission'
        rejected_before = bool(documents_info[f'last_rejected_{document_type}'])

        vals = {
            'cancellation': cancellation,
            'record': self,
            'rejected_before': rejected_before,
            'verifactu_state': self.l10n_es_edi_verifactu_state,
            'company': self.company_id,
            'delivery_date': self.delivery_date,
            'description': self.invoice_origin[:500] if self.invoice_origin else None,
            'invoice_date': self.invoice_date,
            'is_simplified': self.l10n_es_is_simplified,
            'move_type': self.move_type,
            'name': self.name,
            'partner': self.commercial_partner_id,
            'refunded_record': self.reversed_entry_id,
        }

        tax_details_functions = self.env['account.tax']._l10n_es_edi_verifactu_get_tax_details_functions()

        vals['tax_details'] = self._prepare_invoice_aggregated_taxes(
            filter_invl_to_apply=tax_details_functions['full_filter_invl_to_apply'],
            filter_tax_values_to_apply=tax_details_functions['filter_to_apply'],
            grouping_key_generator=tax_details_functions['grouping_key_generator'],
        )

        return vals, errors
