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
        compute="_compute_l10n_es_edi_verifactu_warning"
    )
    l10n_es_edi_verifactu_warning = fields.Html(
        string="Veri*Factu Warning",
        compute="_compute_l10n_es_edi_verifactu_warning"
    )
    l10n_es_edi_verifactu_error_level = fields.Selection(
        string="Veri*Factu Error Level",
        selection=[
            ('rejected', "Rejected"),
            ('registered_with_errors', "Registered with Errors"),
        ],
        compute="_compute_l10n_es_edi_verifactu_errors_and_error_level"
    )
    l10n_es_edi_verifactu_errors = fields.Html(
        string="Veri*Factu Errors",
        compute="_compute_l10n_es_edi_verifactu_errors_and_error_level"
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

    @api.model
    def _l10n_es_edi_verifactu_operation_type_selection(self):
        return [
            # TODO: translate
            # Format: '{impuesto}_{clave_regimen}' (the clave regimen only appplies for VAT and IGIC)
            # VAT
            ('01_01', 'Operación de régimen general'),
            ('01_02', 'Exportación'),
            ('01_11', 'Operaciones de arrendamiento de local de negocio'),
            ('01_17', 'Operación acogida a alguno de los regímenes previstos en el Capítulo XI del Título IX (OSS e IOSS)'),
            ('01_18', 'Recargo de equivalencia'),
            ('01_19', 'Operaciones de actividades incluidas en el Régimen Especial de Agricultura, Ganadería y Pesca (REAGYP)'),
            ('01_20', 'Régimen simplificado'),
            # IPSI
            ('02_', 'IPSI'),
            # IGIC
            ('03_01', 'Operación de régimen general'),
            ('03_02', 'Exportación'),
            ('03_11', 'Operaciones de arrendamiento de local de negocio'),
            ('03_17', 'Régimen especial de comerciante minorista'),
            # other
            ('05_', 'Otros'),
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
        main_taxes = taxes.filtered(
            lambda tax: tax.l10n_es_type not in ('retencion', 'recargo', 'dua', 'ignore')
        )

        # We pick the "first" main tax type.
        # In `_check_record_values` of model 'l10n_es_edi_verifactu.document' we check:
        # There is only a single Veri*Factu Tax Type on the whole move.
        l10n_es_tax_types = main_taxes.mapped('l10n_es_type')
        if not l10n_es_tax_types:
            return False
        return verifactu_tax_type_map.get(l10n_es_tax_types[0], False)

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

        # TODO: do all moves have to be simplified if the company is in the simplified regime?
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
        # TODO: (VAT subject to IPSI/IGIC) or (IGIC subject to VAT/IPSI)
        #   regimen_key = '08'

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
                registered = move.l10n_es_edi_verifactu_state in ('registered_with_errors', 'accepted')
                if registered:
                    warning = _("You are modifying a journal entry for which a Veri*Factu document has been registered by the AEAT.")
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

    @api.depends('l10n_es_edi_verifactu_state', 'l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.state')
    def _compute_show_reset_to_draft_button(self):
        """
        Disallow resetting to draft in the following cases:
        * The move is cancelled
        * We are waiting to sent a cancellation document to the AEAT
        """
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_es_edi_verifactu_state == 'cancelled':
                move.show_reset_to_draft_button = False
                continue
            waiting_documents = move.l10n_es_edi_verifactu_document_ids._filter_waiting()
            if any(doc.document_type == 'cancellation' for doc in waiting_documents):
                move.show_reset_to_draft_button = False

    def l10n_es_edi_verifactu_button_cancel(self):
        created_documents = self._l10n_es_edi_verifactu_mark_for_next_batch(cancellation=True)
        skipped_moves = self.filtered(lambda move: not created_documents.get(move))
        if skipped_moves and len(self) == 1:
            # TODO: not correct in case we skip for concurrency case
            raise UserError(_("We are waiting to send a Veri*Factu record to the AEAT already."))
        # In other cases we just silently skip them

    def _l10n_es_edi_verifactu_check(self, cancellation=False):
        self.ensure_one()
        errors = []

        if self.state != 'posted':
            errors.append(_("The journal entry has to be posted."))

        refunded_move = self.reversed_entry_id
        refunded_document = refunded_move.l10n_es_edi_verifactu_document_ids._get_last('submission')
        if refunded_move and not refunded_document:
            # TODO: could also be cancellation without prior registration
            errors.append(_("The refunded journal entry has no Veri*Factu document yet."))

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

        vals.update({
            'rejected_before': rejected_before,
            'verifactu_state': self.l10n_es_edi_verifactu_state,
            'delivery_date': self.delivery_date,
            'description': self.invoice_origin[:500] if self.invoice_origin else None,
            'invoice_date': self.invoice_date,
            'is_simplified': is_simplified,
            'move_type': self.move_type,
            'name': self.name,
            'partner': self.commercial_partner_id,
            'refunded_document': self.reversed_entry_id.l10n_es_edi_verifactu_document_ids._get_last('submission'),
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

    def _l10n_es_edi_verifactu_create_document(self, cancellation=False, previous_record_identifier=None):
        self.ensure_one()

        record_values = self._l10n_es_edi_verifactu_get_record_values(cancellation=cancellation)

        return self.env['l10n_es_edi_verifactu.document']._create_for_record(
            record_values, previous_record_identifier=previous_record_identifier,
        )

    def _l10n_es_edi_verifactu_mark_for_next_batch(self, cancellation=False):
        record_values_list = [
            move._l10n_es_edi_verifactu_get_record_values(cancellation=cancellation)
            for move in self
        ]
        return self.env['l10n_es_edi_verifactu.document']._mark_records_for_next_batch(record_values_list)
