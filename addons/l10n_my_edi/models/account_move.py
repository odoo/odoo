# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    # ------------------
    # Fields declaration
    # ------------------

    l10n_my_edi_document_ids = fields.Many2many(
        name="MyInvois Documents",
        comodel_name="myinvois.document",
        relation="myinvois_document_invoice_rel",
        column1="invoice_id",
        column2="document_id",
        copy=False,
    )
    l10n_my_edi_display_tax_exemption_reason = fields.Boolean(
        compute='_compute_l10n_my_edi_display_tax_exemption_reason',
        string="Display Tax Exemption Reason",
        export_string_translation=False,
    )
    l10n_my_invoice_need_edi = fields.Boolean(
        compute='_compute_l10n_my_invoice_need_edi',
        export_string_translation=False,
    )
    l10n_my_edi_state = fields.Selection(
        string='MyInvois State',
        help='State of this document on the MyInvois portal.\nA document awaiting validation will be automatically updated once the validation status is available.',
        selection=[
            ('in_progress', 'Validation In Progress'),
            ('valid', 'Valid'),
            ('rejected', 'Rejected'),
            ('invalid', 'Invalid'),
            ('cancelled', 'Cancelled'),
        ],
        compute='_compute_l10n_my_edi_state',
        store=True,
        tracking=True,
        export_string_translation=False,
    )
    # Fields required to be set on the document in some cases.
    l10n_my_edi_exemption_reason = fields.Char(
        string="Tax Exemption Reason",
        help="Buyer’s sales tax exemption certificate number, special exemption as per gazette orders, etc.\n"
             "Only applicable if you are using a tax with a type 'Exempt'.",
    )
    l10n_my_edi_custom_form_reference = fields.Char(
        string="Customs Form Reference Number",
        help="Reference Number of Customs Form No.1, 9, etc.",
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('l10n_my_edi_document_ids.myinvois_state')
    def _compute_l10n_my_edi_state(self):
        for move in self:
            myinvois_document = move._get_active_myinvois_document(including_in_progress=True)
            if not myinvois_document:
                move.l10n_my_edi_state = False

            move.l10n_my_edi_state = myinvois_document.myinvois_state

    @api.depends('l10n_my_edi_state')
    def _compute_need_cancel_request(self):
        # EXTENDS 'account'
        super()._compute_need_cancel_request()

    @api.depends('l10n_my_edi_state')
    def _compute_show_reset_to_draft_button(self):
        # EXTEND 'account'
        super()._compute_show_reset_to_draft_button()
        # If the state is set, it means that we have an active document; and thus we need cancellation.
        self.filtered(lambda m: m.l10n_my_edi_state).show_reset_to_draft_button = False

    @api.depends('l10n_my_invoice_need_edi', 'l10n_my_edi_state')
    def _compute_highlight_send_button(self):
        # EXTENDS 'account' to not highlight the "Send" button when the "Send To MyInvois" button is available to have just one call to action.
        super()._compute_highlight_send_button()
        for move in self:
            if move.l10n_my_invoice_need_edi:
                move.highlight_send_button &= move.l10n_my_edi_state == 'valid'

    @api.depends('company_id', 'invoice_line_ids.tax_ids')
    def _compute_l10n_my_edi_display_tax_exemption_reason(self):
        """ Some users will never use tax-exempt taxes, so it's better to only show the field when necessary. """
        moves_per_proxy_users = self.grouped(lambda m: m._l10n_my_edi_get_proxy_user())
        for proxy_user, moves in moves_per_proxy_users.items():
            for move in moves:
                should_display = proxy_user and any(tax.l10n_my_tax_type == 'E' for tax in move.invoice_line_ids.tax_ids)
                move.l10n_my_edi_display_tax_exemption_reason = should_display

    @api.depends('move_type', 'state', 'country_code', 'l10n_my_edi_state', 'company_id')
    def _compute_l10n_my_invoice_need_edi(self):
        for move in self:
            # We return true for malaysian invoices which are not sent yet, sent but awaiting validation or valid.
            move.l10n_my_invoice_need_edi = bool(
                move.is_invoice()
                and move.state == 'posted'
                and move.country_code == 'MY'
                and move.l10n_my_edi_state in (False, 'in_progress', 'valid')
                and move._l10n_my_edi_get_proxy_user(),
            )

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def button_request_cancel(self):
        # EXTENDS 'account'
        super().button_request_cancel()

        active_myinvois_document = self._get_active_myinvois_document()
        if self._need_cancel_request() and active_myinvois_document:
            return active_myinvois_document.action_cancel_submission()

        return super().button_request_cancel()

    def _get_fields_to_detach(self):
        # EXTENDS account
        fields_list = super()._get_fields_to_detach()
        fields_list.append('l10n_my_edi_file')
        return fields_list

    def _need_cancel_request(self):
        # EXTENDS 'account'
        # For the in_progress state, we do not want to allow resetting to draft nor cancelling. We need to wait for the result first.
        return super()._need_cancel_request() or self._get_active_myinvois_document()

    def _get_name_invoice_report(self):
        # EXTENDS 'account'
        # Meaning we are a myinvois invoice, meaning we need to embed the qr code.
        if self._get_active_myinvois_document():
            return 'l10n_my_edi.report_invoice_document'
        return super()._get_name_invoice_report()

    # --------------
    # Action methods
    # --------------

    def action_l10n_my_edi_update_status(self):
        self.ensure_one()
        self.l10n_my_edi_document_ids._get_active_myinvois_document(including_in_progress=True).action_update_submission_status()

    def action_invoice_sent(self):
        """ The wizard should not be available for invoices sent to MyInvois but not yet validated.
        This is because before validation the ID used for the QR code is not available and the user should NOT send the invoice yet.
        """
        self.ensure_one()

        if self.l10n_my_edi_state == 'in_progress':
            raise UserError(self.env._('You cannot send invoices that are currently being validated.\nPlease wait for the validation to complete.'))

        return super().action_invoice_sent()

    def action_l10n_my_edi_send_invoice(self):
        """
        This action will create the MyInvois Document for this invoice if it does not already exist.
        Once done, it will trigger the sending of said document to the platform.
        """
        invoice_needing_new_document = self.env['account.move']
        myinvois_documents = self.env['myinvois.document']
        for move in self.filtered(lambda m: m.state == 'posted'):
            # It already has a valid document active on the platform, we don't want to send it again.
            if move.l10n_my_edi_state:
                continue

            # On the other hand, if we already have a document in draft, or an invalid document, we allow sending it.
            if valid_document := move.l10n_my_edi_document_ids.filtered(lambda d: d.myinvois_state in [False, 'invalid']):
                myinvois_documents |= valid_document
            else:
                # If we don't have any valid documents, we'll create a new one.
                invoice_needing_new_document |= move

        myinvois_documents |= invoice_needing_new_document._create_myinvois_document()

        if myinvois_documents:
            myinvois_documents._submit_to_myinvois()

    def action_show_myinvois_documents(self):
        return self.l10n_my_edi_document_ids.action_show_myinvois_documents()

    # ----------------
    # Business methods
    # ----------------

    def _create_myinvois_document(self):
        """ Helper which creates and link one MyInvois Document per invoice in self. """
        myinvois_documents_vals = []
        for move in self.filtered(lambda m: m.state == 'posted'):
            myinvois_documents_vals.append({
                'name': move.name,
                'company_id': move.company_id.id,
                'currency_id': move.currency_id.id,
                'myinvois_issuance_date': move.invoice_date,
                'invoice_ids': [Command.link(move.id)],
                'myinvois_exemption_reason': move.l10n_my_edi_exemption_reason,
                'myinvois_custom_form_reference': move.l10n_my_edi_custom_form_reference,
            })
        return self.env['myinvois.document'].create(myinvois_documents_vals)

    def _l10n_my_edi_get_proxy_user(self):
        """
        Helper to retrieve the proxy user related to the company of the record.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        return company.sudo().l10n_my_edi_proxy_user_id

    def _l10n_my_edi_cancel_moves(self):
        """ Try to cancel the moves in self if allowed by the lock date. """
        for move in self:
            try:
                move._check_fiscal_lock_dates()
                move.line_ids._check_tax_lock_date()
                move.button_cancel()
            except UserError as e:
                move.with_context(no_new_invoice=True).message_post(
                    body=self.env._(
                        'The invoice has been canceled on MyInvois, '
                        'But the cancellation in Odoo failed with error: %(error)s\n'
                        'Please resolve the problem manually, and then cancel the invoice.',
                        error=e,
                    ),
                )

    def _generate_myinvois_qr_code(self):
        self.ensure_one()

        myinvois_document = self._get_active_myinvois_document()
        if not myinvois_document or not myinvois_document.myinvois_document_long_id:
            return None

        return myinvois_document._generate_myinvois_qr_code()

    def _get_active_myinvois_document(self, including_in_progress=False):
        """ Shortcut to get the active document of all invoice in self. """
        return self.env['myinvois.document'].union(*[invoice.l10n_my_edi_document_ids._get_active_myinvois_document(including_in_progress) for invoice in self])
