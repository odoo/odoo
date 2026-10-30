from odoo import _, api, models, fields
from odoo.exceptions import RedirectWarning, UserError

from odoo.addons.l10n_pt_stock.models.l10n_pt_at_series import AT_SERIES_MOVEMENT_DOCUMENT_TYPES


# The RBC elements of a transport document held on the transfer (DL 147/2003 art. 4(2), 4(4)): once
# it is issued they are frozen (Despacho 8632/2014 1.11); goods and quantities are on its moves.
L10N_PT_ISSUED_PICKING_FIELDS = {
    'partner_id', 'location_id', 'location_dest_id', 'picking_type_id', 'l10n_pt_start_transport_date', 'company_id',
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
    l10n_pt_stock_at_series_id = fields.Many2one('l10n_pt.at.series', string="Official Series of the Tax Authority")
    l10n_pt_stock_return_at_series_id = fields.Many2one(
        comodel_name='l10n_pt.at.series',
        string="AT Series for Returns",
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

    @api.constrains('l10n_pt_stock_at_series_id', 'l10n_pt_stock_return_at_series_id', 'code')
    def _check_l10n_pt_stock_at_series_id(self):
        for picking_type in self.filtered(lambda t: t.country_code == 'PT'):
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

    _l10n_pt_date_field = "date_done"
    _l10n_pt_document_type_depends = ('picking_type_id', 'company_id', 'location_id', 'location_dest_id', 'return_id')

    l10n_pt_document_type = fields.Selection(selection_add=AT_SERIES_MOVEMENT_DOCUMENT_TYPES)
    l10n_pt_start_transport_date = fields.Datetime(
        'Start of Transport Date',
        tracking=True,
        help="Date and time of start of transport. Set to the validation time when the transfer is "
             "validated, unless a later start was entered.",
    )
    l10n_pt_show_no_at_series_warning = fields.Boolean(compute='_compute_l10n_pt_show_no_at_series_warning')

    ####################################
    # OVERRIDES
    ####################################

    def _action_done(self):
        res = super()._action_done()
        # A transport document is issued when the goods leave, before they circulate (RBC art.
        # 6(1)): it is numbered, dated (`date_done`) and signed here, in one step, so number order,
        # date order and chain order are the same (Despacho 8632/2014 1.6, 2.1.5). Numbered at
        # confirmation, transfers validated out of order broke the chain. Every path to `done`
        # (validate, backorders, barcode, RPC) goes through here.
        if pt_pickings := self.filtered(lambda p: p.country_code == 'PT' and p.state == 'done'):
            now = fields.Datetime.now()
            # The transport cannot start before the document exists; a later start entered by the
            # user is kept.
            for picking in pt_pickings.filtered(lambda p: not p.l10n_pt_document_number and p._l10n_pt_stock_at_series()):
                if not picking.l10n_pt_start_transport_date or picking.l10n_pt_start_transport_date < now:
                    picking.l10n_pt_start_transport_date = now
            pt_pickings._set_l10n_pt_document_number()
            pt_pickings._l10n_pt_compute_missing_hashes()
        return res

    def _l10n_pt_issued(self):
        """The transfers of ``self`` issued as PT transport documents: numbered, i.e. validated."""
        return self.filtered(lambda p: p.country_code == 'PT' and p.l10n_pt_document_number)

    def _l10n_pt_raise_if_issued(self, what):
        """Refuse a change of ``what`` (goods, quantities, ...) on transfers issued as transport documents."""
        if issued := self._l10n_pt_issued():
            raise UserError(_(
                "%(documents)s was issued as a transport document: its %(what)s can no longer be changed. "
                "Make a return to correct it.",
                documents=", ".join(issued.mapped('l10n_pt_document_number')),
                what=what,
            ))

    def write(self, vals):
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
        Refuse to print a transport document before it is issued, i.e. numbered and signed at
        validation: printed earlier, it would travel with the goods unsigned (Despacho 8632/2014
        1.6, 2.1.5). Each refusal says what to do instead of the missing QR code prerequisites.
        """
        if without_series := self.filtered(lambda p: not p.l10n_pt_document_number and not p._l10n_pt_stock_at_series()):
            raise UserError(_(
                "%(transfers)s should travel with a transport document, but its operation type has no AT "
                "series to issue it in. Set an AT series on the operation type: a transfer validated "
                "without one is not issued as a transport document and cannot be printed as one.",
                transfers=", ".join(without_series.mapped('name')),
            ))
        if not_issued := self.filtered(lambda p: not p.l10n_pt_document_number):
            raise UserError(_(
                "A transport document can only be printed once it is issued, when its transfer is "
                "validated: %(transfers)s. To prepare the goods, print the Picking Operations instead.",
                transfers=", ".join(not_issued.mapped('name')),
            ))
        self._l10n_pt_compute_missing_hashes()
        if unsigned := self.filtered(lambda p: not p.l10n_pt_inalterable_hash):
            raise UserError(_(
                "%(documents)s could not be signed yet, so it cannot be printed. The signing service may "
                "be unavailable: try again in a moment.",
                documents=", ".join(unsigned.mapped('l10n_pt_document_number')),
            ))

    def action_open_reprint_wizard(self):
        self.ensure_one()
        if self.country_code == 'PT' and self.l10n_pt_print_version:
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
        # A transfer is issued at validation, so an issued transfer always has a `date_done`.
        return self.date_done

    def _l10n_pt_get_gross_total(self):
        """ Returns 0 (transfers have no monetary total). Split out to allow patching in tests. """
        return 0

    def _l10n_pt_get_document_type(self):
        """
        The movement document this transfer is, by its nature (Portaria 302/2016 4.2.3.8, RBC art. 6(1),
        CIVA art. 36(3)), as a key of `l10n_pt.at.series.document_type`, or False when the company
        issues no transport document for it.
        """
        self.ensure_one()
        code = self.picking_type_id.code
        if code == 'outgoing':
            # Goods received and sent back to their supplier travel under a return note (GD).
            return 'incoming' if self.return_id.picking_type_code == 'incoming' else 'outgoing'
        if code == 'internal':
            # Only a move between two of the company's sites puts goods in circulation (GT).
            return 'outgoing' if self.location_id.warehouse_id != self.location_dest_id.warehouse_id else False
        # Receipts and customer returns: the sender issues the transport document.
        return False

    def _l10n_pt_get_saft_doc_type(self):
        self.ensure_one()
        return SAFT_PT_MOVEMENT_TYPE_MAP[self.l10n_pt_document_type]

    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return []
        return ['date_done', 'l10n_pt_hashed_on', 'name', 'l10n_pt_document_number']

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
        try:
            return super()._calculate_hashes(previous_hash=previous_hash)
        except UserError as e:
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
            # Only issued transfers: numbered at validation. A cancelled one is in the chain only if
            # it was issued before being cancelled.
            ('l10n_pt_document_number', '!=', False),
            ('state', 'in', ('done', 'cancel')),
            ('l10n_pt_inalterable_hash', '=', False),
        ], order='l10n_pt_sequence_number')

    def _l10n_pt_validate_before_hash(self):
        for picking in self:
            if not picking.l10n_pt_document_number:
                raise UserError(_("Transfer %s does not have a Unique Document Number. "
                                  "Verify that its operation type has an AT Series.", picking.name))

    def _l10n_pt_post_hash_hook(self):
        for picking in self:
            picking.message_post(body=_("The delivery order was successfully signed."))

    def _cron_l10n_pt_stock_compute_missing_hashes(self):
        for company in self.env['res.company'].search([
            ('account_fiscal_country_id.code', '=', 'PT'),
        ]):
            self._l10n_pt_compute_missing_hashes(company)
