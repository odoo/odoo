from odoo import _, api, fields, models


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
    l10n_es_edi_verifactu_show_cancel_button = fields.Boolean(
        string="Show Veri*Factu Cancel Button",
        compute='_compute_l10n_es_edi_verifactu_show_cancel_button',
    )
    l10n_es_edi_verifactu_available_clave_regimens = fields.Char(
        string="Available Veri*Factu Regime Key",
        compute='_compute_l10n_es_edi_verifactu_available_clave_regimens',
        help="Technical field to enable a dynamic selection of the field \"Veri*Factu Regime Key\"",
    )
    l10n_es_edi_verifactu_clave_regimen = fields.Selection(
        string="Veri*Factu Regime Key",
        selection='_l10n_es_edi_verifactu_clave_regimen_selection',
        compute='_compute_l10n_es_edi_verifactu_clave_regimen', store=True, readonly=False,
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
    l10n_es_edi_verifactu_refund_reason = fields.Selection(
        selection=[
            ('R1', "R1: Art 80.1 and 80.2 and error of law"),
            ('R2', "R2: Art. 80.3"),
            ('R3', "R3: Art. 80.4"),
            ('R4', "R4: Rest"),
            ('R5', "R5: Corrective invoices concerning simplified invoices"),
        ],
        string="Veri*Factu Refund Reason",
        copy=False,
    )

    @api.model
    def _l10n_es_edi_verifactu_clave_regimen_selection(self):
        return [
            # There are different possibilities for the ClaveRegimen field
            # depending on the Impuesto field (IVA / IGIC)
            # Format: '{clave_regimen}' or '{clave_regimen}_{l10n_es_applicability}'
            #         - The first format is in case the code and label are the same in both lists
            #         - The second format is in case the code, label pair is only in one of the lists
            # VAT & IGIC
            ('01', _("General regime operation")),
            ('02', _("Export")),
            ('11', _("Leasing of business premises")),
            # VAT only
            ('17_iva', _("Operation under one of the regimes provided for in Chapter XI of Title IX (OSS and IOSS).")),
            ('18_iva', _("Recargo de equivalencia")),
            ('19_iva', _("Operations of activities included in the Special Regime for Agriculture, Livestock and Fishing (REAGYP)")),
            ('20_iva', _("Simplified Regime")),
            # IGIC only
            ('17_igic', _("Special retailer regime")),
        ]

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

    @api.model
    def _l10n_es_edi_verifactu_get_available_clave_regimens_map(self):
        """
        Return dictionary (Veri*Factu Tax Applicability -> set(operation types))
        """
        clave_regimen_selection = self._l10n_es_edi_verifactu_clave_regimen_selection()
        return {
            '01': {ot for ot, _desc in clave_regimen_selection if len(ot.removesuffix('_iva')) == 2},
            '03': {ot for ot, _desc in clave_regimen_selection if len(ot.removesuffix('_igic')) == 2},
        }

    def _l10n_es_edi_verifactu_get_suggested_clave_regimen(self):
        """
        Currently we only support a single Clave Regimen per Veri*Factu document.
        """
        self.ensure_one()

        tax_applicability = self._l10n_es_edi_verifactu_get_tax_applicability()
        if not tax_applicability:
            return False

        taxes = self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy()
        special_regime = self.company_id.l10n_es_edi_verifactu_special_vat_regime
        return taxes._l10n_es_edi_verifactu_get_suggested_clave_regimen(
            special_regime, forced_tax_applicability=tax_applicability
        )

    @api.depends('invoice_line_ids.tax_ids')
    def _compute_l10n_es_edi_verifactu_available_clave_regimens(self):
        available_clave_regimens = {
            tax_applicability: ','.join(clave_regimens)
            for tax_applicability, clave_regimens in self._l10n_es_edi_verifactu_get_available_clave_regimens_map().items()
        }
        for move in self:
            tax_applicability = move._l10n_es_edi_verifactu_get_tax_applicability()
            move.l10n_es_edi_verifactu_available_clave_regimens = available_clave_regimens.get(tax_applicability, False)

    @api.depends('invoice_line_ids.tax_ids')
    def _compute_l10n_es_edi_verifactu_clave_regimen(self):
        # Currently we only support one operation type for the whole invoice.
        available_clave_regimens = self._l10n_es_edi_verifactu_get_available_clave_regimens_map()
        for move in self:
            clave_regimen = move.l10n_es_edi_verifactu_clave_regimen
            tax_applicability = move._l10n_es_edi_verifactu_get_tax_applicability()
            if clave_regimen not in available_clave_regimens.get(tax_applicability, set()):
                clave_regimen = move._l10n_es_edi_verifactu_get_suggested_clave_regimen()
            move.l10n_es_edi_verifactu_clave_regimen = clave_regimen

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

    @api.depends('l10n_es_edi_verifactu_state')
    def _compute_l10n_es_edi_verifactu_show_cancel_button(self):
        for move in self:
            move.l10n_es_edi_verifactu_show_cancel_button = move.l10n_es_edi_verifactu_state in ('registered_with_errors', 'accepted')

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
        self._l10n_es_edi_verifactu_mark_for_next_batch(cancellation=True)

    def _l10n_es_edi_verifactu_check(self, cancellation=False):
        self.ensure_one()
        errors = []

        if self.state != 'posted':
            errors.append(_("The journal entry has to be posted."))

        tax_applicability = self._l10n_es_edi_verifactu_get_tax_applicability()
        selected_clave_regimen = self.l10n_es_edi_verifactu_clave_regimen
        available_clave_regimens_map = self._l10n_es_edi_verifactu_get_available_clave_regimens_map()
        if selected_clave_regimen and selected_clave_regimen not in available_clave_regimens_map.get(tax_applicability, set()):
            errors.append(_("The Veri*Factu Regime Key is not compatible with the Veri*Factu Tax Applicability."))

        return errors

    def _l10n_es_edi_verifactu_get_record_values(self, cancellation=False):
        self.ensure_one()

        company = self.company_id
        document_type = 'cancellation' if cancellation else 'submission'
        vals = {
            'company': company,
            'record': self,
            'cancellation': cancellation,
            'errors': self._l10n_es_edi_verifactu_check(cancellation=cancellation),
            'document_vals': {
                'move_id': self.id,
                'company_id': company.id,
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
        selected_clave_regimen = self.l10n_es_edi_verifactu_clave_regimen
        clave_regimen = selected_clave_regimen and selected_clave_regimen.split('_', 1)[0]
        substituted_move = self.l10n_es_edi_verifactu_substituted_entry_id
        reversed_move = self.reversed_entry_id

        move_type = self.move_type
        if move_type == 'out_invoice' and substituted_move:
            verifactu_move_type = 'correction_substitution'
        elif move_type == 'out_invoice':
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
            'refund_reason': self.l10n_es_edi_verifactu_refund_reason,
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
