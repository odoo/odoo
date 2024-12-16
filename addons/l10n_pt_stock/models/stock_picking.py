from odoo import api, models, fields, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import float_repr

from odoo.addons.l10n_pt.utils import hashing as pt_hash_utils

SAFT_PT_MOVEMENT_TYPE_MAP = {
    'outgoing_gt': 'GT',
    'internal_ga': 'GA',
    'incoming_gd': 'GD',
}

AT_SERIES_TYPE_MOVEMENT_TYPE_MAP = {
    'outgoing_gt': 'outgoing',
    'internal_ga': 'internal',
    'incoming_gd': 'incoming',
}


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', depends=['company_id.account_fiscal_country_id'])
    l10n_pt_stock_at_series_id = fields.Many2one(
        "l10n_pt.at.series",
        string="Official Series of the Tax Authority",
        compute="_compute_l10n_pt_stock_at_series_id",
        inverse="_inverse_l10n_pt_stock_at_series_id",
        store=True,
    )
    l10n_pt_stock_at_series_domain = fields.Binary(
        string="AT Series Domain",
        default=[],
        compute='_compute_l10n_pt_stock_at_series_domain',
    )

    def write(self, vals):
        for picking_type in self:
            if 'l10n_pt_stock_at_series_id' not in vals:
                continue
            if (
                picking_type.l10n_pt_stock_at_series_id
                and self.env['stock.picking'].search_count([
                    ('picking_type_id', '=', picking_type.id),
                    ('l10n_pt_stock_inalterable_hash', '!=', False),
                ], limit=1)
            ):
                raise UserError(_("You cannot change the AT series of a Picking Type once it has been used."))
            # AT series can be removed from a stock picking if the previous condition passes
            if vals['l10n_pt_stock_at_series_id'] and picking_type.search_count([
                ('l10n_pt_stock_at_series_id', '=', vals['l10n_pt_stock_at_series_id']),
                ('id', '!=', picking_type.id),
            ], limit=1):
                raise UserError(_("You cannot use the same AT series for more than one Picking Type."))
            at_series = self.env['l10n_pt.at.series'].browse(vals.get('l10n_pt_stock_at_series_id'))
            if at_series and AT_SERIES_TYPE_MOVEMENT_TYPE_MAP[at_series.type] != picking_type.code:
                raise UserError(_(
                    "The type of the series %(prefix)s (%(series_type)s) does not match the operation type %(picking_type_code)s.",
                    prefix=at_series.prefix,
                    series_type=dict(at_series._fields['type'].selection).get(at_series.type),
                    picking_type_code=f"{dict(picking_type._fields['code'].selection).get(picking_type.code)}",
                ))
        return super().write(vals)

    @api.depends('l10n_pt_stock_at_series_id.picking_type_id')
    def _compute_l10n_pt_stock_at_series_id(self):
        for picking_type in self:
            related_series = self.env['l10n_pt.at.series'].search([('picking_type_id', '=', picking_type.id)], limit=1)
            picking_type.l10n_pt_stock_at_series_id = related_series

    def _inverse_l10n_pt_stock_at_series_id(self):
        """Set picking_type_id in the linked series."""
        for picking_type in self:
            if picking_type.l10n_pt_stock_at_series_id:
                picking_type.l10n_pt_stock_at_series_id.picking_type_id = picking_type

    def _compute_l10n_pt_stock_at_series_domain(self):
        for picking_type in self:
            if picking_type.code == 'outgoing':
                picking_type.l10n_pt_stock_at_series_domain = [('type', '=', ('outgoing_gt'))]
            if picking_type.code == 'incoming':
                picking_type.l10n_pt_stock_at_series_domain = [('type', '=', 'incoming_gd')]
            if picking_type.code == 'internal':
                picking_type.l10n_pt_stock_at_series_domain = [('type', '=', 'internal_ga')]


class StockPicking(models.Model):
    _inherit = "stock.picking"

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', depends=['company_id.account_fiscal_country_id'])
    l10n_pt_stock_inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    l10n_pt_stock_inalterable_hash_short = fields.Char(string='Short version of the Portuguese hash', compute='_compute_l10n_pt_stock_inalterable_hash_info')
    l10n_pt_stock_inalterable_hash_version = fields.Integer(string='Portuguese hash version', compute='_compute_l10n_pt_stock_inalterable_hash_info')
    l10n_pt_stock_atcud = fields.Char(string='Portuguese ATCUD', readonly=True, copy=False)
    l10n_pt_stock_qr_code_str = fields.Char(string='Portuguese QR Code', compute='_compute_l10n_pt_stock_qr_code_str')
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True)
    l10n_pt_at_series_id = fields.Many2one("l10n_pt.at.series", string="Official Series of the Tax Authority", compute="_compute_l10n_pt_at_series_id")
    l10n_pt_document_type = fields.Char(string="Portuguese Document Type", compute='_compute_l10n_pt_document_type')
    l10n_pt_stock_document_type_code = fields.Char(string="Portuguese SAF-T Movement Document Code", readonly=True, copy=False)

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
    # GENERAL
    ####################################

    def _get_l10n_pt_stock_document_number(self):
        self.ensure_one()
        return f"{self.l10n_pt_stock_document_type_code or 'stock_picking'} {self.name}"

    def _get_l10n_pt_stock_gross_total(self):
        return 0

    @api.depends('picking_type_id')
    def _compute_l10n_pt_at_series_id(self):
        for picking in self:
            if picking.company_id.account_fiscal_country_id.code == 'PT':
                picking.l10n_pt_at_series_id = picking.picking_type_id.l10n_pt_stock_at_series_id
            else:
                picking.l10n_pt_at_series_id = None

    @api.depends('l10n_pt_at_series_id')
    def _compute_l10n_pt_document_type(self):
        for picking in self:
            if picking.company_id.account_fiscal_country_id.code == 'PT' and picking.l10n_pt_at_series_id:
                picking.l10n_pt_document_type = dict(picking.l10n_pt_at_series_id._fields['type'].selection).get(picking.l10n_pt_at_series_id.type)
            else:
                picking.l10n_pt_document_type = False

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
    # ATCUD - QR CODE
    ####################################

    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return []
        return ['date_done', 'l10n_pt_hashed_on', 'name']

    @api.model
    def _find_last_picking(self, company_id, picking_type):
        return self.sudo().search([
            ('company_id', '=', company_id),
            ('picking_type_id', '=', picking_type.id),
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
                picking.l10n_pt_stock_inalterable_hash_short = hash_str[0] + hash_str[10] + hash_str[20] + hash_str[30]
            else:
                picking.l10n_pt_stock_inalterable_hash_version = False
                picking.l10n_pt_stock_inalterable_hash_short = False

    def _l10n_pt_stock_compute_missing_hashes(self, company_id=None):
        """
        Compute the hash/atcud for all records that do not have one yet
        (because they were not printed/previewed yet)
        """
        company_id = company_id or self.company_id.id

        # We get the existing AT series for movement series and without a picking type associated.
        at_series_without_picking_type = self.env['l10n_pt.at.series'].search([
            ('type', 'in', ['outgoing_gt', 'internal_ga', 'incoming_gd']),
            ('picking_type_id', '=', False)
        ])
        codes = {AT_SERIES_TYPE_MOVEMENT_TYPE_MAP[at_series.type] for at_series in at_series_without_picking_type}
        picking_types = self.env['stock.picking.type'].search([
            ('company_id', '=', company_id),
            ('code', 'in', tuple(codes)),
        ])
        # Picking types that match an existing AT series type but have not yet been associated to an AT Series should be flagged
        if picking_types_without_at_series := picking_types.filtered(lambda pt: not pt.l10n_pt_stock_at_series_id):
            raise RedirectWarning(
                _('You have to set an Official Series for these Operation Types: %s', ', '.join(picking_types_without_at_series.mapped('name'))),
                {
                    'type': 'ir.actions.act_window',
                    'name': _('Incorrect picking types'),
                    'res_model': 'stock.picking.type',
                    'view_mode': 'tree',
                    'views': [[False, 'list'], [False, 'form']],
                    'domain': [('id', 'in', picking_types_without_at_series.ids)],
                },
                _("Show incorrect picking types")
            )

        # Get all picking types with an AT series to find pickings of that type
        picking_types_with_at_series = self.env['stock.picking.type'].search([
            ('company_id', '=', company_id),
            ('l10n_pt_stock_at_series_id', '!=', False),
        ])
        for picking_type in picking_types_with_at_series:
            pickings = self.sudo().search([
                ('company_id', '=', company_id),
                ('picking_type_id', '=', picking_type.id),
                ('state', '=', 'done'),
                ('l10n_pt_stock_inalterable_hash', '=', False),
            ], order='date_done')

            previous_picking = self._find_last_picking(company_id, picking_type)
            try:
                previous_hash = previous_picking.l10n_pt_stock_inalterable_hash.split("$")[2] if previous_picking.l10n_pt_stock_inalterable_hash else ""
            except IndexError:  # hash is not correctly formatted (it has been altered!)
                previous_hash = "invalid_hash"  # will never be a valid hash
            current_atcud_number = int(previous_picking.l10n_pt_stock_atcud.split("-")[-1]) + 1 if previous_picking.l10n_pt_stock_atcud else 1
            for picking in pickings:
                picking.name = f"{picking.picking_type_id.l10n_pt_stock_at_series_id.prefix}/{str(current_atcud_number).zfill(5)}"
                picking.l10n_pt_stock_atcud = f"{picking.l10n_pt_at_series_id._get_at_code()}-{current_atcud_number}"
                picking.l10n_pt_stock_document_type_code = SAFT_PT_MOVEMENT_TYPE_MAP[picking.l10n_pt_at_series_id.type]
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

    ####################################
    # QR CODE
    ####################################

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
            qr_code_dict['D:'] = f"{picking.l10n_pt_stock_document_type_code}*"
            qr_code_dict['G:'] = f"{picking._get_l10n_pt_stock_document_number()}*"
            qr_code_dict['H:'] = f"{picking.l10n_pt_stock_atcud}*"
            qr_code_dict['N:'] = "0.00*"
            qr_code_dict['O:'] = "0.00*"
            qr_code_dict['Q:'] = f"{picking.l10n_pt_stock_inalterable_hash_short}*"
            qr_code_str = ''.join(f"{key}{value}" for key, value in sorted(qr_code_dict.items()))
            picking.l10n_pt_stock_qr_code_str = qr_code_str
