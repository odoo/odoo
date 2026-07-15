from odoo import _, api, models, fields
from odoo.exceptions import RedirectWarning, UserError


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

    l10n_pt_document_number = fields.Char(
        compute='_compute_l10n_pt_document_number', store=True,
        help="Unique identifier made up of the internal document type code, the series name, "
             "and the number of the document within the series.",
    )
    # Document type is used in the template (when printed, documents have to present the document type on each page)
    l10n_pt_document_type = fields.Selection(
        string="Portuguese Document Type",
        related='picking_type_id.code',
    )
    l10n_pt_at_series_id = fields.Many2one(
        related='picking_type_id.l10n_pt_stock_at_series_id',
        string="AT Series",
    )
    l10n_pt_print_version = fields.Selection(
        selection=[
            ('original', 'Original'),
            ('reprint', 'Reprint'),
        ],
        string="Version of Printed Document",
        copy=False,
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

    def button_validate(self):
        picking = super().button_validate()
        for picking in self.filtered(lambda p: p.country_code == 'PT' and p.state == 'done'):
            picking._l10n_pt_check_date()
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

    def _l10n_pt_check_date(self):
        """
        According to the Portuguese tax authority:
        "When the document issuing date is later than the current date, or superior than the date on the system,
        no other document may be issued with the current or previous date within the same series"
        """
        self.ensure_one()
        max_hashed_on_date = self.env['stock.picking'].search([
            ('l10n_pt_hashed_on', '!=', False),
            ('l10n_pt_at_series_id', '=', self.l10n_pt_at_series_id.id),
        ],
            order='l10n_pt_hashed_on desc',
            limit=1
        ).l10n_pt_hashed_on

        if max_hashed_on_date and max_hashed_on_date > fields.Datetime.now():
            raise UserError(_("There exists secured stock pickings with a lock date ahead of the present time."))

    ####################################
    # PT FIELDS - ATCUD, AT SERIES
    ####################################

    @api.depends('picking_type_id.l10n_pt_stock_at_series_id', 'company_id', 'state')
    def _compute_l10n_pt_document_number(self):
        for picking in self:
            if (
                picking.country_code == 'PT'
                and picking.picking_type_id.l10n_pt_stock_at_series_id
                and picking.state != 'draft'
                and not picking.l10n_pt_document_number
            ):
                picking.l10n_pt_document_number = picking.picking_type_id.l10n_pt_stock_at_series_id._l10n_pt_get_document_number_sequence().next_by_id()

    ####################################
    # HASH AND QR CODE
    ####################################

    def _l10n_pt_get_document_date(self):
        self.ensure_one()
        return self.date_done

    def _l10n_pt_get_document_number(self):
        """ Allows patching in tests """
        self.ensure_one()
        return self.l10n_pt_document_number

    def _l10n_pt_get_gross_total(self):
        """ Returns 0 (transfers have no monetary total). Split out to allow patching in tests. """
        return 0

    def _l10n_pt_get_saft_doc_type(self):
        self.ensure_one()
        return SAFT_PT_MOVEMENT_TYPE_MAP[self.picking_type_id.code]

    def _l10n_pt_series_document_types(self):
        return ('outgoing', 'internal', 'incoming')

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
        ], order='date_done desc', limit=1)

    def _l10n_pt_get_unhashed_records(self, at_series):
        return self.sudo().search([
            ('l10n_pt_at_series_id', '=', at_series.id),
            ('picking_type_code', '=', at_series.document_type),
            ('state', '=', 'done'),
            ('l10n_pt_inalterable_hash', '=', False),
        ], order='date_done')

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

