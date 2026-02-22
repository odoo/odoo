import urllib.parse

from odoo import _, api, models, fields
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import float_repr

from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils


SAFT_PT_MOVEMENT_TYPE_MAP = {
    'outgoing': 'GT',
    'internal': 'GA',
    'incoming': 'GD',
}


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')
    l10n_pt_stock_at_series_id = fields.Many2one('l10n_pt.at.series', string="Official Series of the Tax Authority")
    l10n_pt_stock_at_series_line_id = fields.Many2one(
        'l10n_pt.at.series.line',
        string="Document-specific AT Series",
        compute='_compute_l10n_pt_stock_at_series_line_id',
    )

    _sql_constraints = [
        (
            'at_series_code_unique',
            'unique(l10n_pt_stock_at_series_id, code)',
            'An AT series cannot be assigned to multiple Operation Types.'
        )
    ]

    @api.depends('l10n_pt_stock_at_series_id')
    def _compute_l10n_pt_stock_at_series_line_id(self):
        for (code, series), orders in self.grouped(lambda o: (o.code, o.l10n_pt_stock_at_series_id)).items():
            orders.l10n_pt_stock_at_series_line_id = series._get_line_for_type(code) if series else None

    @api.constrains('l10n_pt_stock_at_series_id')
    def _check_l10n_pt_stock_at_series_id(self):
        for picking_type in self:
            if (
                picking_type.country_code == 'PT'
                and picking_type.l10n_pt_stock_at_series_id
                and not picking_type.l10n_pt_stock_at_series_line_id.filtered(lambda l: l.type == picking_type.code)
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
    _inherit = "stock.picking"

    l10n_pt_stock_qr_code_str = fields.Char(string="Portuguese QR Code", compute='_compute_l10n_pt_stock_qr_code_str')
    l10n_pt_stock_inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    l10n_pt_inalterable_hash_short = fields.Char(
        string="Short version of the Portuguese hash",
        compute='_compute_l10n_pt_stock_inalterable_hash_info',
    )
    l10n_pt_stock_inalterable_hash_version = fields.Integer(
        string="Portuguese hash version",
        compute='_compute_l10n_pt_stock_inalterable_hash_info',
    )
    l10n_pt_stock_atcud = fields.Char(string="Portuguese ATCUD", readonly=True, copy=False)
    l10n_pt_document_number = fields.Char(
        string="Unique Document Number",
        compute='_compute_l10n_pt_document_number', store=True,
        help="Unique identifier made up of the internal document type code, the series name, "
             "and the number of the document within the series.",
    )
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True)
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

    def write(self, vals):
        if not vals:
            return True
        for picking in self.filtered(lambda p: p.country_code == 'PT'):
            violated_fields = set(vals).intersection(picking._get_integrity_hash_fields() + ['l10n_pt_stock_inalterable_hash'])
            if violated_fields and picking.l10n_pt_stock_inalterable_hash:
                raise UserError(_(
                    "This document is protected by a hash. "
                    "Therefore, you cannot edit the following fields: %s.",
                    ', '.join(f['string'] for f in self.fields_get(violated_fields).values())
                ))
        return super().write(vals)

    def button_validate(self):
        picking = super().button_validate()
        for picking in self.filtered(lambda p: p.country_code == 'PT' and p.state == 'done'):
            picking._l10n_pt_check_date()
        return picking

    ####################################
    # MISC REQUIREMENTS
    ####################################

    @api.depends('picking_type_id.l10n_pt_stock_at_series_line_id')
    def _compute_l10n_pt_show_no_at_series_warning(self):
        for picking in self:
            picking.l10n_pt_show_no_at_series_warning = not picking.picking_type_id.l10n_pt_stock_at_series_line_id

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

    def update_l10n_pt_print_version(self):
        for picking in self.filtered(lambda o: o.country_code == 'PT'):
            if not picking.l10n_pt_print_version:
                picking.l10n_pt_print_version = 'original'
            else:
                picking.l10n_pt_print_version = 'reprint'

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

    @api.depends('picking_type_id.l10n_pt_stock_at_series_line_id', 'company_id', 'state')
    def _compute_l10n_pt_document_number(self):
        for picking in self:
            if (
                picking.country_code == 'PT'
                and picking.picking_type_id.l10n_pt_stock_at_series_line_id
                and picking.state != 'draft'
                and not picking.l10n_pt_document_number
            ):
                picking.l10n_pt_document_number = picking.picking_type_id.l10n_pt_stock_at_series_line_id._l10n_pt_get_document_number_sequence().next_by_id()

    ####################################
    # HASH AND QR CODE
    ####################################

    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return []
        return ['date_done', 'l10n_pt_hashed_on', 'name', 'l10n_pt_document_number']

    def _get_l10n_pt_stock_document_number(self):
        """ Allows patching in tests """
        self.ensure_one()
        return self.l10n_pt_document_number

    def _get_l10n_pt_stock_gross_total(self):
        """ Allows patching in tests """
        return 0

    def _calculate_hashes(self, previous_hash=None):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return {}
        self.l10n_pt_hashed_on = fields.Datetime.now()
        docs_to_sign = [{
            'id': picking.id,
            'date': picking.date_done.strftime('%Y-%m-%d'),
            'sorting_key': picking.date_done.isoformat(),
            'system_entry_date': picking.l10n_pt_hashed_on.isoformat(timespec='seconds'),
            'name': picking._get_l10n_pt_stock_document_number(),
            'gross_total': float_repr(picking._get_l10n_pt_stock_gross_total(), precision_digits=2),
            'previous_signature': previous_hash,
        } for picking in self]
        try:
            return pt_hash_utils.sign_records(self.env, docs_to_sign, 'stock.picking')
        except UserError as e:
            self._message_log_batch(bodies={p.id: e.args[0] for p in self})
            return {}

    @api.depends('l10n_pt_stock_inalterable_hash')
    def _compute_l10n_pt_stock_inalterable_hash_info(self):
        for picking in self:
            if picking.l10n_pt_stock_inalterable_hash:
                hash_version, hash_str = picking.l10n_pt_stock_inalterable_hash.split("$")[1:]
                picking.l10n_pt_stock_inalterable_hash_version = int(hash_version)
                picking.l10n_pt_inalterable_hash_short = hash_str[0] + hash_str[10] + hash_str[20] + hash_str[30]
            else:
                picking.l10n_pt_stock_inalterable_hash_version = False
                picking.l10n_pt_inalterable_hash_short = False

    @api.model
    def _find_last_picking(self, at_series_line):
        return self.sudo().search([
            ('l10n_pt_at_series_id', '=', at_series_line.at_series_id.id),
            ('picking_type_code', '=', at_series_line.type),
            ('l10n_pt_stock_inalterable_hash', '!=', False),
        ], order='date_done desc', limit=1)

    def _l10n_pt_compute_missing_hashes(self, company=None):
        """
        Compute the hash/atcud for all records that do not have one yet
        (because they were not printed/previewed yet)
        """
        company = company or self.env.company

        # Get all AT series lines that apply to stock.pickings to find unhashed pickings per series
        at_series_lines = self.env['l10n_pt.at.series.line'].search([
            '|',
            '&',
            ('company_id', '=', company.id),
            ('company_exclusive_series', '=', True),
            '&',
            ('company_id', 'in', company.parent_ids.ids),
            ('company_exclusive_series', '=', False),
            ('type', 'in', ('outgoing', 'internal', 'incoming')),
        ])
        unhashed_pickings = self.sudo().search([
            ('l10n_pt_at_series_id', 'in', at_series_lines.mapped('at_series_id.id')),
            ('state', '=', 'done'),
            ('l10n_pt_stock_inalterable_hash', '=', False),
        ], order='date_done')

        # Group unhashed pickings by AT series and picking type. This allows matching pickings with their AT Series line
        pickings_grouped = unhashed_pickings.grouped(lambda p: (p.l10n_pt_at_series_id.id, p.picking_type_code))
        for at_series_line in at_series_lines:
            pickings = pickings_grouped.get((at_series_line.at_series_id.id, at_series_line.type))
            if not pickings:
                continue

            previous_picking = self._find_last_picking(at_series_line)
            try:
                previous_hash = previous_picking.l10n_pt_stock_inalterable_hash.split("$")[2] if previous_picking.l10n_pt_stock_inalterable_hash else ""
            except IndexError:  # hash is not correctly formatted (it has been altered!)
                previous_hash = "invalid_hash"  # will never be a valid hash
            for picking in pickings:
                if not picking.l10n_pt_document_number:
                    raise UserError(_("Transfer %s does not have a Unique Document Number. "
                                      "Verify that its operation type has an AT Series.", picking.name))
                current_atcud_number = int(picking.l10n_pt_document_number.split('/')[-1])
                picking.l10n_pt_stock_atcud = f"{at_series_line._get_at_code()}-{current_atcud_number}"

            pickings_hashes = pickings._calculate_hashes(previous_hash)
            for picking, l10n_pt_stock_inalterable_hash in pickings_hashes.items():
                picking.l10n_pt_stock_inalterable_hash = l10n_pt_stock_inalterable_hash
                picking.message_post(body=_("The delivery order was successfully signed."))

    def _cron_l10n_pt_stock_compute_missing_hashes(self):
        for company in self.env['res.company'].search([
            ('account_fiscal_country_id.code', '=', 'PT'),
        ]):
            self._l10n_pt_compute_missing_hashes(company)

    def l10n_pt_verify_prerequisites_qr_code(self):
        self.ensure_one()
        if self.country_code == 'PT':
            return pt_hash_utils.verify_prerequisites_qr_code(self, self.l10n_pt_stock_inalterable_hash, self.l10n_pt_stock_atcud)

    @api.depends('l10n_pt_stock_atcud')
    def _compute_l10n_pt_stock_qr_code_str(self):
        """ Generate the informational QR code for Portugal
        E.g.: A:509445535*B:123456823*C:BE*D:GT*E:N*F:20220103*G:GT 01P2022/1*H:0*I1:PT*I7:325.20*I8:74.80*N:74.80*O:400.00*P:0.00*Q:P0FE*R:2230
        """
        for picking in self.filtered(lambda p: (
            not p.l10n_pt_stock_qr_code_str  # Skip if already computed
        )):
            if picking.country_code != "PT" or not picking.l10n_pt_stock_inalterable_hash:
                picking.l10n_pt_stock_qr_code_str = False
                continue

            picking.l10n_pt_verify_prerequisites_qr_code()
            # Most of the values needed for the QR Code string are filled in pt_hash_utils
            qr_code_dict, _tax_letter = pt_hash_utils.l10n_pt_common_qr_code_str(picking, self.env, picking.date_done)
            qr_code_dict['D:'] = f"{SAFT_PT_MOVEMENT_TYPE_MAP[picking.picking_type_id.code]}*"
            qr_code_dict['H:'] = f"{picking.l10n_pt_stock_atcud}*"
            qr_code_dict['N:'] = "0.00*"
            qr_code_dict['O:'] = "0.00*"
            qr_code_dict['Q:'] = f"{picking.l10n_pt_inalterable_hash_short}*"
            qr_code_str = ''.join(f"{key}{value}" for key, value in sorted(qr_code_dict.items()))
            picking.l10n_pt_stock_qr_code_str = urllib.parse.quote_plus(qr_code_str)
