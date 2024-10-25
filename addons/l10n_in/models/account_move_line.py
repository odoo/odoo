import re
from datetime import date

from odoo import _, api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_in_hsn_code = fields.Char(string="HSN/SAC Code", compute="_compute_l10n_in_hsn_code", store=True, readonly=False, copy=False)
    l10n_in_gstr_section = fields.Selection(
        selection=[
            ("sale_b2b_rcm", "S B2B RCM"),
            ("sale_b2b_regular", "S B2B Regular"),
            ("sale_b2cl", "S B2CL"),
            ("sale_b2cs", "S B2CS"),
            ("sale_exp_wp", "S EXP(WP)"),
            ("sale_exp_wop", "S EXP(WOP)"),
            ("sale_sez_wp", "S SEZ(WP)"),
            ("sale_sez_wop", "S SEZ(WOP)"),
            ("sale_deemed_export", "S Deemed Export"),
            ("sale_cdnr_rcm", "S CDNR RCM"),
            ("sale_cdnr_regular", "S CDNR Regular"),
            ("sale_cdnr_deemed_export", "S CDNR(Deemed Export)"),
            ("sale_cdnr_sez_wp", "S CDNR(SEZ-WP)"),
            ("sale_cdnr_sez_wop", "S CDNR(SEZ-WOP)"),
            ("sale_cdnur_b2cl", "S CDNUR(B2CL)"),
            ("sale_cdnur_exp_wp", "S CDNUR(EXP-WP)"),
            ("sale_cdnur_exp_wop", "S CDNUR(EXP-WOP)"),
            ("sale_nil_rated", "S Nil Rated"),
            ("sale_out_of_scope", "S Out of Scope"),
            ],
        string="GSTR Section",
        index=True,
    )

    # withholding related fields
    l10n_in_withhold_tax_amount = fields.Monetary(string="TDS Tax Amount", compute='_compute_l10n_in_withhold_tax_amount')
    l10n_in_tds_tcs_section_id = fields.Many2one(related="account_id.l10n_in_tds_tcs_section_id")

    @api.depends('tax_ids')
    def _compute_l10n_in_withhold_tax_amount(self):
        # Compute the withhold tax amount for the withholding lines
        withholding_lines = self.filtered('move_id.l10n_in_is_withholding')
        (self - withholding_lines).l10n_in_withhold_tax_amount = False
        for line in withholding_lines:
            line.l10n_in_withhold_tax_amount = line.currency_id.round(abs(line.price_total - line.price_subtotal))

    @api.depends('product_id', 'product_id.l10n_in_hsn_code')
    def _compute_l10n_in_hsn_code(self):
        for line in self:
            if line.move_id.country_code == 'IN' and line.parent_state == 'draft':
                line.l10n_in_hsn_code = line.product_id.l10n_in_hsn_code

    def _l10n_in_check_invalid_hsn_code(self):
        self.ensure_one()
        hsn_code = self.env['account.move']._l10n_in_extract_digits(self.l10n_in_hsn_code)
        if not hsn_code:
            return _("HSN code is not set in product line %(name)s", name=self.name)
        elif not re.match(r'^\d{4}$|^\d{6}$|^\d{8}$', hsn_code):
            return _(
                "Invalid HSN Code (%(hsn_code)s) in product line %(product_line)s",
                hsn_code=hsn_code,
                product_line=self.product_id.name or self.name
            )
        return False

    def _get_l10n_in_tax_tag_ids(self):

        def get_tag_ids(*refs):
            return [self.env.ref(ref).id for ref in refs]

        return {
            'gst_rc': get_tag_ids(
                'l10n_in.tax_tag_base_sgst_rc', 'l10n_in.tax_tag_sgst_rc',
                'l10n_in.tax_tag_base_cgst_rc', 'l10n_in.tax_tag_cgst_rc',
                'l10n_in.tax_tag_base_igst_rc', 'l10n_in.tax_tag_igst_rc',
                'l10n_in.tax_tag_base_cess_rc', 'l10n_in.tax_tag_cess_rc',
            ),
            'gst': get_tag_ids(
                'l10n_in.tax_tag_base_sgst', 'l10n_in.tax_tag_sgst',
                'l10n_in.tax_tag_base_cgst', 'l10n_in.tax_tag_cgst',
                'l10n_in.tax_tag_base_igst', 'l10n_in.tax_tag_igst',
                'l10n_in.tax_tag_base_cess', 'l10n_in.tax_tag_cess',
            ),
            'nil': get_tag_ids(
                'l10n_in.tax_tag_exempt', 'l10n_in.tax_tag_nil_rated', 'l10n_in.tax_tag_non_gst_supplies',
            ),
            'export': get_tag_ids(
                'l10n_in.tax_tag_base_igst', 'l10n_in.tax_tag_igst',
                'l10n_in.tax_tag_base_cess', 'l10n_in.tax_tag_cess',
            ),
            'export_lut': get_tag_ids(
                'l10n_in.tax_tag_base_igst_lut', 'l10n_in.tax_tag_zero_rated',
            ),
        }

    def _set_l10n_in_gstr_section(self):

        def tags_have_categ(line_tax_tags, category):
            return any(tag in line_tax_tags for tag in tax_tags_dict[category])

        def is_invoice(move):
            return move.is_inbound() and not move.debit_origin_id

        def get_transaction_type(move):
            return 'intra_state' if move.l10n_in_state_id == move.company_id.state_id else 'inter_state'

        def get_section(line, tax_tags_dict):
            move = line.move_id
            gst_treatment = move.l10n_in_gst_treatment
            transaction_type = get_transaction_type(move)
            line_tags = line.tax_tag_ids.ids
            is_inv = is_invoice(move)
            amt_limit = 100000 if not line.invoice_date or line.invoice_date >= date(2024, 11, 1) else 250000

            # If no relevant tags are found, or the tags do not match any category, mark as out of scope
            if not line_tags or not any(tags_have_categ(line_tags, c) for c in tax_tags_dict):
                return 'sale_out_of_scope'

            # B2CS: Unregistered or Consumer sales with gst tags
            if gst_treatment in ('unregistered', 'consumer') and tags_have_categ(line_tags, 'gst'):
                if transaction_type == 'intra_state':
                    return 'sale_b2cs'
                if transaction_type == "inter_state" and (
                    is_inv
                    and move.amount_total <= amt_limit
                    or move.debit_origin_id and move.debit_origin_id.amount_total <= amt_limit
                    or move.reversed_entry_id and move.reversed_entry_id.amount_total <= amt_limit
                ):
                    return 'sale_b2cs'

            # Nil rated sales
            if gst_treatment != 'overseas' and tags_have_categ(line_tags, 'nil'):
                return 'sale_nil_rated'

            # If it's a standard invoice (not a debit/credit note)
            if is_inv:
                # B2B with Reverse Charge and Regular
                if gst_treatment in ('regular', 'composition', 'uin_holders'):
                    if tags_have_categ(line_tags, 'gst_rc'):
                        return 'sale_b2b_rcm'
                    elif tags_have_categ(line_tags, 'gst'):
                        return 'sale_b2b_regular'
                # B2CL: Unregistered interstate sales above threshold
                if (
                    gst_treatment in ('unregistered', 'consumer')
                    and tags_have_categ(line_tags, 'gst')
                    and transaction_type == 'inter_state'
                    and move.amount_total > amt_limit
                ):
                    return 'sale_b2cl'
                # Export with payment and without payment (under LUT) of tax
                if gst_treatment == 'overseas':
                    if tags_have_categ(line_tags, 'export'):
                        return 'sale_exp_wp'
                    elif tags_have_categ(line_tags, 'export_lut'):
                        return 'sale_exp_wop'
                # SEZ with payment and without payment of tax
                if gst_treatment == 'special_economic_zone':
                    if tags_have_categ(line_tags, 'export'):
                        return 'sale_sez_wp'
                    elif tags_have_categ(line_tags, 'export_lut'):
                        return 'sale_sez_wop'
                # Deemed export
                if gst_treatment == 'deemed_export' and tags_have_categ(line_tags, 'export'):
                    return 'sale_deemed_export'

            # If it's not a standard invoice (i.e., it's a debit/credit note)
            if not is_inv:
                # CDN for B2B reverse charge and B2B regular
                if gst_treatment in ('regular', 'composition', 'uin_holders'):
                    if tags_have_categ(line_tags, 'gst_rc'):
                        return 'sale_cdnr_rcm'
                    elif tags_have_categ(line_tags, 'gst'):
                        return 'sale_cdnr_regular'
                # CDN for SEZ exports with payment and without payment
                if gst_treatment == 'special_economic_zone':
                    if tags_have_categ(line_tags, 'export'):
                        return 'sale_cdnr_sez_wp'
                    elif tags_have_categ(line_tags, 'export_lut'):
                        return 'sale_cdnr_sez_wop'
                # CDN for deemed exports
                if gst_treatment == 'deemed_export' and tags_have_categ(line_tags, 'gst'):
                    return 'sale_cdnr_deemed_export'
                # CDN for B2CL (interstate > threshold)
                if (
                    gst_treatment in ('unregistered', 'consumer')
                    and tags_have_categ(line_tags, 'gst')
                    and transaction_type == 'inter_state'
                    and (
                        move.debit_origin_id and move.debit_origin_id.amount_total > amt_limit
                        or move.reversed_entry_id and move.reversed_entry_id.amount_total > amt_limit
                        or not move.reversed_entry_id and not move.is_inbound()
                    )
                ):
                    return 'sale_cdnur_b2cl'
                # CDN for exports with payment and without payment
                if gst_treatment == 'overseas':
                    if tags_have_categ(line_tags, 'export'):
                        return 'sale_cdnur_exp_wp'
                    elif tags_have_categ(line_tags, 'export_lut'):
                        return 'sale_cdnur_exp_wop'
            # If none of the above match, default to out of scope
            return 'sale_out_of_scope'

        indian_sale_moves_lines = self.filtered(
            lambda l: l.move_id.country_code == 'IN'
            and l.move_id.is_sale_document(include_receipts=True)
            and l.display_type in ('product', 'tax')
        )
        if not indian_sale_moves_lines:
            return
        tax_tags_dict = self._get_l10n_in_tax_tag_ids()

        for move_line in indian_sale_moves_lines:
            move_line.l10n_in_gstr_section = get_section(move_line, tax_tags_dict)
