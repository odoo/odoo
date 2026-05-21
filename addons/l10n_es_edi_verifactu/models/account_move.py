from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_edi_verifactu_required = fields.Boolean(
        string="Veri*Factu Required",
        related='company_id.l10n_es_edi_verifactu_required',
    )
    l10n_es_edi_verifactu_document_ids = fields.One2many(
        comodel_name='l10n_es_edi_verifactu.document',
        inverse_name='move_id',
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
        compute='_compute_l10n_es_edi_verifactu_state', store=True,
        help="""- Rejected: Successfully sent to the AEAT, but it was rejected during validation
                - Registered with Errors: Registered at the AEAT, but the AEAT has some issues with the sent document
                - Accepted: Registered by the AEAT without errors
                - Cancelled: Registered by the AEAT as cancelled""",
    )
    l10n_es_edi_verifactu_warning_level = fields.Char(
        string="Veri*Factu Warning Level",
        compute="_compute_l10n_es_edi_verifactu_warning",
    )
    l10n_es_edi_verifactu_warning = fields.Html(
        string="Veri*Factu Warning",
        compute="_compute_l10n_es_edi_verifactu_warning",
    )
    l10n_es_edi_verifactu_qr_code = fields.Char(
        string="Veri*Factu QR Code",
        compute='_compute_l10n_es_edi_verifactu_qr_code',
    )
    l10n_es_edi_verifactu_substituted_entry_id = fields.Many2one(
        comodel_name='account.move',
        string="Substitution of",
        index='btree_not_null',
        readonly=True,
        copy=False,
        check_company=True,
    )
    l10n_es_edi_verifactu_substitution_move_ids = fields.One2many(
        string="Substituted by",
        comodel_name='account.move',
        inverse_name='l10n_es_edi_verifactu_substituted_entry_id',
    )

    def _l10n_es_edi_verifactu_get_tax_applicability(self):
        """
        Currently we only support a single Veri*Factu Tax Applicability per Veri*Factu document.
        In `_check_record_values` of model 'l10n_es_edi_verifactu.document' we check:
        There is only a single Veri*Factu Tax Applicability on the whole move.
        """
        self.ensure_one()
        if not self.l10n_es_edi_verifactu_required:
            return False

        taxes = self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy()
        return taxes._l10n_es_edi_verifactu_get_applicability()

    @api.depends('l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.state')
    def _compute_l10n_es_edi_verifactu_state(self):
        for move in self:
            state = move.l10n_es_edi_verifactu_document_ids._get_state()
            move.l10n_es_edi_verifactu_state = state

    @api.depends('l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.json_attachment_id')
    def _compute_l10n_es_edi_verifactu_qr_code(self):
        for move in self:
            last_submission = move.l10n_es_edi_verifactu_document_ids._get_last('submission')
            url = last_submission._get_qr_code_img_url() if last_submission else False
            move.l10n_es_edi_verifactu_qr_code = url

    @api.depends('state', 'l10n_es_edi_verifactu_state', 'l10n_es_edi_verifactu_document_ids',
                 'l10n_es_edi_verifactu_document_ids.state', 'l10n_es_edi_verifactu_document_ids.errors')
    def _compute_l10n_es_edi_verifactu_warning(self):
        for move in self:
            last_document = move.l10n_es_edi_verifactu_document_ids.sorted()[:1]

            warning = False
            warning_level = False
            if last_document.state == 'registered_with_errors':
                warning = last_document.errors
                warning_level = 'warning'
            elif last_document.errors:
                warning = last_document.errors
                warning_level = 'danger'
            elif move.state == 'draft':
                if move.l10n_es_edi_verifactu_state:
                    warning = _("You are modifying a journal entry for which a Veri*Factu document has been sent to the AEAT already.")
                    warning_level = 'warning'
                elif last_document._filter_waiting():
                    warning = _("You are modifying a journal entry for which a Veri*Factu document is waiting to be sent.")
                    warning_level = 'warning'

            if last_document._filter_waiting():
                warning = _("%(existing_warning)sA Veri*Factu document is waiting to be sent as soon as possible.",
                            existing_warning=(warning + '\n' if warning else ''))
                warning_level = warning_level or 'info'

            move.l10n_es_edi_verifactu_warning = warning
            move.l10n_es_edi_verifactu_warning_level = warning_level

    @api.depends('l10n_es_edi_verifactu_state', 'l10n_es_edi_verifactu_document_ids',
                 'l10n_es_edi_verifactu_document_ids.state', 'l10n_es_edi_verifactu_document_ids.json_attachment_id')
    def _compute_show_reset_to_draft_button(self):
        """
        Disallow resetting to draft in the following cases:
        * The move is registered (accepted, regsitered_with_errors, cancelled)
        * We are waiting to sent a document to the AEAT
        """
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if (move.l10n_es_edi_verifactu_state in ('registered_with_errors', 'accepted', 'cancelled')
                or move.l10n_es_edi_verifactu_document_ids._filter_waiting()):
                move.show_reset_to_draft_button = False

    @api.model
    def _l10n_es_edi_verifactu_action_go_to_journal_entry(self, move):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': move.id,
            'views': [(self.env.ref('account.view_move_form').id, 'form')],
            'context': self.env.context,
        }

    def l10n_es_edi_verifactu_button_cancel(self):
        if self.l10n_es_edi_verifactu_state not in ('registered_with_errors', 'accepted'):
            raise ValidationError(self.env._(
                "Veri*Factu Cancellation Request is only allowed for the invoice in either 'Registered with Errors' or 'Accepted' Veri*Factu Status."
            ))
        self._l10n_es_edi_verifactu_mark_for_next_batch(cancellation=True)

    def _l10n_es_edi_verifactu_check(self, cancellation=False):
        self.ensure_one()
        errors = []

        if self.state != 'posted':
            errors.append(_("The journal entry has to be posted."))

        return errors

    def _l10n_es_edi_verifactu_get_record_values(self, cancellation=False):
        self.ensure_one()

        company = self.company_id
        obligado_partner = self._l10n_es_edi_verifactu_get_obligado_partner()
        document_type = 'cancellation' if cancellation else 'submission'
        vals = {
            'company': company,
            'record': self,
            'obligado_partner': obligado_partner,
            'cancellation': cancellation,
            'is_self_billing': self.journal_id.is_self_billing,
            'errors': self._l10n_es_edi_verifactu_check(cancellation=cancellation),
            'document_vals': {
                'move_id': self.id,
                'company_id': company.id,
                'obligado_partner_id': obligado_partner.id,
                'document_type': document_type,
            },
        }

        if vals['errors']:
            return vals

        documents = self.l10n_es_edi_verifactu_document_ids
        # Just checking whether the last document was rejected is enough; we do not allow to submit the same record
        # again after a cancellation (else we get the error '[3000] Registro de facturación duplicado.').
        rejected_before = documents._get_last(document_type).state == 'rejected'

        tax_applicability = self._l10n_es_edi_verifactu_get_tax_applicability()
        raw_clave = self.l10n_es_vat_regime_code_id
        clave_regimen = raw_clave and raw_clave.split('_', 1)[0]
        substituted_move = self.l10n_es_edi_verifactu_substituted_entry_id
        reversed_move = self.reversed_entry_id

        move_type = self.move_type
        if move_type == 'out_invoice' and substituted_move:
            verifactu_move_type = 'correction_substitution'
        elif move_type in ['out_invoice', 'in_invoice']:
            verifactu_move_type = 'invoice'
        elif move_type == 'out_refund' and reversed_move.l10n_es_edi_verifactu_substitution_move_ids:
            verifactu_move_type = 'reversal_for_substitution'
        else:
            # move_type == 'out_refund' and not reversed_move.l10n_es_edi_verifactu_substitution_move_ids
            verifactu_move_type = 'correction_incremental'

        vals.update({
            'rejected_before': rejected_before,
            'verifactu_state': self.l10n_es_edi_verifactu_state,
            'delivery_date': self.delivery_date,
            'description': self.invoice_origin[:500] if self.invoice_origin else None,
            'invoice_date': self.invoice_date,
            'is_simplified': self.l10n_es_is_simplified,
            'move_type': move_type,
            'verifactu_move_type': verifactu_move_type,
            'sign': -1 if move_type == 'out_refund' else 1,
            'name': self.name,
            'partner': self.commercial_partner_id,
            'invoice_type': self.l10n_es_invoice_type,
            'refunded_document': reversed_move.l10n_es_edi_verifactu_document_ids._get_last('submission'),
            'substituted_document': substituted_move.l10n_es_edi_verifactu_document_ids._get_last('submission'),
            'substituted_document_reversal_document': substituted_move.reversal_move_ids.l10n_es_edi_verifactu_document_ids._get_last('submission'),
            'documents': documents,
            'record_identifier': documents._get_last('submission')._get_record_identifier(),
            'l10n_es_applicability': tax_applicability,
            'clave_regimen': clave_regimen or None,
        })

        base_amls = self.line_ids.filtered(lambda x: x.display_type == 'product')
        base_lines = [self._prepare_product_base_line_for_taxes_computation(x) for x in base_amls]
        epd_amls = self.line_ids.filtered(lambda line: line.display_type == 'epd')
        base_lines += [self._prepare_epd_base_line_for_taxes_computation(line) for line in epd_amls]
        cash_rounding_amls = self.line_ids \
            .filtered(lambda line: line.display_type == 'rounding' and not line.tax_repartition_line_id)
        base_lines += [self._prepare_cash_rounding_base_line_for_taxes_computation(line) for line in cash_rounding_amls]
        tax_amls = self.line_ids.filtered('tax_repartition_line_id')
        tax_lines = [self._prepare_tax_line_for_taxes_computation(x) for x in tax_amls]
        vals['tax_details'] = self.env['l10n_es_edi_verifactu.document']._get_tax_details(base_lines, company, tax_lines=tax_lines)

        return vals

    def _l10n_es_edi_verifactu_create_documents(self, cancellation=False):
        record_values_list = [
            move._l10n_es_edi_verifactu_get_record_values(cancellation=cancellation)
            for move in self
        ]
        return {
            record_values['record']: self.env['l10n_es_edi_verifactu.document']._create_for_record(record_values)
            for record_values in record_values_list
        }

    def _l10n_es_edi_verifactu_mark_for_next_batch(self, cancellation=False):
        document_map = self._l10n_es_edi_verifactu_create_documents(cancellation=cancellation)
        self.env['l10n_es_edi_verifactu.document'].trigger_next_batch()
        return document_map

    # EXTENDS account_move
    @api.depends('move_type', 'state', 'journal_id.is_self_billing')
    def _compute_display_send_button(self):
        super()._compute_display_send_button()
        for move in self:
            if (
                move.move_type in ['in_invoice', 'in_refund']
                and move.state == 'posted'
                and move.journal_id.is_self_billing
                and move.company_id.account_fiscal_country_id.code == 'ES'
                and move.company_id.l10n_es_edi_verifactu_required
            ):
                move.display_send_button = True

    def _l10n_es_edi_verifactu_get_obligado_partner(self):
        """Return the partner acting as ObligadoEmision for this document.
        For regular invoices this is always the company's own partner.
        Overridden for self-billing vendor bills.
        """
        self.ensure_one()
        if self.journal_id.is_self_billing:
            return self.commercial_partner_id
        return self.company_id.partner_id

    def _reverse_moves(self, default_values_list=None, cancel=False):
        default_values_list = default_values_list or [{}] * len(self)
        for move, default_values in zip(self, default_values_list):
            if move.l10n_es_edi_verifactu_substitution_move_ids:
                default_values['l10n_es_invoice_type'] = 'F2' if move.l10n_es_is_simplified else 'F1'
        return super()._reverse_moves(
            default_values_list=default_values_list,
            cancel=cancel,
        )
