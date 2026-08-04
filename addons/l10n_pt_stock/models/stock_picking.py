from odoo import _, api, models, fields
from odoo.exceptions import RedirectWarning, UserError

from odoo.addons.l10n_pt_stock.models.l10n_pt_at_series import AT_SERIES_MOVEMENT_DOCUMENT_TYPES


SAFT_PT_MOVEMENT_TYPE_MAP = {
    'outgoing': 'GT',
    'internal': 'GA',
    'incoming': 'GD',
}


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')
    l10n_pt_stock_at_series_id = fields.Many2one('l10n_pt.at.series', string="Official Series of the Tax Authority")

    _at_series_code_unique = models.Constraint(
        'unique(l10n_pt_stock_at_series_id, code)',
        'An AT series cannot be assigned to multiple Operation Types.',
    )

    @api.constrains('l10n_pt_stock_at_series_id')
    def _check_l10n_pt_stock_at_series_id(self):
        for picking_type in self:
            if (
                picking_type.country_code == 'PT'
                and picking_type.l10n_pt_stock_at_series_id
                and picking_type.l10n_pt_stock_at_series_id.document_type != picking_type.code
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
                    _("There is no AT series for this Operation Type registered under the series name %(series_name)s."
                      "Create a new series or view existing series via the Accounting Settings.",
                      series_name=picking_type.l10n_pt_stock_at_series_id.name),
                    action_error,
                    _('Add an AT Series'),
                )


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "l10n.pt.hashed.document.mixin"]

    _l10n_pt_date_field = "date_done"
    _l10n_pt_document_type_depends = ('picking_type_id', 'company_id')

    l10n_pt_document_type = fields.Selection(selection_add=AT_SERIES_MOVEMENT_DOCUMENT_TYPES)
    l10n_pt_at_series_id = fields.Many2one(
        related='picking_type_id.l10n_pt_stock_at_series_id',
        string="AT Series",
    )
    l10n_pt_start_transport_date = fields.Datetime(
        'Start of Transport Date',
        store=True,
        default=fields.Datetime.now,
        tracking=True,
        help="Date and time of start of transport",
    )
    l10n_pt_show_no_at_series_warning = fields.Boolean(compute='_compute_l10n_pt_show_no_at_series_warning')

    ####################################
    # OVERRIDES
    ####################################

    def action_confirm(self):
        res = super().action_confirm()
        # A transport document must legally carry its number before the goods move, so it is
        # allocated as soon as the picking leaves draft. `button_validate` funnels draft pickings
        # through here too, so this covers every path out of draft.
        self.filtered(lambda p: p.country_code == 'PT')._set_l10n_pt_document_number()
        return res

    def button_validate(self):
        picking = super().button_validate()
        self.filtered(lambda p: p.country_code == 'PT' and p.state == 'done')._check_l10n_pt_dates()
        return picking

    ####################################
    # MISC REQUIREMENTS
    ####################################

    @api.depends('picking_type_id.l10n_pt_stock_at_series_id')
    def _compute_l10n_pt_show_no_at_series_warning(self):
        for picking in self:
            picking.l10n_pt_show_no_at_series_warning = not picking.picking_type_id.l10n_pt_stock_at_series_id

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
        # A transfer cancelled before validation never gets a `date_done`, yet it was issued and
        # numbered at confirmation, so it still has to be signed. Fall back to the transport date,
        # which always has a value. Transfers that were validated keep signing `date_done`, so no
        # existing signature changes.
        return self.date_done or self.l10n_pt_start_transport_date

    def _l10n_pt_get_gross_total(self):
        """ Returns 0 (transfers have no monetary total). Split out to allow patching in tests. """
        return 0

    def _l10n_pt_get_document_type(self):
        self.ensure_one()
        code = self.picking_type_id.code
        return code if code in SAFT_PT_MOVEMENT_TYPE_MAP else False

    def _l10n_pt_get_saft_doc_type(self):
        self.ensure_one()
        return SAFT_PT_MOVEMENT_TYPE_MAP[self.l10n_pt_document_type]

    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return []
        return ['date_done', 'l10n_pt_hashed_on', 'name', 'l10n_pt_document_number']

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
            ('picking_type_code', '=', at_series.document_type),
            ('l10n_pt_inalterable_hash', '!=', False),
        ], order='l10n_pt_document_number desc', limit=1)

    def _l10n_pt_get_unhashed_records(self, at_series):
        return self.sudo().search([
            ('l10n_pt_at_series_id', '=', at_series.id),
            ('picking_type_code', '=', at_series.document_type),
            # A cancelled transfer keeps the number it consumed at confirmation, so it stays part of
            # the chain and is reported as cancelled -- same treatment as a cancelled invoice.
            ('state', 'in', ('done', 'cancel')),
            ('l10n_pt_inalterable_hash', '=', False),
        ], order='l10n_pt_document_number')

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
