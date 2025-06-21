from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_edi_verifactu_required = fields.Boolean(
        string="Veri*Factu Required",
        compute='_compute_l10n_es_edi_verifactu_required',
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
        tracking=True,
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
    l10n_es_edi_verifactu_error_level = fields.Selection(
        string="Veri*Factu Error Level",
        selection=[
            ('rejected', "Rejected"),
            ('registered_with_errors', "Registered with Errors"),
        ],
        compute="_compute_l10n_es_edi_verifactu_errors_and_error_level",
    )
    l10n_es_edi_verifactu_errors = fields.Html(
        string="Veri*Factu Errors",
        compute="_compute_l10n_es_edi_verifactu_errors_and_error_level",
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
    l10n_es_edi_verifactu_available_operation_types = fields.Char(
        string="Available Veri*Factu Operation Type",
        compute='_compute_l10n_es_edi_verifactu_available_operation_types',
        help="Technical field to enable a dynamic selection of the field \"Veri*Factu Operation Type\"",
    )
    l10n_es_edi_verifactu_operation_type = fields.Selection(
        string="Veri*Factu Operation Type",
        selection='_l10n_es_edi_verifactu_operation_type_selection',
        compute='_compute_l10n_es_edi_verifactu_operation_type', store=True, readonly=False,
    )
    l10n_es_edi_verifactu_substituted_entry_id = fields.Many2one(
        comodel_name='account.move',
        string="Substitution of",
        index='btree_not_null',
        readonly=True,
        copy=False,
        check_company=True,
    )
    l10n_es_edi_verifactu_substitution_move_id = fields.One2many(
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
    def _l10n_es_edi_verifactu_operation_type_selection(self):
        return [
            # Format: '{impuesto}_{clave_regimen}' (the clave regimen only appplies for VAT and IGIC)
            # VAT
            ('01_01', 'General regime operation'), # Operación de régimen general
            ('01_02', 'Export'), # Exportación
            ('01_11', 'Leasing of business premises'), # Operaciones de arrendamiento de local de negocio
            ('01_17', 'Operation under one of the regimes provided for in Chapter XI of Title IX (OSS and IOSS).'), # Operación acogida a alguno de los regímenes previstos en el Capítulo XI del Título IX (OSS e IOSS)
            ('01_18', 'Recargo de equivalencia'), # Recargo de equivalencia
            ('01_19', 'Operations of activities included in the Special Regime for Agriculture, Livestock and Fishing (REAGYP)'), # Operaciones de actividades incluidas en el Régimen Especial de Agricultura, Ganadería y Pesca (REAGYP)
            ('01_20', 'Simplified Regime'), # Régimen simplificado
            # IPSI
            ('02_', 'IPSI'), # IPSI
            # IGIC
            ('03_01', 'General regime operation'), # Operación de régimen general
            ('03_02', 'Export'), # Exportación
            ('03_11', 'Leasing of business premises'), # Operaciones de arrendamiento de local de negocio
            ('03_17', 'Special retailer regime'), # Régimen especial de comerciante minorista
            # other
            ('05_', 'Other'), # Otros
        ]

    def _l10n_es_edi_verifactu_get_verifactu_tax_type(self):
        """
        Currently we only support one operation type (Veri*Factu Tax Type / Clave Regimen) for the whole invoice.
        In `_check_record_values` of model 'l10n_es_edi_verifactu.document' we check:
        There is only a single Veri*Factu Tax Type on the whole move.
        """
        self.ensure_one()
        if not self.l10n_es_edi_verifactu_required:
            return False

        verifactu_tax_type_map = self.env['account.tax']._l10n_es_edi_verifactu_get_tax_types_map()

        taxes = self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy()
        main_taxes = taxes._l10n_es_edi_verifactu_filter_main_taxes()

        # We pick the "first" main tax type (they always have a `l10n_es_applicability`).
        # In `_check_record_values` of model 'l10n_es_edi_verifactu.document' we check:
        # There is only a single Veri*Factu Tax Type on the whole move.
        if not main_taxes:
            return False
        return verifactu_tax_type_map.get(main_taxes[0].l10n_es_applicability, False)

    @api.model
    def _l10n_es_edi_verifactu_get_available_operation_types_map(self):
        """
        Return dictionary (Veri*Factu Tax Type -> set(operation types))
        """
        verifactu_tax_types = self.env['account.tax']._l10n_es_edi_verifactu_get_tax_types_map().values()
        operation_type_selection = self._l10n_es_edi_verifactu_operation_type_selection()
        return {
            verifactu_tax_type: {ot for ot, _desc in operation_type_selection if ot.startswith(f'{verifactu_tax_type}_')}
            for verifactu_tax_type in verifactu_tax_types
        }

    def _l10n_es_edi_verifactu_suggested_operation_type(self):
        """
        Currently we only support one operation type (Veri*Factu Tax Type / Clave Regimen) for the whole invoice.
        """
        self.ensure_one()

        verifactu_tax_type = self._l10n_es_edi_verifactu_get_verifactu_tax_type()
        if not verifactu_tax_type:
            return False

        taxes = self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy()
        recargo_taxes = taxes.filtered(lambda tax: tax.l10n_es_type == 'recargo')

        regimen_key = None
        VAT = verifactu_tax_type == '01'
        IGIC = verifactu_tax_type == '03'
        if not (VAT or IGIC):
            return f'{verifactu_tax_type}_'

        oss_tag = self.env.ref('l10n_eu_oss.tag_oss', raise_if_not_found=False)
        if self.move_type == 'out_invoice':
            repartition_lines = taxes.invoice_repartition_line_ids
        else:
            # move.move_type == 'out_refund'
            repartition_lines = taxes.refund_repartition_line_ids

        company_regime = self.company_id.l10n_es_edi_verifactu_special_vat_regime

        if VAT and company_regime == 'simplified' and self.l10n_es_is_simplified:
            # simplified
            regimen_key = '20'
        elif VAT and company_regime == 'reagyp':
            # REAGYP
            regimen_key = '19'
        elif VAT and recargo_taxes:
            # recargo
            regimen_key = '18'
        elif VAT and oss_tag and oss_tag in repartition_lines.tag_ids:
            # oss
            regimen_key = '17'
        elif taxes.filtered(lambda tax: tax.l10n_es_type == 'exento' and tax.l10n_es_exempt_reason == 'E2'):
            # export
            regimen_key = '02'
        else:
            regimen_key = '01'

        return f'{verifactu_tax_type}_{regimen_key}'

    @api.depends('invoice_line_ids.tax_ids')
    def _compute_l10n_es_edi_verifactu_available_operation_types(self):
        """
        Currently we only support one operation type (Veri*Factu Tax Type / Clave Regimen) for the whole invoice.
        """
        available_operation_types = {
            verifactu_tax_type: ','.join(operation_types)
            for verifactu_tax_type, operation_types in self._l10n_es_edi_verifactu_get_available_operation_types_map().items()
        }
        for move in self:
            verifactu_tax_type = move._l10n_es_edi_verifactu_get_verifactu_tax_type()
            move.l10n_es_edi_verifactu_available_operation_types = available_operation_types.get(verifactu_tax_type, False)

    @api.depends('invoice_line_ids.tax_ids')
    def _compute_l10n_es_edi_verifactu_operation_type(self):
        # Currently we only support one operation type for the whole invoice.
        available_operation_types = self._l10n_es_edi_verifactu_get_available_operation_types_map()
        for move in self:
            operation_type = move.l10n_es_edi_verifactu_operation_type
            if operation_type not in available_operation_types.get(operation_type, set()):
                operation_type = move._l10n_es_edi_verifactu_suggested_operation_type()
            move.l10n_es_edi_verifactu_operation_type = operation_type

    @api.depends('country_code')
    def _compute_l10n_es_edi_verifactu_required(self):
        for move in self:
            move.l10n_es_edi_verifactu_required = move.country_code == 'ES' and move.company_id.l10n_es_edi_verifactu_required

    @api.depends('l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.state', 'l10n_es_edi_verifactu_document_ids.errors')
    def _compute_l10n_es_edi_verifactu_errors_and_error_level(self):
        for move in self:
            last_document = move.l10n_es_edi_verifactu_document_ids.sorted()[:1]
            error_level = False if last_document.state == 'accepted' else last_document.state
            move.l10n_es_edi_verifactu_error_level = error_level
            move.l10n_es_edi_verifactu_errors = last_document.errors

    @api.depends('l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.state')
    def _compute_l10n_es_edi_verifactu_state(self):
        for move in self:
            state = move.l10n_es_edi_verifactu_document_ids._get_state()
            move.l10n_es_edi_verifactu_state = state

    @api.depends('l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.record_identifier')
    def _compute_l10n_es_edi_verifactu_qr_code(self):
        for move in self:
            last_submission = move.l10n_es_edi_verifactu_document_ids._get_last('submission')
            url = last_submission._get_qr_code_img_url() if last_submission else False
            move.l10n_es_edi_verifactu_qr_code = url

    @api.depends('l10n_es_edi_verifactu_state', 'l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.state')
    def _compute_l10n_es_edi_verifactu_warning(self):
        for move in self:
            warning = False
            warning_level = False
            waiting_documents = move.l10n_es_edi_verifactu_document_ids._filter_waiting()
            if move.state == 'draft':
                if move.l10n_es_edi_verifactu_state:
                    warning = _("You are modifying a journal entry for which a Veri*Factu document has been sent to the AEAT already.")
                    warning_level = 'warning'
                elif waiting_documents:
                    warning = _("You are modifying a journal entry for which a Veri*Factu document is waiting to be sent.")
                    warning_level = 'warning'
            elif move.state == 'posted' and waiting_documents:
                warning = _("A Veri*Factu document is waiting to be sent as soon as possible.")
                warning_level = 'info'
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

    def l10n_es_edi_verifactu_button_cancel(self):
        self._l10n_es_edi_verifactu_mark_for_next_batch(cancellation=True)

    def _l10n_es_edi_verifactu_check(self, cancellation=False):
        self.ensure_one()
        errors = []

        if self.state != 'posted':
            errors.append(_("The journal entry has to be posted."))

        if not self.l10n_es_edi_verifactu_operation_type:
            errors.append(_("The journal entry has no Veri*Factu Operation Type."))

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
        is_simplified = self.l10n_es_is_simplified

        verifactu_tax_type, clave_regimen = self.l10n_es_edi_verifactu_operation_type.split('_', 1)
        substituted_move = self.l10n_es_edi_verifactu_substituted_entry_id
        reversed_move = self.reversed_entry_id

        move_type = self.move_type
        if move_type == 'out_invoice' and substituted_move:
            verifactu_move_type = 'correction_substitution'
        elif move_type == 'out_invoice':
            verifactu_move_type = 'invoice'
        elif move_type == 'out_refund' and reversed_move.l10n_es_edi_verifactu_substitution_move_id:
            verifactu_move_type = 'reversal_for_substitution'
        else:
            # move_type == 'out_refund' and not reversed_move.l10n_es_edi_verifactu_substitution_move_id
            verifactu_move_type = 'correction_incremental'

        vals.update({
            'rejected_before': rejected_before,
            'verifactu_state': self.l10n_es_edi_verifactu_state,
            'delivery_date': self.delivery_date,
            'description': self.invoice_origin[:500] if self.invoice_origin else None,
            'invoice_date': self.invoice_date,
            'is_simplified': is_simplified,
            'move_type': move_type,
            'verifactu_move_type': verifactu_move_type,
            'name': self.name,
            'partner': self.commercial_partner_id,
            'refund_reason': self.l10n_es_edi_verifactu_refund_reason,
            'refunded_document': reversed_move.l10n_es_edi_verifactu_document_ids._get_last('submission'),
            'substituted_document': substituted_move.l10n_es_edi_verifactu_document_ids._get_last('submission'),
            'substituted_document_reversal_document': substituted_move.reversal_move_id.l10n_es_edi_verifactu_document_ids._get_last('submission'),
            'documents': documents,
            'record_identifier': documents._get_last('submission').record_identifier,
            'verifactu_tax_type': verifactu_tax_type,
            'clave_regimen': clave_regimen or None,
        })

        tax_details_functions = self.env['account.tax']._l10n_es_edi_verifactu_get_tax_details_functions(company)

        vals['tax_details'] = self._prepare_invoice_aggregated_taxes(
            filter_invl_to_apply=tax_details_functions['full_filter_invl_to_apply'],
            filter_tax_values_to_apply=tax_details_functions['filter_to_apply'],
            grouping_key_generator=tax_details_functions['grouping_key_generator'],
        )

        vals['errors'] = self.env['l10n_es_edi_verifactu.document']._check_record_values(vals)

        return vals

    def _l10n_es_edi_verifactu_create_documents(self, cancellation=False):
        record_values_list = [
            move._l10n_es_edi_verifactu_get_record_values(cancellation=cancellation)
            for move in self
        ]
        return self.env['l10n_es_edi_verifactu.document']._create_from_record_values_list(record_values_list)

    def _l10n_es_edi_verifactu_mark_for_next_batch(self, cancellation=False):
        documents = self._l10n_es_edi_verifactu_create_documents(cancellation=cancellation)
        self.env['l10n_es_edi_verifactu.document'].trigger_next_batch()
        return documents
