import re

from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.tools import float_repr, format_date

from odoo.addons.l10n_pt.const import PT_CERTIFICATION_NUMBER
from odoo.addons.l10n_pt.utils import hashing as pt_hash_utils


class PosOrder(models.Model):
    _inherit = "pos.order"

    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])
    l10n_pt_pos_inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    l10n_pt_pos_inalterable_hash_short = fields.Char(string='Short version of the Portuguese hash', compute='_compute_l10n_pt_pos_inalterable_hash_info')
    l10n_pt_pos_inalterable_hash_version = fields.Integer(string='Portuguese hash version', compute='_compute_l10n_pt_pos_inalterable_hash_info')
    l10n_pt_pos_atcud = fields.Char(string='Portuguese ATCUD', readonly=True, copy=False)
    l10n_pt_pos_qr_code_str = fields.Char(string='Portuguese QR Code', compute='_compute_l10n_pt_pos_qr_code_str')
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True)

    ####################################
    # GENERAL
    ####################################

    def _get_l10n_pt_pos_document_number(self):
        self.ensure_one()
        return f"pos_order {self.name}"

    ####################################
    # HASH
    ####################################
    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return []
        return ['date_order', 'l10n_pt_hashed_on', 'amount_total', 'name']

    @api.model
    def _find_last_order(self, company_id, pos_config_id):
        return self.sudo().search([
            ('company_id', '=', company_id),
            ('config_id', '=', pos_config_id),
            ('l10n_pt_pos_inalterable_hash', '!=', False),
        ], order='date_order desc', limit=1)

    def _calculate_hashes(self, previous_hash=None):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return {}
        self.l10n_pt_hashed_on = fields.Datetime.now()
        docs_to_sign = [{
            'id': order.id,
            'date': order.date_order.strftime('%Y-%m-%d'),
            'sorting_key': order.date_order.isoformat(),
            'system_entry_date': order.l10n_pt_hashed_on.isoformat(timespec='seconds'),
            'name': order._get_l10n_pt_pos_document_number(),
            'gross_total': float_repr(order.amount_total, 2),
            'previous_signature': previous_hash,
        } for order in self]
        return pt_hash_utils.sign_records(self.env, docs_to_sign)

    @api.depends('l10n_pt_pos_inalterable_hash')
    def _compute_l10n_pt_pos_inalterable_hash_info(self):
        for order in self:
            if order.l10n_pt_pos_inalterable_hash:
                hash_version, hash_str = order.l10n_pt_pos_inalterable_hash.split("$")[1:]
                order.l10n_pt_pos_inalterable_hash_version = int(hash_version)
                order.l10n_pt_pos_inalterable_hash_short = hash_str[0] + hash_str[10] + hash_str[20] + hash_str[30]
            else:
                order.l10n_pt_pos_inalterable_hash_version = False
                order.l10n_pt_pos_inalterable_hash_short = False

    def l10n_pt_pos_compute_missing_hashes(self, company_id, pos_config_id=None):
        """
        Compute the hash/atcud for all records that do not have one yet
        (because they were not printed/previewed yet)
        """
        if len(self) == 1 and self.l10n_pt_pos_inalterable_hash:
            last_order = self  # May happen if reprint of the same order
        else:
            pos_config_id = pos_config_id or self.config_id.id
            orders = self.sudo().search([
                ('company_id', '=', company_id),
                ('config_id', '=', pos_config_id),
                ('state', 'in', ['paid', 'done', 'invoiced']),
                ('l10n_pt_pos_inalterable_hash', '=', False),
            ], order='date_order')

            previous_order = self._find_last_order(company_id, pos_config_id)
            try:
                previous_hash = previous_order.l10n_pt_pos_inalterable_hash.split("$")[2] if previous_order.l10n_pt_pos_inalterable_hash else ""
            except IndexError:  # hash is not correctly formatted (it has been altered!)
                previous_hash = "123"  # will never be a valid hash
            current_atcud_number = int(previous_order.l10n_pt_pos_atcud.split("-")[-1]) + 1 if previous_order.l10n_pt_pos_atcud else 1
            for order in orders:
                order.name = f"{order.config_id.l10n_pt_pos_at_series_id.prefix}/{str(current_atcud_number).zfill(5)}"
                order.l10n_pt_pos_atcud = f"{order.config_id.l10n_pt_pos_at_series_id._get_at_code()}-{current_atcud_number}"
                current_atcud_number += 1

            orders_hashes = orders._calculate_hashes(previous_hash)
            for order_id, l10n_pt_pos_inalterable_hash in orders_hashes.items():
                order = self.browse(order_id)
                order.l10n_pt_pos_inalterable_hash = l10n_pt_pos_inalterable_hash
            last_order = orders[-1:]
        return {
            "name": last_order.name,
            "hash": last_order.l10n_pt_pos_inalterable_hash,
            "hash_short": last_order.l10n_pt_pos_inalterable_hash_short,
            "atcud": last_order.l10n_pt_pos_atcud,
            "qr_code_str": last_order.l10n_pt_pos_qr_code_str,
        }  # Send the last one that is being printed to the POS frontend

    ####################################
    # QR CODE
    ####################################
    @api.depends('l10n_pt_pos_atcud')
    def _compute_l10n_pt_pos_qr_code_str(self):
        """ Generate the informational QR code for Portugal invoicing.
        E.g.: A:509445535*B:123456823*C:BE*D:FT*E:N*F:20220103*G:FT 01P2022/1*H:0*I1:PT*I7:325.20*I8:74.80*N:74.80*O:400.00*P:0.00*Q:P0FE*R:2230
        """
        EUR = self.env.ref('base.EUR')

        def format_amount(pos_order, amount):
            """
            Convert amount to EUR based on the rate of a given account_move's date
            Format amount to 2 decimals as per SAF-T (PT) requirements
            """
            amount_eur = pos_order.currency_id._convert(amount, EUR, pos_order.company_id, pos_order.date_order)
            return float_repr(amount_eur, 2)

        def get_details_by_tax_category(pos_order):
            """Returns the base and value tax for each PT tax category (Normal, Intermediate, Reduced, Exempt)"""
            res = {}
            for line in pos_order.lines:
                for tax in line.tax_ids:
                    tax = order.fiscal_position_id.map_tax(tax)
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    tax_details = tax.compute_all(price, line.order_id.currency_id, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)['taxes']
                    if tax.tax_group_id.l10n_pt_tax_category not in res:
                        res[tax.tax_group_id.l10n_pt_tax_category] = {
                            'base': 0,
                            'vat': 0,
                        }
                    res[tax.tax_group_id.l10n_pt_tax_category]['base'] += sum(tax.get('base', 0.0) for tax in tax_details)
                    res[tax.tax_group_id.l10n_pt_tax_category]['vat'] += sum(tax.get('amount', 0.0) for tax in tax_details)
            return res

        for order in self.filtered(lambda o: (
            not o.l10n_pt_pos_qr_code_str  # Skip if already computed
        )):
            if order.company_id.account_fiscal_country_id.code != "PT" or not order.l10n_pt_pos_inalterable_hash:
                order.l10n_pt_pos_qr_code_str = False
                continue

            pt_hash_utils.verify_prerequisites_qr_code(order, order.l10n_pt_pos_inalterable_hash, order.l10n_pt_pos_atcud)

            company_vat = re.sub(r'\D', '', order.company_id.vat)
            partner_vat = re.sub(r'\D', '', order.partner_id.vat or '999999990')
            details_by_tax_group = get_details_by_tax_category(order)
            tax_letter = 'I'
            if order.company_id.l10n_pt_region_code == 'PT-AC':
                tax_letter = 'J'
            elif order.company_id.l10n_pt_region_code == 'PT-MA':
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
            qr_code_str += f"{tax_letter}1:{order.company_id.l10n_pt_region_code}*"
            if details_by_tax_group.get('E'):
                qr_code_str += f"{tax_letter}2:{details_by_tax_group.get('E')['base']}*"
            for i, tax_category in enumerate(('R', 'I', 'N')):
                if details_by_tax_group.get(tax_category):
                    qr_code_str += f"{tax_letter}{i * 2 + 3}:{details_by_tax_group.get(tax_category)['base']}*"
                    qr_code_str += f"{tax_letter}{i * 2 + 4}:{details_by_tax_group.get(tax_category)['vat']}*"
            qr_code_str += f"N:{format_amount(order, order.amount_tax)}*"
            qr_code_str += f"O:{format_amount(order, order.amount_total)}*"
            qr_code_str += f"Q:{order.l10n_pt_pos_inalterable_hash_short}*"
            qr_code_str += f"R:{PT_CERTIFICATION_NUMBER}"
            order.l10n_pt_pos_qr_code_str = qr_code_str

    ####################################
    # OVERRIDES
    ####################################

    def write(self, vals):
        if not vals:
            return True
        for order in self:
            violated_fields = set(vals).intersection(order._get_integrity_hash_fields() + ['l10n_pt_pos_inalterable_hash'])
            if (
                order.company_id.account_fiscal_country_id.code == 'PT'
                and violated_fields
                and order.l10n_pt_pos_inalterable_hash
            ):
                raise UserError(_(
                    "This document is protected by a hash. "
                    "Therefore, you cannot edit the following fields: %s.",
                    ', '.join(f['string'] for f in order.fields_get(violated_fields).values())
                ))
        return super().write(vals)
