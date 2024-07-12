import re

from odoo import models, fields, _, api
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import float_repr, format_date

from odoo.addons.l10n_pt.const import PT_CERTIFICATION_NUMBER
from odoo.addons.l10n_pt.utils import hashing as pt_hash_utils


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', depends=['company_id.account_fiscal_country_id'])
    l10n_pt_stock_at_series_id = fields.Many2one("l10n_pt.at.series", string="Official Series of the Tax Authority")

    def write(self, vals):
        for picking_type in self:
            if "l10n_pt_stock_at_series_id" not in vals:
                continue
            if (
                picking_type.l10n_pt_stock_at_series_id
                and self.env['stock.picking'].search_count([
                    ('picking_type_id', '=', picking_type.id),
                    ('l10n_pt_stock_inalterable_hash', '!=', False),
                ], limit=1)
            ):
                raise UserError(_("You cannot change the AT series of a Picking Type once it has been used."))
            if picking_type.search_count([
                ('l10n_pt_stock_at_series_id', '=', vals['l10n_pt_stock_at_series_id']),
                ('id', '!=', picking_type.id),
            ], limit=1):
                raise UserError(_("You cannot use the same AT series for more than one Picking Type."))
        return super().write(vals)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', depends=['company_id.account_fiscal_country_id'])
    l10n_pt_stock_inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    l10n_pt_stock_inalterable_hash_short = fields.Char(string='Short version of the Portuguese hash', compute='_compute_l10n_pt_stock_inalterable_hash_info')
    l10n_pt_stock_inalterable_hash_version = fields.Integer(string='Portuguese hash version', compute='_compute_l10n_pt_stock_inalterable_hash_info')
    l10n_pt_stock_atcud = fields.Char(string='Portuguese ATCUD', readonly=True, copy=False)
    l10n_pt_stock_qr_code_str = fields.Char(string='Portuguese QR Code', compute='_compute_l10n_pt_stock_qr_code_str')
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True)

    ####################################
    # GENERAL
    ####################################

    def _get_l10n_pt_stock_document_number(self):
        self.ensure_one()
        return f"stock_picking {self.name}"

    def _get_l10n_pt_stock_gross_total(self):
        return 0

    ####################################
    # HASH & ATCUD
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
            return pt_hash_utils.sign_records(self.env, docs_to_sign)
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
        picking_types = self.env['stock.picking.type'].search([
            ('company_id', '=', company_id),
            ('code', '=', 'outgoing'),
        ])

        if picking_types_without_at_series := picking_types.filtered(lambda pt: not pt.l10n_pt_stock_at_series_id):
            raise RedirectWarning(
                _('You have to set an Official Series (of type Stock Picking) for these Operation Types: %s', ', '.join(picking_types_without_at_series.mapped('name'))),
                {
                    'type': 'ir.actions.act_window',
                    'name': 'Incorrect picking types',
                    'res_model': 'stock.picking.type',
                    'view_mode': 'tree',
                    'views': [[False, 'list'], [False, 'form']],
                    'domain': [('id', 'in', picking_types_without_at_series.ids)],
                },
                _("Show incorrect picking types")
            )

        for picking_type in picking_types:
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
                picking.l10n_pt_stock_atcud = f"{picking.picking_type_id.l10n_pt_stock_at_series_id._get_at_code()}-{current_atcud_number}"
                current_atcud_number += 1

            pickings_hashes = pickings._calculate_hashes(previous_hash)
            for picking_id, l10n_pt_stock_inalterable_hash in pickings_hashes.items():
                picking = self.browse(picking_id)
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
        E.g.: A:509445535*B:123456823*C:BE*D:FT*E:N*F:20220103*G:FT 01P2022/1*H:0*I1:PT*I7:325.20*I8:74.80*N:74.80*O:400.00*P:0.00*Q:P0FE*R:2230
        """
        for picking in self.filtered(lambda p: (
            not p.l10n_pt_stock_qr_code_str  # Skip if already computed
        )):
            if picking.company_id.account_fiscal_country_id.code != "PT" or not picking.l10n_pt_stock_inalterable_hash:
                picking.l10n_pt_stock_qr_code_str = False
                continue

            pt_hash_utils.verify_prerequisites_qr_code(picking, picking.l10n_pt_stock_inalterable_hash, picking.l10n_pt_stock_atcud)

            company_vat = re.sub(r'\D', '', picking.company_id.vat)
            partner_vat = re.sub(r'\D', '', picking.partner_id.vat or '999999990')
            tax_letter = 'I'
            if picking.company_id.l10n_pt_region_code == 'PT-AC':
                tax_letter = 'J'
            elif picking.company_id.l10n_pt_region_code == 'PT-MA':
                tax_letter = 'K'

            qr_code_str = ""
            qr_code_str += f"A:{company_vat}*"
            qr_code_str += f"B:{partner_vat}*"
            qr_code_str += f"C:{picking.partner_id.country_id.code if picking.partner_id and picking.partner_id.country_id else 'Desconhecido'}*"
            qr_code_str += "D:FR*"
            qr_code_str += "E:N*"
            qr_code_str += f"F:{format_date(self.env, picking.date_done, date_format='yyyyMMdd')}*"
            qr_code_str += f"G:{picking._get_l10n_pt_stock_document_number()}*"
            qr_code_str += f"H:{picking.l10n_pt_stock_atcud}*"
            qr_code_str += f"{tax_letter}1:{picking.company_id.l10n_pt_region_code}*"
            qr_code_str += "N:0.00*"
            qr_code_str += "O:0.00"
            qr_code_str += f"Q:{picking.l10n_pt_stock_inalterable_hash_short}*"
            qr_code_str += f"R:{PT_CERTIFICATION_NUMBER}"
            picking.l10n_pt_stock_qr_code_str = qr_code_str

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
