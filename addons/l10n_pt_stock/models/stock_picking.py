from odoo import api, models, fields, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import float_repr

from odoo.addons.l10n_pt.utils import hashing as pt_hash_utils
from odoo.addons.l10n_pt_stock.models.l10n_pt_at_series import AT_SERIES_MOVEMENT_DOCUMENT_TYPES


SAFT_PT_MOVEMENT_TYPE_MAP = {
    'outgoing': 'GT',
    'internal': 'GA',
    'incoming': 'GD',
}


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', depends=['company_id.account_fiscal_country_id'])
    l10n_pt_stock_at_series_id = fields.Many2one('l10n_pt.at.series', string="Official Series of the Tax Authority")
    l10n_pt_stock_at_series_line_id = fields.Many2one(
        'l10n_pt.at.series.line',
        string="Document-specific AT Series",
        compute='_compute_l10n_pt_stock_at_series_line_id',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('l10n_pt_stock_at_series_id'):
                continue
            if self.env['stock.picking.type'].search_count([
                ('l10n_pt_stock_at_series_id', '=', vals['l10n_pt_stock_at_series_id']),
                ('code', '=', vals['code']),
            ], limit=1):
                raise UserError(_("You cannot use the same AT series for more than one Picking Type with the same operation type."))
        return super().create(vals_list)

    def write(self, vals):
        for picking_type in self:
            if 'l10n_pt_stock_at_series_id' not in vals:
                continue
            if vals['l10n_pt_stock_at_series_id'] and picking_type.search_count([
                ('l10n_pt_stock_at_series_id', '=', vals['l10n_pt_stock_at_series_id']),
                ('id', '!=', picking_type.id),
                ('code', '=', picking_type.code),
            ], limit=1):
                raise UserError(_("You cannot use the same AT series for more than one Picking Type with the same operation type."))
        return super(PickingType, self).write(vals)

    @api.depends('l10n_pt_stock_at_series_id')
    def _compute_l10n_pt_stock_at_series_line_id(self):
        for picking_type in self:
            if picking_type.l10n_pt_stock_at_series_id:
                picking_type.l10n_pt_stock_at_series_line_id = self.env['l10n_pt.at.series.line'].search([
                    ('at_series_id', '=', picking_type.l10n_pt_stock_at_series_id.id),
                    ('type', '=', picking_type.code)
                ])
            else:
                picking_type.l10n_pt_stock_at_series_line_id = None

    @api.constrains('l10n_pt_stock_at_series_id')
    def _check_l10n_pt_stock_at_series_id(self):
        for picking_type in self:
            if (
                picking_type.company_id.country_id.code == 'PT'
                and picking_type.l10n_pt_stock_at_series_id
                and not picking_type.l10n_pt_stock_at_series_line_id.filtered(lambda line: line.type == picking_type.code)
            ):
                action_error = {
                    'view_mode': 'form',
                    'name': _('Draft Entries'),
                    'res_model': 'l10n_pt.at.series',
                    'res_id': picking_type.l10n_pt_stock_at_series_id.id,
                    'type': 'ir.actions.act_window',
                    'views': [[self.env.ref('l10n_pt.view_l10n_pt_at_series_form').id, 'form']],
                    'target': 'new',
                }
                raise RedirectWarning(
                    _("There is no AT series for this Picking Type registered under the series name %(series_name)s. Create a new series or view existing series via the Accounting Settings.",
                      series_name=picking_type.l10n_pt_stock_at_series_id.name),
                    action_error,
                    _('Add an AT Series'),
                )


class StockPicking(models.Model):
    _inherit = "stock.picking"

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', depends=['company_id.account_fiscal_country_id'])
    l10n_pt_stock_qr_code_str = fields.Char(string="Portuguese QR Code", compute='_compute_l10n_pt_stock_qr_code_str')
    l10n_pt_stock_inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    l10n_pt_inalterable_hash_short = fields.Char(string="Short version of the Portuguese hash", compute='_compute_l10n_pt_stock_inalterable_hash_info')
    l10n_pt_stock_inalterable_hash_version = fields.Integer(string="Portuguese hash version", compute='_compute_l10n_pt_stock_inalterable_hash_info')
    l10n_pt_stock_atcud = fields.Char(string="Portuguese ATCUD", readonly=True, copy=False)
    l10n_pt_document_number = fields.Char(
        string="Unique Document Number",
        compute='_compute_l10n_pt_document_number', store=True,
        help="Unique identifier made up of the internal document type code, the series name, and the number of the document within the series.",
    )
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True)
    # Document type used in invoice template (when printed, documents have to present the document type on each page)
    l10n_pt_document_type = fields.Selection(
        selection=AT_SERIES_MOVEMENT_DOCUMENT_TYPES,
        string="Portuguese Document Type",
        compute='_compute_l10n_pt_document_type',
        store=True,
    )
    # Required for the report template, to identify training series
    l10n_pt_at_series_id = fields.Many2one('l10n_pt.at.series', string="AT Series", compute='_compute_l10n_pt_at_series_id')

    ####################################
    # OVERRIDES
    ####################################

    def write(self, vals):
        if not vals:
            return True
        for picking in self.filtered(lambda p: p.company_id.account_fiscal_country_id.code == 'PT'):
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
        for picking in self.filtered(lambda p: p.company_id.account_fiscal_country_id.code == "PT"):
            picking._l10n_pt_check_date()
        return picking

    ####################################
    # MISC REQUIREMENTS
    ####################################

    def _l10n_pt_check_date(self):
        """
        According to the Portuguese tax authority:
        "When the document issuing date is later than the current date, or superior than the date on the system,
        no other document may be issued with the current or previous date within the same series"
        """
        max_hashed_on_date = self.env['stock.picking'].search(
            [('l10n_pt_hashed_on', '!=', False)],
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
                picking.company_id.account_fiscal_country_id.code == 'PT'
                and picking.picking_type_id.l10n_pt_stock_at_series_line_id
                and picking.state != 'draft'
                and not picking.l10n_pt_document_number
            ):
                picking.l10n_pt_document_number = picking.picking_type_id.l10n_pt_stock_at_series_line_id._l10n_pt_get_document_number_sequence().next_by_id()
            else:
                picking.l10n_pt_document_number = False

    @api.depends('company_id', 'picking_type_id.l10n_pt_stock_at_series_id')
    def _compute_l10n_pt_at_series_id(self):
        for picking in self:
            if picking.company_id.account_fiscal_country_id.code == 'PT' and picking.picking_type_id.l10n_pt_stock_at_series_id:
                picking.l10n_pt_at_series_id = picking.picking_type_id.l10n_pt_stock_at_series_id
            else:
                picking.l10n_pt_at_series_id = False

    @api.depends('picking_type_id')
    def _compute_l10n_pt_document_type(self):
        for picking in self:
            if (
                picking.company_id.account_fiscal_country_id.code == 'PT'
                and picking.picking_type_id.l10n_pt_stock_at_series_line_id
            ):
                picking.l10n_pt_document_type = picking.picking_type_id.code
            else:
                picking.l10n_pt_document_type = False

    ####################################
    # HASH AND QR CODE
    ####################################

    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return []
        return ['date_done', 'l10n_pt_hashed_on', 'name']

    def _get_l10n_pt_stock_document_number(self):
        self.ensure_one()
        return self.l10n_pt_document_number

    def _get_l10n_pt_stock_gross_total(self):
        return 0

    @api.model
    def _find_last_picking(self, company_id, at_series):
        return self.sudo().search([
            ('company_id', '=', company_id),
            ('l10n_pt_document_number', '=like', f'{at_series.document_identifier}%'),
            ('l10n_pt_stock_inalterable_hash', '!=', False),
        ], order='date_done desc', limit=1)

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

    def _l10n_pt_stock_compute_missing_hashes(self, company_id=None):
        """
        Compute the hash/atcud for all records that do not have one yet
        (because they were not printed/previewed yet)
        """
        company_id = company_id or self.company_id.id

        # Get all picking types with an AT series to find pickings of that type
        at_series_lines = self.env['l10n_pt.at.series.line'].search([
            ('company_id', '=', company_id),
            ('type', 'in', ('outgoing', 'internal', 'incoming')),
        ])
        for at_series in at_series_lines:
            pickings = self.sudo().search([
                ('company_id', '=', company_id),
                ('l10n_pt_document_number', '=like', f'{at_series.document_identifier}%'),
                ('state', '=', 'done'),
                ('l10n_pt_stock_inalterable_hash', '=', False),
            ], order='date_done')

            previous_picking = self._find_last_picking(company_id, at_series)
            try:
                previous_hash = previous_picking.l10n_pt_stock_inalterable_hash.split("$")[2] if previous_picking.l10n_pt_stock_inalterable_hash else ""
            except IndexError:  # hash is not correctly formatted (it has been altered!)
                previous_hash = "invalid_hash"  # will never be a valid hash
            current_atcud_number = int(previous_picking.l10n_pt_stock_atcud.split("-")[-1]) + 1 if previous_picking.l10n_pt_stock_atcud else 1
            for picking in pickings:
                at_series = picking.picking_type_id.l10n_pt_stock_at_series_line_id
                picking.l10n_pt_stock_atcud = f"{at_series._get_at_code()}-{current_atcud_number}"
                current_atcud_number += 1

            pickings_hashes = pickings._calculate_hashes(previous_hash)
            for picking, l10n_pt_stock_inalterable_hash in pickings_hashes.items():
                picking.l10n_pt_stock_inalterable_hash = l10n_pt_stock_inalterable_hash
                picking.message_post(body=_("The delivery order was successfully signed."))

    def _cron_l10n_pt_stock_compute_missing_hashes(self):
        for company in self.env['res.company'].search([
            ('account_fiscal_country_id.code', '=', 'PT'),
        ]):
            self._l10n_pt_stock_compute_missing_hashes(company.id)

    @api.depends('l10n_pt_stock_atcud')
    def _compute_l10n_pt_stock_qr_code_str(self):
        """ Generate the informational QR code for Portugal
        E.g.: A:509445535*B:123456823*C:BE*D:FT*E:N*F:20220103*G:GT 01P2022/1*H:0*I1:PT*I7:325.20*I8:74.80*N:74.80*O:400.00*P:0.00*Q:P0FE*R:2230
        """
        for picking in self.filtered(lambda p: (
            not p.l10n_pt_stock_qr_code_str  # Skip if already computed
        )):
            if picking.company_id.account_fiscal_country_id.code != "PT" or not picking.l10n_pt_stock_inalterable_hash:
                picking.l10n_pt_stock_qr_code_str = False
                continue

            pt_hash_utils.verify_prerequisites_qr_code(picking, picking.l10n_pt_stock_inalterable_hash, picking.l10n_pt_stock_atcud)
            # Most of the values needed for the QR Code string are filled in pt_hash_utils
            qr_code_dict, _tax_letter = pt_hash_utils.l10n_pt_common_qr_code_str(picking, self.env, picking.date_done)
            qr_code_dict['D:'] = f"{SAFT_PT_MOVEMENT_TYPE_MAP[picking.picking_type_id.code]}*"
            qr_code_dict['G:'] = f"{picking._get_l10n_pt_stock_document_number()}*"
            qr_code_dict['H:'] = f"{picking.l10n_pt_stock_atcud}*"
            qr_code_dict['N:'] = "0.00*"
            qr_code_dict['O:'] = "0.00*"
            qr_code_dict['Q:'] = f"{picking.l10n_pt_inalterable_hash_short}*"
            qr_code_str = ''.join(f"{key}{value}" for key, value in sorted(qr_code_dict.items()))
            picking.l10n_pt_stock_qr_code_str = qr_code_str
