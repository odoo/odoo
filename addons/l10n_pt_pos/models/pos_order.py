import re
import urllib.parse
import stdnum.pt.nif

from odoo.addons.l10n_pt_account.utils.hashing import L10nPtHashingUtils
from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.tools import float_repr, format_date


class PosOrder(models.Model):
    _inherit = "pos.order"

    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])
    l10n_pt_pos_inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    l10n_pt_pos_qr_code_str = fields.Char(string='Portuguese QR Code', compute='_compute_l10n_pt_pos_qr_code_str', store=True)
    l10n_pt_pos_inalterable_hash_short = fields.Char(string='Short version of the Portuguese hash', compute='_compute_l10n_pt_pos_inalterable_hash_info')
    l10n_pt_pos_inalterable_hash_version = fields.Integer(string='Portuguese hash version', compute='_compute_l10n_pt_pos_inalterable_hash_info')
    l10n_pt_pos_atcud = fields.Char(string='Portuguese ATCUD', compute='_compute_l10n_pt_pos_atcud', store=True)

    # -------------------------------------------------------------------------
    # HASH
    # -------------------------------------------------------------------------
    @api.depends('l10n_pt_pos_inalterable_hash')
    def _compute_l10n_pt_pos_inalterable_hash_info(self):
        for order in self:
            if order.l10n_pt_pos_inalterable_hash:
                hash_version, hash_str = order.l10n_pt_pos_inalterable_hash.split("$")[1:]
                order.l10n_pt_pos_inalterable_hash_version = int(hash_version)
                order.l10n_pt_pos_inalterable_hash_short = hash_str[0] + hash_str[10] + hash_str[20] + hash_str[30]
            else:
                order.l10n_pt_stock_inalterable_hash_version = False
                order.l10n_pt_pos_inalterable_hash_short = False

    @api.depends('name', 'config_id.l10n_pt_pos_official_series_id.code', 'l10n_pt_pos_inalterable_hash')
    def _compute_l10n_pt_pos_atcud(self):
        for order in self:
            if (
                order.company_id.country_id.code == 'PT'
                and order.config_id.l10n_pt_pos_official_series_id
                and order.l10n_pt_pos_inalterable_hash
                and not order.l10n_pt_pos_atcud
            ):
                order.l10n_pt_pos_atcud = f"{order.config_id.l10n_pt_pos_official_series_id.code}-{order._get_l10n_pt_pos_sequence_info()[1]}"
            else:
                order.l10n_pt_pos_atcud = False

    @api.depends('l10n_pt_pos_atcud')
    def _compute_l10n_pt_pos_qr_code_str(self):
        """ Generate the informational QR code for Portugal invoicing.
        E.g.: A:509445535*B:123456823*C:BE*D:FT*E:N*F:20220103*G:FT 01P2022/1*H:0*I1:PT*I7:325.20*I8:74.80*N:74.80*O:400.00*P:0.00*Q:P0FE*R:2230
        """

        def format_amount(pos_order, amount):
            """
            Convert amount to EUR based on the rate of a given account_move's date
            Format amount to 2 decimals as per SAF-T (PT) requirements
            """
            amount_eur = pos_order.currency_id._convert(amount, self.env.ref('base.EUR'), pos_order.company_id, pos_order.date_order)
            return float_repr(amount_eur, 2)

        def get_details_by_tax_category(pos_order):
            """Returns the base and value tax for each PT tax category (Normal, Intermediate, Reduced, Exempt)"""
            res = {}
            for line in pos_order.lines:
                for tax in line.tax_ids:
                    tax = order.fiscal_position_id.map_tax(tax)
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    tax_details = tax.compute_all(price, line.order_id.currency_id, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)['taxes']
                    if tax.tax_group_id.l10n_pt_account_tax_category not in res:
                        res[tax.tax_group_id.l10n_pt_account_tax_category] = {
                            'base': 0,
                            'vat': 0,
                        }
                    res[tax.tax_group_id.l10n_pt_account_tax_category]['base'] += sum(tax.get('base', 0.0) for tax in tax_details)
                    res[tax.tax_group_id.l10n_pt_account_tax_category]['vat'] += sum(tax.get('amount', 0.0) for tax in tax_details)
            return res

        for order in self.filtered(lambda o: (
            o.company_id.country_id.code == "PT"
            and not o.l10n_pt_pos_qr_code_str  # Skip if already computed
        )):
            if not order.l10n_pt_pos_inalterable_hash:
                continue
            company_vat_ok = order.company_id.vat and stdnum.pt.nif.is_valid(order.company_id.vat)
            hash_ok = order.l10n_pt_pos_inalterable_hash
            atcud_ok = order.l10n_pt_pos_atcud

            if not company_vat_ok or not hash_ok or not atcud_ok:
                error_msg = _("Some fields required for the generation of the document are missing or invalid. Please verify them:\n")
                error_msg += _('- The `VAT` of your company should be defined and match the following format: PT123456789\n') if not company_vat_ok else ""
                error_msg += _("- The `ATCUD` is not defined. Please verify the journal's official series") if not atcud_ok else ""
                error_msg += _("- The `hash` is not defined. You can contact the support.") if not hash_ok else ""
                raise UserError(error_msg)

            company_vat = re.sub(r'\D', '', order.company_id.vat)
            partner_vat = re.sub(r'\D', '', order.partner_id.vat or '999999990')
            details_by_tax_group = get_details_by_tax_category(order)
            tax_letter = 'I'
            if order.company_id.l10n_pt_account_region_code == 'PT-AC':
                tax_letter = 'J'
            elif order.company_id.l10n_pt_account_region_code == 'PT-MA':
                tax_letter = 'K'

            qr_code_str = ""
            qr_code_str += f"A:{company_vat}*"
            qr_code_str += f"B:{partner_vat}*"
            qr_code_str += f"C:{order.partner_id.country_id.code if order.partner_id and order.partner_id.country_id else 'Desconhecido'}*"
            qr_code_str += "D:FR*"
            qr_code_str += "E:N*"
            qr_code_str += f"F:{format_date(self.env, order.date_order, date_format='yyyyMMdd')}*"
            qr_code_str += f"G:{order._get_l10n_pt_pos_document_number()}*"
            qr_code_str += f"H:{order.l10n_pt_pos_atcud}*"
            qr_code_str += f"{tax_letter}1:{order.company_id.l10n_pt_account_region_code}*"
            if details_by_tax_group.get('E'):
                qr_code_str += f"{tax_letter}2:{details_by_tax_group.get('E')['base']}*"
            for i, tax_category in enumerate(('R', 'I', 'N')):
                if details_by_tax_group.get(tax_category):
                    qr_code_str += f"{tax_letter}{i * 2 + 3}:{details_by_tax_group.get(tax_category)['base']}*"
                    qr_code_str += f"{tax_letter}{i * 2 + 4}:{details_by_tax_group.get(tax_category)['vat']}*"
            qr_code_str += f"N:{format_amount(order, order.amount_tax)}*"
            qr_code_str += f"O:{format_amount(order, order.amount_total)}*"
            qr_code_str += f"Q:{order.l10n_pt_pos_inalterable_hash_short}*"
            qr_code_str += "R:0000"  # TODO: Fill with Certificate number provided by the Tax Authority
            order.l10n_pt_pos_qr_code_str = urllib.parse.quote_plus(qr_code_str)

    def _get_integrity_hash_fields(self):
        if self.company_id.country_id.code != 'PT':
            return []
        return ['date_order', 'create_date', 'amount_total', 'name']

    def _get_l10n_pt_pos_sequence_info(self):
        self.ensure_one()
        sequence_prefix = re.sub(r'[^A-Za-z0-9]+', '_', '_'.join(self.name.split('/')[:-1])).rstrip('_')
        sequence_number = self.name.split('/')[-1]
        return sequence_prefix, sequence_number

    def _get_l10n_pt_pos_document_number(self):
        self.ensure_one()
        sequence_prefix, sequence_number = self._get_l10n_pt_pos_sequence_info()
        return f"pos_order {sequence_prefix}/{sequence_number}"

    def _hash_compute(self, previous_hash=None):
        if self.company_id.country_id.code != 'PT' or not self._context.get('l10n_pt_force_compute_signature'):
            return {}
        endpoint = self.env['ir.config_parameter'].sudo().get_param('l10n_pt_account.iap_endpoint', L10nPtHashingUtils.L10N_PT_SIGN_DEFAULT_ENDPOINT)
        if endpoint == 'demo':
            return self._l10n_pt_pos_sign_records_using_demo_key(previous_hash)  # sign locally with the demo key provided by the government
        return self._l10n_pt_pos_sign_records_using_iap(previous_hash)  # sign the records using Odoo's IAP (or a custom endpoint)

    def _l10n_pt_pos_sign_records_using_iap(self, previous_hash):
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        docs_to_sign = [{
            'id': order.id,
            'date': order.date_order.isoformat(),
            'sorting_key': order.name,
            'system_entry_date': order.create_date.isoformat(timespec='seconds'),
            'l10n_pt_document_number': order._get_l10n_pt_pos_document_number(),
            'gross_total': float_repr(order.amount_total, 2),
            'previous_signature': previous_hash,
        } for order in self]
        return L10nPtHashingUtils._l10n_pt_sign_records_using_iap(self.env, docs_to_sign)

    def _l10n_pt_pos_get_message_to_hash(self, previous_hash):
        self.ensure_one()
        return L10nPtHashingUtils._l10n_pt_get_message_to_hash(self.date_order, self.create_date, self.amount_total, self._get_l10n_pt_pos_document_number(), previous_hash)

    def _l10n_pt_pos_get_last_record(self):
        self.ensure_one()
        return self.sudo().search([
            ('config_id', '=', self.config_id.id),
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('l10n_pt_pos_inalterable_hash', '!=', False),
        ], order="id DESC", limit=1)

    def _l10n_pt_pos_sign_records_using_demo_key(self, previous_hash):
        """
        Technical requirements from the Portuguese tax authority can be found at page 13 of the following document:
        https://info.portaldasfinancas.gov.pt/pt/docs/Portug_tax_system/Documents/Order_No_8632_2014_of_the_3rd_July.pdf
        """
        res = {}
        for order in self:
            if not previous_hash:
                previous = order._l10n_pt_pos_get_last_record()
                previous_hash = previous.l10n_pt_pos_inalterable_hash if previous else ""
            previous_hash = previous_hash.split("$")[2] if previous_hash else ""
            message = order._l10n_pt_pos_get_message_to_hash(previous_hash)
            res[order.id] = L10nPtHashingUtils._l10n_pt_sign_using_demo_key(self.env, message)
            previous_hash = res[order.id]
        return res

    def _l10n_pt_pos_verify_integrity(self, previous_hash, public_key_str):
        """
        :return: True if the hash of the record is valid, False otherwise
        """
        self.ensure_one()
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        message = self._l10n_pt_pos_get_message_to_hash(previous_hash)
        return L10nPtHashingUtils._l10n_pt_verify_integrity(message, self.l10n_pt_pos_inalterable_hash, public_key_str)

    def l10n_pt_pos_compute_missing_hashes(self, company_id):
        """
        Compute the hash for all records that do not have one yet
        (because they were not printed/previewed yet)
        """
        orders = self.search([
            ('company_id', '=', company_id),
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('l10n_pt_pos_inalterable_hash', '=', False),
        ], order='id')
        if not orders:
            return ''
        orders_hashes = self.env['pos.order'].browse([o.id for o in orders]).with_context(l10n_pt_force_compute_signature=True)._hash_compute()
        for order_id, l10n_pt_pos_inalterable_hash in orders_hashes.items():
            super(PosOrder, self.env['pos.order'].browse(order_id)).write({'l10n_pt_pos_inalterable_hash': l10n_pt_pos_inalterable_hash})
        return {
            "hash": orders[-1].l10n_pt_pos_inalterable_hash,
            "qr_code_str": orders[-1].l10n_pt_pos_qr_code_str,
            "atcud": orders[-1].l10n_pt_pos_atcud,
        }


    def write(self, vals):
        if not vals:
            return True
        for order in self:
            violated_fields = set(vals).intersection(order._get_integrity_hash_fields() + ['l10n_pt_pos_inalterable_hash'])
            if (
                order.company_id.country_id.code == 'PT'
                and violated_fields
                and order.l10n_pt_pos_inalterable_hash
               ):
                raise UserError(_("You cannot edit the following fields: %s", ', '.join(violated_fields)))
        return super(PosOrder, self).write(vals)
