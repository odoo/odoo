from odoo import _, api, models, fields
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import float_compare, format_datetime
from odoo.fields import Domain

from odoo.addons.l10n_pt_stock.models.l10n_pt_at_series import AT_SERIES_MOVEMENT_DOCUMENT_TYPES


# The RBC elements of a transport document held on the transfer (DL 147/2003 art. 4(2), 4(4)): once
# it is issued they are frozen (Despacho 8632/2014 1.11); goods and quantities are on its moves.
L10N_PT_ISSUED_PICKING_FIELDS = {
    'partner_id', 'location_id', 'location_dest_id', 'picking_type_id', 'l10n_pt_start_transport_date', 'company_id',
    'l10n_pt_no_transport_document',
}

SAFT_PT_MOVEMENT_TYPE_MAP = {
    'outgoing': 'GT',
    'internal': 'GA',
    'incoming': 'GD',
}

# The movement documents (keys of `l10n_pt.at.series.document_type`) the series of an operation type
# may issue, by operation code. Deliveries and moves between the company's own sites are GT; a
# receipt issues nothing, since the sender issues the transport document; GA is for the company's
# own fixed assets, which no operation type models. A supplier return's GD comes from the delivery
# type's returns series instead.
L10N_PT_STOCK_SERIES_TYPES_BY_CODE = {
    'outgoing': ('outgoing',),
    'internal': ('outgoing',),
}


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')
    # The document types `l10n_pt_stock_at_series_id` may take, for its "Create and edit".
    l10n_pt_stock_series_document_types = fields.Json(compute='_compute_l10n_pt_stock_series_document_types')
    # The series each field may take, for their domains.
    l10n_pt_stock_available_at_series_ids = fields.Many2many(
        comodel_name='l10n_pt.at.series',
        compute='_compute_l10n_pt_stock_available_at_series_ids',
    )
    l10n_pt_stock_available_return_at_series_ids = fields.Many2many(
        comodel_name='l10n_pt.at.series',
        compute='_compute_l10n_pt_stock_available_at_series_ids',
    )
    l10n_pt_stock_at_series_id = fields.Many2one(
        comodel_name='l10n_pt.at.series',
        string="Official Series of the Tax Authority",
        domain="[('id', 'in', l10n_pt_stock_available_at_series_ids)]",
    )
    l10n_pt_stock_return_at_series_id = fields.Many2one(
        comodel_name='l10n_pt.at.series',
        string="AT Series for Returns",
        domain="[('id', 'in', l10n_pt_stock_available_return_at_series_ids)]",
        help="Return Note (GD) series issued by returns of received goods made with this operation type, "
             "i.e. returns to suppliers.",
    )

    _at_series_code_unique = models.Constraint(
        'unique(l10n_pt_stock_at_series_id, code)',
        'An AT series cannot be assigned to multiple Operation Types.',
    )
    _return_at_series_unique = models.Constraint(
        'unique(l10n_pt_stock_return_at_series_id)',
        'An AT series for returns cannot be assigned to multiple Operation Types.',
    )

    @api.depends('code')
    def _compute_l10n_pt_stock_series_document_types(self):
        for picking_type in self:
            picking_type.l10n_pt_stock_series_document_types = list(
                L10N_PT_STOCK_SERIES_TYPES_BY_CODE.get(picking_type.code, ())
            )

    @api.depends('code', 'company_id')
    def _compute_l10n_pt_stock_available_at_series_ids(self):
        """
        The series the company may use (``_l10n_pt_company_domain``) of the document types the operation
        code issues: its movement series, and, for a delivery type, its returns (GD) series. Ended series
        are kept, as the save-time check accepts them; the dropdown hides them as it hides any inactive record.
        """
        self.l10n_pt_stock_available_at_series_ids = False
        self.l10n_pt_stock_available_return_at_series_ids = False
        at_series_model = self.env['l10n_pt.at.series'].with_context(active_test=False)
        movement_types = [document_type for document_type, _label in AT_SERIES_MOVEMENT_DOCUMENT_TYPES]
        for company, picking_types in self.filtered(lambda t: t.country_code == 'PT').grouped('company_id').items():
            company_series = at_series_model.search(
                at_series_model._l10n_pt_company_domain(company) & Domain('document_type', 'in', movement_types)
            )
            for picking_type in picking_types:
                document_types = L10N_PT_STOCK_SERIES_TYPES_BY_CODE.get(picking_type.code, ())
                picking_type.l10n_pt_stock_available_at_series_ids = company_series.filtered(
                    lambda s: s.document_type in document_types
                )
                if picking_type.code == 'outgoing':
                    picking_type.l10n_pt_stock_available_return_at_series_ids = company_series.filtered(
                        lambda s: s.document_type == 'incoming'
                    )

    @api.constrains('l10n_pt_stock_at_series_id', 'l10n_pt_stock_return_at_series_id', 'code', 'company_id')
    def _check_l10n_pt_stock_at_series_id(self):
        at_series_model = self.env['l10n_pt.at.series']
        for picking_type in self.filtered(lambda t: t.country_code == 'PT'):
            all_series = picking_type.l10n_pt_stock_at_series_id | picking_type.l10n_pt_stock_return_at_series_id
            if foreign := all_series - all_series.filtered_domain(at_series_model._l10n_pt_company_domain(picking_type.company_id)):
                raise UserError(_(
                    "The AT series %(series)s cannot be used by the operation type %(operation_type)s of "
                    "%(company)s. An operation type uses the series of its own company, or a series of a parent "
                    "company that is not exclusive.",
                    series=", ".join(foreign.mapped('display_name')),
                    operation_type=picking_type.display_name,
                    company=picking_type.company_id.display_name,
                ))
            return_series = picking_type.l10n_pt_stock_return_at_series_id
            if return_series and (picking_type.code != 'outgoing' or return_series.document_type != 'incoming'):
                raise UserError(_(
                    "Only a delivery operation type takes a series for returns, and it must be a "
                    "Return Note (GD) series."
                ))
            if (
                picking_type.l10n_pt_stock_at_series_id
                and picking_type.l10n_pt_stock_at_series_id.document_type
                not in L10N_PT_STOCK_SERIES_TYPES_BY_CODE.get(picking_type.code, ())
            ):
                action_error = {
                    'view_mode': 'form',
                    'name': _('Draft Entries'),
                    'res_model': 'l10n_pt.at.series',
                    'res_id': picking_type.l10n_pt_stock_at_series_id.id,
                    'type': 'ir.actions.act_window',
                    'views': [[self.env.ref('l10n_pt_certification.view_l10n_pt_at_series_form').id, 'form']],
                    'target': 'new',
                }
                raise RedirectWarning(
                    _("The AT series %(series_name)s cannot be used by this Operation Type: deliveries and "
                      "transfers between warehouses issue Transport Guides (GT), and receipts issue no "
                      "document. Create a new series or view existing series via the Accounting Settings.",
                      series_name=picking_type.l10n_pt_stock_at_series_id.name),
                    action_error,
                    _('Add an AT Series'),
                )


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "l10n.pt.hashed.document.mixin"]

    _l10n_pt_date_field = "l10n_pt_issue_date"
    _l10n_pt_document_type_depends = (
        'picking_type_id', 'company_id', 'location_id', 'location_dest_id', 'return_id', 'partner_id.country_id',
        'l10n_pt_no_transport_document',
    )

    l10n_pt_document_type = fields.Selection(selection_add=AT_SERIES_MOVEMENT_DOCUMENT_TYPES)
    l10n_pt_start_transport_date = fields.Datetime(
        'Start of Transport',
        tracking=True,
        help="Date and time the goods leave. A transport document communicated to the AT before its "
             "transfer is validated needs it, still to come. Otherwise validation sets it to the "
             "validation time, unless a later start was entered.",
    )
    # The user may let the goods travel with another transport document, such as their invoice (RBC art.
    # 2(1)(b)): the transfer then issues none.
    l10n_pt_no_transport_document = fields.Boolean(
        string="Without Transport Document",
        tracking=True,
        copy=False,
        help="Validate this transfer without issuing its transport document, because another document, such as "
             "its invoice, accompanies the goods. An invoice that is the transport document is exempt from "
             "communication to the AT only if it accompanies the goods.",
    )
    l10n_pt_transport_document_reference = fields.Char(
        string="Travels With",
        tracking=True,
        copy=False,
        help="The document that accompanies the goods instead, e.g. FT 2026/00012.",
    )
    l10n_pt_show_no_at_series_warning = fields.Boolean(compute='_compute_l10n_pt_show_no_at_series_warning')
    l10n_pt_documented_elsewhere = fields.Boolean(compute='_compute_l10n_pt_documented_elsewhere')
    # The transport document's date: when it was issued, at validation or, communicated beforehand,
    # while the transfer was ready. Transfers issued before this field existed take their
    # validation date, which they were signed with.
    l10n_pt_issue_date = fields.Datetime(
        string="Issue Date",
        compute='_compute_l10n_pt_issue_date',
        store=True,
        readonly=True,
        copy=False,
    )

    ####################################
    # OVERRIDES
    ####################################

    @api.depends()
    def _compute_l10n_pt_issue_date(self):
        # Computed once, when the column is created; set by `_l10n_pt_issue` from then on.
        for picking in self:
            picking.l10n_pt_issue_date = picking.l10n_pt_issue_date or (picking.l10n_pt_document_number and picking.date_done)

    def _pre_action_done_hook(self):
        # An operation type without AT series issues no transport document: ask before the goods leave
        # without one. Only the Validate button asks; `_action_done` called directly has nobody to ask.
        res = super()._pre_action_done_hook()
        if res is True and not self.env.context.get('l10n_pt_skip_no_document_warning'):
            if without_series := self._l10n_pt_without_at_series():
                return without_series._l10n_pt_action_no_document_warning()
        return res

    def _l10n_pt_action_no_document_warning(self):
        wizard = self.env['l10n.pt.stock.no.document.warning'].create({'picking_ids': self.ids})
        return {
            'name': _("No Transport Document"),
            'type': 'ir.actions.act_window',
            'res_model': 'l10n.pt.stock.no.document.warning',
            'res_id': wizard.id,
            'views': [(False, 'form')],
            'target': 'new',
            # Keeps `button_validate_picking_ids` and the validation's options for the wizard's Validate
            'context': self.env.context,
        }

    def _action_done(self):
        without_series = self._l10n_pt_without_at_series()
        # A transport document is issued before the goods circulate (RBC art. 6(1)): communicated
        # beforehand, it was issued while ready, and is validated in full, as issued.
        self._l10n_pt_check_validated_as_issued()
        res = super()._action_done()
        # Otherwise it is issued here: every path to `done` (validate, backorders, barcode, RPC) goes
        # through here.
        if pt_pickings := self.filtered(lambda p: p.country_code == 'PT' and p.state == 'done'):
            pt_pickings._l10n_pt_issue()
            pt_pickings._l10n_pt_compute_missing_hashes()
        without_series.filtered(lambda p: p.state == 'done')._l10n_pt_log_without_transport_document()
        return res

    def _l10n_pt_issue(self, before_transport=False):
        """
        Issue the transfers of ``self`` that are to travel with a transport document: number, date and
        sign them in one step, so that number order, date order and chain order are the same
        (Despacho 8632/2014 1.6, 2.1.5).

        :param before_transport: issue ready transfers before their goods leave, to communicate them
            first: the transport starts at the entered Start of Transport, which must be still to
            come, and every move is reserved in full, since the document states the goods. The
            scheduled date, a planning date, plays no part. Otherwise, at validation, the
            transport starts now, unless a later start was entered.
        """
        to_issue = self.filtered(lambda p: (
            p.country_code == 'PT' and not p.l10n_pt_document_number and p._l10n_pt_stock_at_series()
        ))
        now = fields.Datetime.now()
        if before_transport:
            to_issue._l10n_pt_check_issuable_before_transport(now)
        else:
            to_issue.filtered(
                lambda p: not p.l10n_pt_start_transport_date or p.l10n_pt_start_transport_date < now
            ).l10n_pt_start_transport_date = now
        to_issue.l10n_pt_issue_date = now
        to_issue._set_l10n_pt_document_number()
        if before_transport:
            # A transport document is communicated with its signature: when signing fails, nothing is
            # issued, rather than communicating unsigned documents.
            try:
                to_issue.with_context(l10n_pt_stock_raise_signing_errors=True)._l10n_pt_compute_missing_hashes()
            except UserError as e:
                raise UserError(_(
                    "The transport documents could not be signed, so they cannot be issued and communicated:\n%(error)s",
                    error=e.args[0],
                )) from e
        return to_issue

    def _l10n_pt_check_issuable_before_transport(self, now):
        """
        Refuse to issue the transfers of ``self`` before their goods leave unless each is ready in full
        and has a Start of Transport still to come; one error names every transfer and its reason.
        """
        reasons = []
        for picking in self:
            start = picking.l10n_pt_start_transport_date
            if not start:
                reasons.append(_("%(transfer)s: no Start of Transport was entered", transfer=picking.name))
            elif start <= now:
                reasons.append(_(
                    "%(transfer)s: its Start of Transport, %(date)s, has passed",
                    transfer=picking.name,
                    date=format_datetime(self.env, start),
                ))
            if picking.state != 'assigned' or any(
                float_compare(move.quantity, move.product_uom_qty, precision_rounding=move.product_uom.rounding)
                for move in picking.move_ids.filtered(lambda m: m.state != 'cancel')
            ):
                reasons.append(_("%(transfer)s: its goods are not all reserved", transfer=picking.name))
        if reasons:
            raise UserError(_(
                "These transfers cannot be issued before their goods leave:\n%(reasons)s\n\nA transport "
                "document states when its goods leave and which goods: enter a Start of Transport still to "
                "come, and issue a transfer once it is ready in full.",
                reasons="\n".join(f"- {reason}" for reason in reasons),
            ))

    def action_cancel(self):
        # An issued transport document not validated yet is annulled with its transfer: only before its
        # transport starts (AT FAQ 5418-5420), and with a reason (Portaria 302/2016 4.2.3.2.3), asked for
        # by the form's Cancel button; any other path is refused without one.
        to_annul = self._l10n_pt_issued().filtered(lambda p: p.state not in ('done', 'cancel'))
        to_annul._l10n_pt_check_annullable()
        if to_annul.filtered(lambda p: not p.l10n_pt_cancel_reason):
            if not self.env.context.get('l10n_pt_cancel_with_reason'):
                raise UserError(_(
                    "%(documents)s was issued as a transport document: cancel its transfer from its form, with "
                    "the reason it is annulled.",
                    documents=", ".join(to_annul.mapped('l10n_pt_document_number')),
                ))
            action = self.env['ir.actions.actions']._for_xml_id('l10n_pt_certification.action_l10n_pt_cancel')
            action['context'] = {
                'model': 'stock.picking',
                'picking_ids': self.ids,
                'default_l10n_pt_notice': "\n".join(to_annul.mapped(lambda p: p._l10n_pt_annulment_notice())),
            }
            return action
        res = super().action_cancel()
        to_annul._l10n_pt_record_cancellation()
        return res

    def _l10n_pt_check_annullable(self):
        """Refuse to annul an issued transport document whose transport has started (AT FAQ 5418, 5419)."""
        now = fields.Datetime.now()
        if started := self.filtered(lambda p: p.l10n_pt_start_transport_date and p.l10n_pt_start_transport_date <= now):
            raise UserError(_(
                "%(documents)s cannot be annulled: its transport has started, after which the AT no longer "
                "allows annulling a transport document. Validate it as issued.",
                documents=", ".join(started.mapped('l10n_pt_document_number')),
            ))

    def _l10n_pt_annulment_notice(self):
        """What annulling this issued transport document means, shown before it is annulled."""
        self.ensure_one()
        return _(
            "%(document)s will be annulled: it stays in its series, as annulled.",
            document=self.l10n_pt_document_number,
        )

    def _l10n_pt_check_validated_as_issued(self):
        """Refuse to validate a transfer issued beforehand otherwise than in full, as its document states."""
        for picking in self._l10n_pt_issued().filtered(lambda p: p.state not in ('done', 'cancel')):
            moves = picking.move_ids.filtered(lambda m: m.state != 'cancel')
            partial = moves.filtered('picked') and moves.filtered(lambda m: not m.picked)
            if partial or any(
                float_compare(move.quantity, move.product_uom_qty, precision_rounding=move.product_uom.rounding)
                for move in moves
            ):
                raise UserError(_(
                    "%(document)s was issued for the goods of %(transfer)s: validate it in full, as issued.",
                    document=picking.l10n_pt_document_number,
                    transfer=picking.name,
                ))

    def _l10n_pt_without_at_series(self):
        """
        The transfers of ``self`` that would travel with a transport document (a GT, or a GD for a
        supplier return, to a destination in Portugal) but whose operation type has no AT series to
        issue it in: the operation type opts them out, and they are validated without one.
        """
        return self.filtered(lambda p: (
            p.country_code == 'PT'
            and p.l10n_pt_document_type
            and not p.l10n_pt_document_number
            and not p._l10n_pt_stock_at_series()
        )) - self._l10n_pt_documented_elsewhere()

    def _l10n_pt_documented_elsewhere(self):
        """
        The transfers of ``self`` whose goods are documented by another document than a transport document
        (none here): they are never reported as leaving without one.
        """
        return self.browse()

    def _compute_l10n_pt_documented_elsewhere(self):
        documented_elsewhere = self._l10n_pt_documented_elsewhere()
        for picking in self:
            picking.l10n_pt_documented_elsewhere = picking in documented_elsewhere

    def _l10n_pt_log_without_transport_document(self):
        """Note on each transfer of ``self`` that it was validated without a transport document, and why."""
        document_types = dict(self._fields['l10n_pt_document_type']._description_selection(self.env))
        self._message_log_batch(bodies={
            picking.id: _(
                "Validated without a transport document: its operation type, %(operation_type)s, has no AT "
                "series for a %(document_type)s.",
                operation_type=picking.picking_type_id.display_name,
                document_type=document_types.get(picking.l10n_pt_document_type, picking.l10n_pt_document_type),
            )
            for picking in self
        })

    def _l10n_pt_issued(self):
        """
        The transfers of ``self`` issued as PT transport documents: numbered, at validation or, to be
        communicated before their goods leave, while ready.
        """
        return self.filtered(lambda p: p.country_code == 'PT' and p.l10n_pt_document_number)

    def _l10n_pt_raise_if_issued(self, what):
        """Refuse a change of ``what`` (goods, quantities, ...) on transfers issued as transport documents."""
        if issued := self._l10n_pt_issued():
            if not_done := issued.filtered(lambda p: p.state != 'done'):
                raise UserError(_(
                    "%(documents)s was issued as a transport document: its %(what)s can no longer be changed. "
                    "Validate it as issued.",
                    documents=", ".join(not_done.mapped('l10n_pt_document_number')),
                    what=what,
                ))
            raise UserError(_(
                "%(documents)s was issued as a transport document: its %(what)s can no longer be changed. "
                "Make a return to correct it.",
                documents=", ".join(issued.mapped('l10n_pt_document_number')),
                what=what,
            ))

    def write(self, vals):
        if 'l10n_pt_no_transport_document' in vals and self.filtered(lambda p: (
            p.state in ('done', 'cancel') and p.l10n_pt_no_transport_document != bool(vals['l10n_pt_no_transport_document'])
        )):
            raise UserError(_("Whether a transfer travels with its own transport document cannot be changed once it is done."))
        if issued := self._l10n_pt_issued():
            if vals.get('is_locked') is False and issued.filtered('is_locked'):
                issued._l10n_pt_raise_if_issued(_("lines"))
            for field_name in L10N_PT_ISSUED_PICKING_FIELDS & vals.keys():
                field = self._fields[field_name]
                value = field.convert_to_record(field.convert_to_cache(vals[field_name], self), self)
                issued.filtered(lambda p: p[field_name] != value)._l10n_pt_raise_if_issued(field.string)
        return super().write(vals)

    def _set_l10n_pt_document_number(self):
        # The series is the operation type's when the transfer is issued, and stays the transfer's:
        # re-pointing the type later must not re-file past transfers (Despacho 8632/2014 1.9, 2.1.5).
        to_number = self.filtered(lambda p: p.country_code == 'PT' and not p.l10n_pt_document_number)
        for pickings in to_number.grouped(lambda p: (p.picking_type_id, p.l10n_pt_document_type)).values():
            pickings.l10n_pt_at_series_id = pickings[0]._l10n_pt_stock_at_series()
        to_number = to_number.filtered('l10n_pt_at_series_id')
        to_number._check_l10n_pt_at_series_id()
        to_number._check_l10n_pt_dates()
        return super()._set_l10n_pt_document_number()

    ####################################
    # MISC REQUIREMENTS
    ####################################

    @api.depends('l10n_pt_document_type', 'picking_type_id.l10n_pt_stock_at_series_id', 'picking_type_id.l10n_pt_stock_return_at_series_id')
    def _compute_l10n_pt_show_no_at_series_warning(self):
        for picking in self:
            picking.l10n_pt_show_no_at_series_warning = bool(
                picking.l10n_pt_document_type and not picking._l10n_pt_stock_at_series()
            )

    def _l10n_pt_stock_at_series(self):
        """The series this transfer is to be issued in, by its document type."""
        self.ensure_one()
        if self.l10n_pt_document_type == 'incoming':
            return self.picking_type_id.l10n_pt_stock_return_at_series_id
        if self.l10n_pt_document_type:
            return self.picking_type_id.l10n_pt_stock_at_series_id
        return self.env['l10n_pt.at.series']

    def _l10n_pt_get_loading_and_unloading_places(self):
        """
        Where the goods are loaded and unloaded (RBC art. 2(1)(h)-(i), 4(4)), as partners: the address
        of one of the company's warehouses, or the partner the goods are sent to.
        """
        self.ensure_one()
        company_partner = self.company_id.partner_id
        loading = self.location_id.warehouse_id.partner_id or company_partner
        if self.location_dest_id.warehouse_id:
            unloading = self.location_dest_id.warehouse_id.partner_id or company_partner
        else:
            unloading = self.partner_id
        return loading, unloading

    def _l10n_pt_get_recipient(self):
        """Who the goods are sent to (RBC art. 4(2)(c)): the company itself between its own sites."""
        self.ensure_one()
        if self.location_dest_id.warehouse_id:
            return self.company_id.partner_id
        return self.partner_id.commercial_partner_id

    def _l10n_pt_get_legal_tz(self):
        """The time zone of the company's region, in which the start of transport is printed."""
        self.ensure_one()
        return {'PT-AC': 'Atlantic/Azores', 'PT-MA': 'Atlantic/Madeira'}.get(
            self.company_id.l10n_pt_region_code, 'Europe/Lisbon',
        )

    def _l10n_pt_get_first_print_copy_labels(self):
        # A transport document is processed in three exemplars, for the recipient, the inspection
        # and the sender (RBC art. 5(2), 6(5)).
        if self.l10n_pt_document_number:
            return ['Original', 'Duplicado', 'Triplicado']
        return super()._l10n_pt_get_first_print_copy_labels()

    def _l10n_pt_check_printable(self):
        """
        Refuse to print a transport document before it is issued, i.e. numbered and signed, at
        validation or when communicated before its goods leave: printed earlier, it would travel with
        the goods unsigned (Despacho 8632/2014 1.6, 2.1.5). A transfer validated without one prints as a
        plain delivery slip; before its validation it is refused as well, since its first print is kept
        and an AT series set on its operation type in the meantime would still issue it. Each refusal
        says what to do instead of the missing QR code prerequisites.
        """
        not_issued = self.filtered(lambda p: not p.l10n_pt_document_number and p.state not in ('done', 'cancel'))
        if without_series := not_issued.filtered(lambda p: not p._l10n_pt_stock_at_series()):
            raise UserError(_(
                "%(transfers)s will be validated without a transport document, as its operation type has no "
                "AT series: its delivery slip can only be printed once it is validated. To prepare the "
                "goods, print the Picking Operations instead.",
                transfers=", ".join(without_series.mapped('name')),
            ))
        if not_issued:
            raise UserError(_(
                "A transport document can only be printed once it is issued, when its transfer is "
                "validated or communicated to the AT before its goods leave: %(transfers)s. To prepare "
                "the goods, print the Picking Operations instead.",
                transfers=", ".join(not_issued.mapped('name')),
            ))
        issued = self.filtered('l10n_pt_document_number')
        issued._l10n_pt_compute_missing_hashes()
        if unsigned := issued.filtered(lambda p: not p.l10n_pt_inalterable_hash):
            raise UserError(_(
                "%(documents)s could not be signed yet, so it cannot be printed. The signing service may "
                "be unavailable: try again in a moment.",
                documents=", ".join(unsigned.mapped('l10n_pt_document_number')),
            ))

    def action_open_reprint_wizard(self):
        self.ensure_one()
        if self.country_code == 'PT' and self.l10n_pt_document_number and self.l10n_pt_print_version:
            return {
                'name': _('Reprint Reason'),
                'type': 'ir.actions.act_window',
                'res_model': 'l10n_pt.reprint.reason',
                'view_mode': 'form',
                'target': 'new',
            }
        return self.env.ref('stock.action_report_delivery').report_action(self)

    ####################################
    # HASH AND QR CODE
    ####################################

    def _l10n_pt_get_document_date(self):
        self.ensure_one()
        return self.l10n_pt_issue_date

    def _l10n_pt_get_gross_total(self):
        """Transfers have no monetary total."""
        return 0

    def _l10n_pt_get_document_type(self):
        """
        The movement document this transfer is, by its nature (Portaria 302/2016 4.2.3.8, RBC art. 6(1),
        CIVA art. 36(3)), as a key of `l10n_pt.at.series.document_type`, or False when the company
        issues no transport document for it.
        """
        self.ensure_one()
        if self.l10n_pt_no_transport_document:
            return False
        code = self.picking_type_id.code
        if code == 'outgoing':
            # Goods received and sent back to their supplier travel under a return note (GD).
            document_type = 'incoming' if self.return_id.picking_type_code == 'incoming' else 'outgoing'
        elif code == 'internal':
            # Only a move between two of the company's sites puts goods in circulation (GT).
            document_type = 'outgoing' if self.location_id.warehouse_id != self.location_dest_id.warehouse_id else False
        else:
            # Receipts and customer returns: the sender issues the transport document.
            return False
        # Goods leaving Portugal, to another member state or a third country, are outside the RBC
        # (art. 3(2)(b)-(c)); a destination without a country is taken to be in Portugal.
        _loading, unloading = self._l10n_pt_get_loading_and_unloading_places()
        if document_type and unloading.country_id and unloading.country_id.code != 'PT':
            return False
        return document_type

    def _l10n_pt_get_saft_doc_type(self):
        self.ensure_one()
        return SAFT_PT_MOVEMENT_TYPE_MAP[self.l10n_pt_document_type]

    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return []
        return ['l10n_pt_issue_date', 'l10n_pt_hashed_on', 'name', 'l10n_pt_document_number']

    def _l10n_pt_protected_fields(self):
        return super()._l10n_pt_protected_fields() + ['l10n_pt_at_series_id']

    def _l10n_pt_chain_domain(self, at_series):
        # A series is addressed by the kind of movement it covers, not only by its id.
        return [
            *super()._l10n_pt_chain_domain(at_series),
            ('l10n_pt_document_type', '=', at_series.document_type),
        ]

    def _l10n_pt_document_label(self, at_series):
        return 'delivery order', 'delivery orders', self.env._('Delivery orders')

    def _l10n_pt_qr_get_customer(self):
        # The recipient the transport document prints: the company itself between its own sites
        # (Portaria 302/2016 4.2.3.11).
        return self._l10n_pt_get_recipient()

    def _l10n_pt_get_tax_details_by_region(self):
        # A transfer has no monetary total and no taxes: its QR code reads I1:0.
        return {}

    def _calculate_hashes(self, previous_hash=None):
        # Validation goes on without a signature, which is retried later; issuing to communicate does not.
        try:
            return super()._calculate_hashes(previous_hash=previous_hash)
        except UserError as e:
            if self.env.context.get('l10n_pt_stock_raise_signing_errors'):
                raise
            self._message_log_batch(bodies={p.id: e.args[0] for p in self})
            return {}

    @api.model
    def _l10n_pt_find_last_hashed(self, at_series):
        return self.sudo().search([
            ('l10n_pt_at_series_id', '=', at_series.id),
            ('l10n_pt_document_type', '=', at_series.document_type),
            ('l10n_pt_inalterable_hash', '!=', False),
        ], order='l10n_pt_sequence_number desc', limit=1)

    def _l10n_pt_get_unhashed_records(self, at_series):
        return self.sudo().search([
            ('l10n_pt_at_series_id', '=', at_series.id),
            ('l10n_pt_document_type', '=', at_series.document_type),
            # Only issued transfers: numbered at validation, or while ready to be communicated first.
            ('l10n_pt_document_number', '!=', False),
            ('l10n_pt_inalterable_hash', '=', False),
        ], order='l10n_pt_sequence_number')

    def _l10n_pt_validate_before_hash(self):
        for picking in self:
            if not picking.l10n_pt_document_number:
                raise UserError(_("Transfer %s does not have a Document Number. "
                                  "Verify that its operation type has an AT Series.", picking.name))

    def _l10n_pt_post_hash_hook(self):
        for picking in self:
            picking.message_post(body=_("The delivery order was successfully signed."))

    def _cron_l10n_pt_stock_compute_missing_hashes(self):
        for company in self.env['res.company'].search([
            ('account_fiscal_country_id.code', '=', 'PT'),
        ]):
            self._l10n_pt_compute_missing_hashes(company)
