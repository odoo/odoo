from markupsafe import Markup
import urllib.parse

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_repr

from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils


class PosOrder(models.Model):
    _inherit = "pos.order"

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')
    l10n_pt_pos_qr_code_str = fields.Char(string="Portuguese QR Code", compute='_compute_l10n_pt_pos_qr_code_str')
    l10n_pt_pos_inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    l10n_pt_inalterable_hash_short = fields.Char(
        string="Short version of the Portuguese hash",
        compute='_compute_l10n_pt_pos_inalterable_hash_info',
    )
    l10n_pt_pos_inalterable_hash_version = fields.Integer(
        string="Portuguese hash version",
        compute='_compute_l10n_pt_pos_inalterable_hash_info',
    )
    l10n_pt_pos_atcud = fields.Char(string="Portuguese ATCUD", readonly=True, copy=False)
    l10n_pt_document_number = fields.Char(
        string="Unique Document Number",
        compute='_compute_l10n_pt_document_number', store=True,
        help="Unique identifier made up of the internal document type code, the series name, and the number of the "
             "document within the series.",
    )
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True)
    l10n_pt_at_series_id = fields.Many2one(
        'l10n_pt.at.series',
        related='config_id.l10n_pt_pos_at_series_id',
        string="AT Series",
    )
    l10n_pt_is_reprint = fields.Boolean(readonly=True)

    ####################################
    # OVERRIDES
    ####################################

    def write(self, vals):
        if not vals:
            return True
        for order in self:
            violated_fields = set(vals).intersection(order._get_integrity_hash_fields() + ['l10n_pt_pos_inalterable_hash'])
            if (
                order.country_code == 'PT'
                and violated_fields
                and order.l10n_pt_pos_inalterable_hash
            ):
                raise UserError(_(
                    "This document is protected by a hash. "
                    "Therefore, you cannot edit the following fields: %s.",
                    ', '.join(f['string'] for f in order.fields_get(violated_fields).values())
                ))
        return super().write(vals)

    def _generate_pos_order_invoice(self):
        """
        Set generate_pdf to False in order to avoid generating two versions of the invoice, due to extension of
        `_get_invoice_legal_documents` in l10n_pt_certification.account_move.
        """
        if self.country_code == 'PT':
            return super(PosOrder, self.with_context(generate_pdf=False))._generate_pos_order_invoice()
        return super()._generate_pos_order_invoice()

    ####################################
    # PT REQUIREMENTS
    ####################################

    def _l10n_pt_pos_get_vat_exemptions_reasons(self):
        # Get list of exemption reasons present in the order
        self.ensure_one()
        taxes_with_exemption = self.line_ids.tax_ids.filtered(lambda tax: tax.l10n_pt_tax_exemption_reason)
        return sorted(set(taxes_with_exemption.mapped(
            lambda tax: dict(tax._fields['l10n_pt_tax_exemption_reason'].selection).get(tax.l10n_pt_tax_exemption_reason)
        )))

    @api.depends('country_code', 'config_id.l10n_pt_pos_at_series_line_id')
    def _compute_l10n_pt_document_number(self):
        for order in self:
            if (
                order.country_code == 'PT'
                and order.config_id.l10n_pt_pos_at_series_line_id
                and not order.l10n_pt_document_number
            ):
                order.l10n_pt_document_number = order.config_id.l10n_pt_pos_at_series_line_id._l10n_pt_get_document_number_sequence().next_by_id()
            else:
                order.l10n_pt_document_number = False

    def update_l10n_pt_print_version(self):
        self.ensure_one()
        self.l10n_pt_is_reprint = True

    def post_reprint_reason(self, reason):
        self.ensure_one()
        msg = Markup(_("Reason for reprinting document %(name)s:<br/>%(reason)s", name=self.name, reason=reason))
        self.message_post(body=msg)
        return True

    ####################################
    # HASH AND QR CODE
    ####################################

    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return []
        return ['date_order', 'l10n_pt_hashed_on', 'amount_total', 'name', 'l10n_pt_document_number']

    def _calculate_hashes(self, previous_hash=None):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return {}
        self.l10n_pt_hashed_on = fields.Datetime.now()
        docs_to_sign = [{
            'id': order.id,
            'date': order.date_order.strftime('%Y-%m-%d'),
            'sorting_key': order.date_order.isoformat(),
            'system_entry_date': order.l10n_pt_hashed_on.isoformat(timespec='seconds'),
            'name': order.l10n_pt_document_number,
            'gross_total': float_repr(order.amount_total, 2),
            'previous_signature': previous_hash,
        } for order in self]
        return pt_hash_utils.sign_records(self.env, docs_to_sign, 'pos.order')

    @api.depends('l10n_pt_pos_inalterable_hash')
    def _compute_l10n_pt_pos_inalterable_hash_info(self):
        for order in self:
            if order.l10n_pt_pos_inalterable_hash:
                hash_version, hash_str = order.l10n_pt_pos_inalterable_hash.split("$")[1:]
                order.l10n_pt_pos_inalterable_hash_version = int(hash_version)
                order.l10n_pt_inalterable_hash_short = hash_str[0] + hash_str[10] + hash_str[20] + hash_str[30]
            else:
                order.l10n_pt_pos_inalterable_hash_version = False
                order.l10n_pt_inalterable_hash_short = False

    @api.model
    def _find_last_order(self, at_series):
        return self.sudo().search([
            ('l10n_pt_at_series_id', '=', at_series.at_series_id.id),
            ('l10n_pt_pos_inalterable_hash', '!=', False),
        ], order='date_order desc', limit=1)

    def l10n_pt_pos_compute_missing_hashes(self, pos_config_id=None, at_series_line=None):
        """
        Compute the hash/atcud for all records that do not have one yet
        (because they were not printed/previewed yet)
        """
        if pos_config_id:
            at_series_line = self.env['l10n_pt.at.series.line'].search([
                ('at_series_id', '=', self.env['pos.config'].browse(pos_config_id).l10n_pt_pos_at_series_id.id),
                ('type', '=', 'pos_order'),
            ])
        if not at_series_line:
            raise UserError(_("No AT Series of type 'Invoice/Receipt (FR)' was found for this POS Configuration."))
        orders = self.sudo().search([
            ('l10n_pt_at_series_id', '=', at_series_line.at_series_id.id),
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('l10n_pt_pos_inalterable_hash', '=', False),
        ], order='date_order')

        previous_order = self._find_last_order(at_series_line)
        try:
            previous_hash = previous_order.l10n_pt_pos_inalterable_hash.split("$")[2] if previous_order.l10n_pt_pos_inalterable_hash else ""
        except IndexError:  # hash is not correctly formatted (it has been altered!)
            previous_hash = "123"  # will never be a valid hash
        for order in orders.sorted(key=lambda pos_order: (pos_order.write_date, pos_order.name)):
            current_atcud_number = int(order.l10n_pt_document_number.split('/')[-1])
            order.l10n_pt_pos_atcud = f"{order.config_id.l10n_pt_pos_at_series_line_id._get_at_code()}-{current_atcud_number}"

        orders_hashes = orders._calculate_hashes(previous_hash)
        for order, l10n_pt_pos_inalterable_hash in orders_hashes.items():
            order.l10n_pt_pos_inalterable_hash = l10n_pt_pos_inalterable_hash

    def l10n_pt_get_order_vals(self):
        self.ensure_one()
        return {
            'name': self.name,
            'hash': self.l10n_pt_pos_inalterable_hash,
            'hash_short': self.l10n_pt_inalterable_hash_short,
            'atcud': self.l10n_pt_pos_atcud,
            'document_identifier': self.l10n_pt_document_number,
            'qr_code_str': self.l10n_pt_pos_qr_code_str,
            'is_reprint': self.l10n_pt_is_reprint,
            'document_type': _("Invoice/Receipt"),
        }

    def l10n_pt_verify_prerequisites_qr_code(self):
        self.ensure_one()
        if self.country_code == 'PT':
            return pt_hash_utils.verify_prerequisites_qr_code(self, self.l10n_pt_pos_inalterable_hash, self.l10n_pt_pos_atcud)

    @api.depends('l10n_pt_pos_atcud', 'l10n_pt_pos_inalterable_hash')
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
                    tax = pos_order.fiscal_position_id.map_tax(tax)
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
            if order.country_code != "PT" or not order.l10n_pt_pos_inalterable_hash:
                order.l10n_pt_pos_qr_code_str = False
                continue

            details_by_tax_group = get_details_by_tax_category(order)

            order.l10n_pt_verify_prerequisites_qr_code()
            # qr_code_dict contains most of the values needed for the qr code string
            qr_code_dict, tax_letter = pt_hash_utils.l10n_pt_common_qr_code_str(order, self.env, order.date_order)
            qr_code_dict['D:'] = "FR*"
            qr_code_dict['H:'] = f"{order.l10n_pt_pos_atcud}*"
            if details_by_tax_group.get('E'):
                qr_code_dict[f'{tax_letter}2:'] = f"{details_by_tax_group.get('E')['base']}*"
            for i, tax_category in enumerate(('R', 'I', 'N')):
                if details_by_tax_group.get(tax_category):
                    qr_code_dict[f'{tax_letter}{i * 2 + 3}:'] = f"{details_by_tax_group.get(tax_category)['base']}*"
                    qr_code_dict[f'{tax_letter}{i * 2 + 4}:'] = f"{details_by_tax_group.get(tax_category)['vat']}*"
            qr_code_dict['N:'] = f"{format_amount(order, order.amount_tax)}*"
            qr_code_dict['O:'] = f"{format_amount(order, order.amount_total)}*"
            qr_code_dict['Q:'] = f"{order.l10n_pt_inalterable_hash_short}*"
            qr_code_str = ''.join(f"{key}{value}" for key, value in sorted(qr_code_dict.items()))
            order.l10n_pt_pos_qr_code_str = urllib.parse.quote_plus(qr_code_str)
