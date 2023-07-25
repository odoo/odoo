import re
import urllib.parse
import stdnum.pt.nif
from odoo.addons.l10n_pt_account.utils.hashing import L10nPtHashingUtils
from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.tools import format_date


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])

    l10n_pt_stock_secure_sequence_id = fields.Many2one(
        'ir.sequence',
        help='Sequence to use to ensure the securisation of data',
        readonly=True, copy=False
    )
    l10n_pt_stock_tax_authority_series_id = fields.Many2one("l10n_pt_account.tax.authority.series", string="Official Series of the Tax Authority")

    def write(self, vals):
        for picking_type in self.filtered(lambda pt: pt.company_id.country_id.code == 'PT'):
            if vals.get('l10n_pt_stock_tax_authority_series_id') and picking_type.l10n_pt_stock_tax_authority_series_id:
                if self.env['stock.picking'].search_count([('picking_type_id', '=', picking_type.id)]):
                    raise UserError(_("You cannot change the official series of a journal once it has been used."))
        return super().write(vals)

    def _create_l10n_pt_stock_secure_sequence(self):
        for picking_type in self.filtered(lambda pt: pt.company_id.country_id.code == 'PT' and not pt.l10n_pt_stock_secure_sequence_id):
            picking_type.l10n_pt_stock_secure_sequence_id = self.env['ir.sequence'].create({
                'name': _('Securisation of %s', picking_type.name),
                'code': 'SECURE-' + picking_type.code,
                'implementation': 'no_gap',
                'prefix': '',
                'suffix': '',
                'padding': 0,
                'company_id': picking_type.company_id.id,
            })


class StockPicking(models.Model):
    _inherit = "stock.picking"

    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])
    l10n_pt_secure_sequence_number = fields.Integer(string='Inalterable no-gap sequence number', copy=False)
    l10n_pt_stock_inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    l10n_pt_stock_qr_code_str = fields.Char(string='Portuguese QR Code', compute='_compute_l10n_pt_stock_qr_code_str', store=True)
    l10n_pt_stock_inalterable_hash_short = fields.Char(string='Short version of the Portuguese hash', compute='_compute_l10n_pt_stock_inalterable_hash_info')
    l10n_pt_stock_inalterable_hash_version = fields.Integer(string='Portuguese hash version', compute='_compute_l10n_pt_stock_inalterable_hash_info')
    l10n_pt_stock_atcud = fields.Char(string='Portuguese ATCUD', compute='_compute_l10n_pt_stock_atcud', store=True)

    # -------------------------------------------------------------------------
    # HASH
    # -------------------------------------------------------------------------
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

    @api.depends('name', 'picking_type_id.l10n_pt_stock_tax_authority_series_id.code', 'l10n_pt_stock_inalterable_hash')
    def _compute_l10n_pt_stock_atcud(self):
        for picking in self:
            if (
                picking.company_id.country_id.code == 'PT'
                and picking.picking_type_id.l10n_pt_stock_tax_authority_series_id
                and picking.l10n_pt_stock_inalterable_hash
                and not picking.l10n_pt_stock_atcud
            ):
                picking.l10n_pt_stock_atcud = f"{picking.picking_type_id.l10n_pt_stock_tax_authority_series_id.code}-{picking._get_l10n_pt_stock_sequence_info()[1]}"
            else:
                picking.l10n_pt_stock_atcud = False

    @api.depends('l10n_pt_stock_atcud')
    def _compute_l10n_pt_stock_qr_code_str(self):
        """ Generate the informational QR code for Portugal
        E.g.: A:509445535*B:123456823*C:BE*D:FT*E:N*F:20220103*G:FT 01P2022/1*H:0*I1:PT*I7:325.20*I8:74.80*N:74.80*O:400.00*P:0.00*Q:P0FE*R:2230
        """
        for picking in self.filtered(lambda o: (
            o.company_id.country_id.code == "PT"
            and not o.l10n_pt_stock_qr_code_str  # Skip if already computed
        )):
            if not picking.l10n_pt_stock_inalterable_hash:
                continue
            company_vat_ok = picking.company_id.vat and stdnum.pt.nif.is_valid(picking.company_id.vat)
            hash_ok = picking.l10n_pt_stock_inalterable_hash
            atcud_ok = picking.l10n_pt_stock_atcud

            if not company_vat_ok or not hash_ok or not atcud_ok:
                error_msg = _("Some fields required for the generation of the document are missing or invalid. Please verify them:\n")
                error_msg += _('- The `VAT` of your company should be defined and match the following format: PT123456789\n') if not company_vat_ok else ""
                error_msg += _("- The `ATCUD` is not defined. Please verify the journal's tax authority series") if not atcud_ok else ""
                error_msg += _("- The `hash` is not defined. You can contact the support.") if not hash_ok else ""
                raise UserError(error_msg)

            company_vat = re.sub(r'\D', '', picking.company_id.vat)
            partner_vat = re.sub(r'\D', '', picking.partner_id.vat or '999999990')
            tax_letter = 'I'
            if picking.company_id.l10n_pt_account_region_code == 'PT-AC':
                tax_letter = 'J'
            elif picking.company_id.l10n_pt_account_region_code == 'PT-MA':
                tax_letter = 'K'

            qr_code_str = ""
            qr_code_str += f"A:{company_vat}*"
            qr_code_str += f"B:{partner_vat}*"
            qr_code_str += f"C:{picking.partner_id.country_id.code if picking.partner_id and picking.partner_id.country_id else 'Desconhecido'}*"
            qr_code_str += "D:FR*"
            qr_code_str += "E:N*"
            qr_code_str += f"F:{format_date(self.env, picking.date, date_format='yyyyMMdd')}*"
            qr_code_str += f"G:{picking._get_l10n_pt_stock_document_number()}*"
            qr_code_str += f"H:{picking.l10n_pt_stock_atcud}*"
            qr_code_str += f"{tax_letter}1:{picking.company_id.l10n_pt_account_region_code}*"
            qr_code_str += f"N:0.00*"
            qr_code_str += f"O:0.00"
            qr_code_str += f"Q:{picking.l10n_pt_stock_inalterable_hash_short}*"
            qr_code_str += "R:0000"  # TODO: Fill with Certificate number provided by the Tax Authority
            picking.l10n_pt_stock_qr_code_str = urllib.parse.quote_plus(qr_code_str)

    def _get_integrity_hash_fields(self):
        if self.company_id.country_id.code != 'PT':
            return []
        return ['date', 'create_date', 'name']

    def _get_l10n_pt_stock_sequence_info(self):
        self.ensure_one()
        return self.picking_type_id.sequence_code, self.l10n_pt_secure_sequence_number

    def _get_l10n_pt_stock_document_number(self):
        self.ensure_one()
        sequence_prefix, sequence_number = self._get_l10n_pt_stock_sequence_info()
        return f"stock_picking {sequence_prefix}/{sequence_number}"

    def _hash_compute(self, previous_hash=None):
        if self.company_id.country_id.code != 'PT' or not self._context.get('l10n_pt_force_compute_signature'):
            return {}
        endpoint = self.env['ir.config_parameter'].sudo().get_param('l10n_pt_account.iap_endpoint', L10nPtHashingUtils.L10N_PT_SIGN_DEFAULT_ENDPOINT)
        if endpoint == 'demo':
            return self._l10n_pt_stock_sign_records_using_demo_key(previous_hash)  # sign locally with the demo key provided by the government
        return self._l10n_pt_stock_sign_records_using_iap(previous_hash)  # sign the records using Odoo's IAP (or a custom endpoint)

    def _l10n_pt_stock_sign_records_using_iap(self, previous_hash):
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        docs_to_sign = [{
            'id': picking.id,
            'sorting_key': picking.l10n_pt_secure_sequence_number,
            'date': picking.date.isoformat(),
            'system_entry_date': picking.create_date.isoformat(timespec='seconds'),
            'l10n_pt_document_number': picking._get_l10n_pt_stock_document_number(),
            'gross_total': '0.00',
            'previous_signature': previous_hash,
        } for picking in self]
        return L10nPtHashingUtils._l10n_pt_sign_records_using_iap(self.env, docs_to_sign)

    def _l10n_pt_stock_get_message_to_hash(self, previous_hash):
        self.ensure_one()
        return L10nPtHashingUtils._l10n_pt_get_message_to_hash(self.date, self.create_date, 0.0, self._get_l10n_pt_stock_document_number(), previous_hash)

    def _l10n_pt_stock_get_last_record(self):
        self.ensure_one()
        return self.sudo().search([
            ('picking_type_id', '=', self.picking_type_id.id),
            ('state', '=', 'done'),
            ('l10n_pt_stock_inalterable_hash', '!=', False),
        ], order="l10n_pt_secure_sequence_number DESC", limit=1)

    def _l10n_pt_stock_sign_records_using_demo_key(self, previous_hash):
        """
        Technical requirements from the Portuguese tax authority can be found at page 13 of the following document:
        https://info.portaldasfinancas.gov.pt/pt/docs/Portug_tax_system/Documents/Order_No_8632_2014_of_the_3rd_July.pdf
        """
        res = {}
        for picking in self:
            if not previous_hash:
                previous = picking._l10n_pt_stock_get_last_record()
                previous_hash = previous.l10n_pt_stock_inalterable_hash if previous else ""
            previous_hash = previous_hash.split("$")[2] if previous_hash else ""
            message = picking._l10n_pt_stock_get_message_to_hash(previous_hash)
            res[picking.id] = L10nPtHashingUtils._l10n_pt_sign_using_demo_key(self.env, message)
            previous_hash = res[picking.id]
        return res

    def _l10n_pt_stock_verify_integrity(self, previous_hash, public_key_str):
        """
        :return: True if the hash of the record is valid, False otherwise
        """
        self.ensure_one()
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        message = self._l10n_pt_stock_get_message_to_hash(previous_hash)
        return L10nPtHashingUtils._l10n_pt_verify_integrity(message, self.l10n_pt_stock_inalterable_hash, public_key_str)

    def l10n_pt_stock_compute_missing_hashes(self, company_id):
        """
        Compute the hash for all records that do not have one yet
        (because they were not printed/previewed yet)
        """
        pickings = self.search([
            ('company_id', '=', company_id),
            ('state', '=', 'done'),
            ('picking_type_id.code', '=', 'outgoing'),
            ('l10n_pt_stock_inalterable_hash', '=', False),
        ], order='l10n_pt_secure_sequence_number')
        pickings = pickings.filtered(lambda p: not hasattr(p, 'pos_order_id') or not p.pos_order_id) # POS orders are hashed in their own way (see l10n_pt_pos)
        if not pickings:
            return ''
        pickings_hashes = self.env['stock.picking'].browse([p.id for p in pickings]).with_context(l10n_pt_force_compute_signature=True)._hash_compute()
        for order_id, l10n_pt_stock_inalterable_hash in pickings_hashes.items():
            super(StockPicking, self.env['stock.picking'].browse(order_id)).write({'l10n_pt_stock_inalterable_hash': l10n_pt_stock_inalterable_hash})

    def button_validate(self):
        for picking in self.filtered(lambda p: p.company_id.country_id.code == 'PT' and not p.l10n_pt_secure_sequence_number):
            if not picking.company_id.country_id:
                raise UserError(_("You have to set a country in your company setting."))
            if picking.company_id.country_id.code == 'PT' and not picking.picking_type_id.l10n_pt_stock_tax_authority_series_id:
                raise UserError(_("You have to set a official Tax Authority Series in the Stock Picking Type."))
            picking.picking_type_id._create_l10n_pt_stock_secure_sequence()
            picking.l10n_pt_secure_sequence_number = picking.picking_type_id.l10n_pt_stock_secure_sequence_id.next_by_id()
        return super().button_validate()

    def write(self, vals):
        if not vals:
            return True
        for picking in self.filtered(lambda p: p.company_id.country_id.code == 'PT' and p.state == 'done'):
            violated_fields = set(vals).intersection(picking._get_integrity_hash_fields() + ['l10n_pt_stock_inalterable_hash', 'l10n_pt_secure_sequence_number'])
            if picking.l10n_pt_stock_inalterable_hash and violated_fields:
                raise UserError(_("You cannot edit the following fields: %s", ', '.join(violated_fields)))
        return super(StockPicking, self).write(vals)
