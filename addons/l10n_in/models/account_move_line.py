import re
from datetime import date

from odoo import _, api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_in_hsn_code = fields.Char(string="HSN/SAC Code", compute="_compute_l10n_in_hsn_code", store=True, readonly=False, copy=False)
    l10n_in_gstr_section = fields.Selection(
        selection=[
            ("sale_b2b_rcm", "B2B RCM"),
            ("sale_b2b_regular", "B2B Regular"),
            ("sale_b2cl", "B2CL"),
            ("sale_b2cs", "B2CS"),
            ("sale_exp_wp", "EXP(WP)"),
            ("sale_exp_wop", "EXP(WOP)"),
            ("sale_sez_wp", "SEZ(WP)"),
            ("sale_sez_wop", "SEZ(WOP)"),
            ("sale_deemed_export", "Deemed Export"),
            ("sale_cdnr_rcm", "CDNR RCM"),
            ("sale_cdnr_regular", "CDNR Regular"),
            ("sale_cdnr_deemed_export", "CDNR(Deemed Export)"),
            ("sale_cdnr_sez_wp", "CDNR(SEZ-WP)"),
            ("sale_cdnr_sez_wop", "CDNR(SEZ-WOP)"),
            ("sale_cdnur_b2cl", "CDNUR(B2CL)"),
            ("sale_cdnur_exp_wp", "CDNUR(EXP-WP)"),
            ("sale_cdnur_exp_wop", "CDNUR(EXP-WOP)"),
            ("sale_nil_rated", "Nil Rated"),
            ("sale_exempt", "Exempt"),
            ("sale_non_gst_supplies", "Non-GST Supplies"),
            ("sale_eco_9_5", "ECO 9(5)"),
            ("sale_out_of_scope", "Out of Scope"),
            ("purchase_b2b_regular", "B2B Regular"),
            ("purchase_b2c_regular", "B2C Regular"),  # will be removed in master
            ("purchase_b2b_rcm", "B2B RCM"),
            ("purchase_b2c_rcm", "B2C RCM"),
            ("purchase_imp_services", "IMP(service)"),
            ("purchase_imp_goods", "IMP(goods)"),
            ("purchase_cdnr_regular", "CDNR Regular"),
            ("purchase_cdnur_regular", "CDNUR Regular"),
            ("purchase_cdnr_rcm", "CDNR RCM"),
            ("purchase_cdnur_rcm", "CDNUR RCM"),
            ("purchase_nil_rated", "Nil Rated"),
            ("purchase_exempt", "Exempt"),
            ("purchase_non_gst_supplies", "Non-GST Supplies"),
            ("purchase_out_of_scope", "Out of Scope"),
            ],
        string="GSTR Section",
        index="btree_not_null",
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
        xmlid_to_res_id = self.env['ir.model.data']._xmlid_to_res_id
        tag_refs = {
            'sgst': ['l10n_in.tax_tag_base_sgst', 'l10n_in.tax_tag_sgst'],
            'cgst': ['l10n_in.tax_tag_base_cgst', 'l10n_in.tax_tag_cgst'],
            'igst': ['l10n_in.tax_tag_base_igst', 'l10n_in.tax_tag_igst'],
            'cess': ['l10n_in.tax_tag_base_cess', 'l10n_in.tax_tag_cess'],
            'eco_9_5': ['l10n_in.tax_tag_eco_9_5'],
        }
        return {
            categ: [xmlid_to_res_id(xml_id) for xml_id in ref]
            for categ, ref in tag_refs.items()
        }

    def _get_l10n_in_gstr_section(self, tax_tags_dict):

        def tags_have_categ(line_tax_tags, categories):
            return any(tag in line_tax_tags for category in categories for tag in tax_tags_dict.get(category, []))

        def is_invoice(move):
            return move.is_inbound() and not move.debit_origin_id

        def is_move_bill(move):
            return move.is_outbound() and not move.debit_origin_id

        def get_transaction_type(move):
            return 'intra_state' if move.l10n_in_state_id == move.company_id.state_id else 'inter_state'

        def is_reverse_charge_tax(line):
            return any(tax.l10n_in_reverse_charge for tax in line.tax_ids | line.tax_line_id)

        def is_lut_tax(line):
            return any(tax.l10n_in_is_lut for tax in line.tax_ids | line.tax_line_id)

        def get_sales_section(line):
            move = line.move_id
            gst_treatment = move.l10n_in_gst_treatment
            transaction_type = get_transaction_type(move)
            line_tags = line.tax_tag_ids.ids
            is_inv = is_invoice(move)
            amt_limit = 100000 if not line.invoice_date or line.invoice_date >= date(2024, 11, 1) else 250000

            # ECO 9(5) Section: Check if the line has the ECO 9(5) tax tag
            if tags_have_categ(line_tags, ['eco_9_5']):
                return 'sale_eco_9_5'

            # Nil rated, Exempt, Non-GST Sales
            if gst_treatment != 'overseas':
                if any(tax.l10n_in_tax_type == 'nil_rated' for tax in line.tax_ids):
                    return 'sale_nil_rated'
                elif any(tax.l10n_in_tax_type == 'exempt' for tax in line.tax_ids):
                    return 'sale_exempt'
                elif any(tax.l10n_in_tax_type == 'non_gst' for tax in line.tax_ids):
                    return 'sale_non_gst_supplies'

            # B2CS: Unregistered or Consumer sales with gst tags
            if gst_treatment in ('unregistered', 'consumer') and not is_reverse_charge_tax(line):
                if (transaction_type == 'intra_state' and tags_have_categ(line_tags, ['sgst', 'cgst', 'cess'])) or (
                    transaction_type == "inter_state"
                    and tags_have_categ(line_tags, ['igst', 'cess'])
                    and not is_lut_tax(line)
                    and (
                        is_inv and move.amount_total <= amt_limit
                        or move.debit_origin_id and move.debit_origin_id.amount_total <= amt_limit
                        or move.reversed_entry_id and move.reversed_entry_id.amount_total <= amt_limit
                    )
                ):
                    return 'sale_b2cs'

            # If no relevant tags are found, or the tags do not match any category, mark as out of scope
            if not line_tags or not tags_have_categ(line_tags, ['sgst', 'cgst', 'igst', 'cess', 'eco_9_5']):
                return 'sale_out_of_scope'

            # If it's a standard invoice (not a debit/credit note)
            if is_inv:
                # B2B with Reverse Charge and Regular
                if gst_treatment in ('regular', 'composition', 'uin_holders') and tags_have_categ(line_tags, ['sgst', 'cgst', 'igst', 'cess']) and not is_lut_tax(line):
                    if is_reverse_charge_tax(line):
                        return 'sale_b2b_rcm'
                    return 'sale_b2b_regular'

                if not is_reverse_charge_tax(line):
                    # B2CL: Unregistered interstate sales above threshold
                    if (
                        gst_treatment in ('unregistered', 'consumer')
                        and tags_have_categ(line_tags, ['igst', 'cess'])
                        and not is_lut_tax(line)
                        and transaction_type == 'inter_state'
                        and move.amount_total > amt_limit
                    ):
                        return 'sale_b2cl'
                    # Export with payment and without payment (under LUT) of tax
                    if gst_treatment == 'overseas' and tags_have_categ(line_tags, ['igst', 'cess']):
                        if is_lut_tax(line):
                            return 'sale_exp_wop'
                        return 'sale_exp_wp'
                    # SEZ with payment and without payment of tax
                    if gst_treatment == 'special_economic_zone' and tags_have_categ(line_tags, ['igst', 'cess']):
                        if is_lut_tax(line):
                            return 'sale_sez_wop'
                        return 'sale_sez_wp'
                    # Deemed export
                    if gst_treatment == 'deemed_export' and tags_have_categ(line_tags, ['sgst', 'cgst', 'igst', 'cess']) and not is_lut_tax(line):
                        return 'sale_deemed_export'

            # If it's not a standard invoice (i.e., it's a debit/credit note)
            if not is_inv:
                # CDN for B2B reverse charge and B2B regular
                if gst_treatment in ('regular', 'composition', 'uin_holders') and tags_have_categ(line_tags, ['sgst', 'cgst', 'igst', 'cess']) and not is_lut_tax(line):
                    if is_reverse_charge_tax(line):
                        return 'sale_cdnr_rcm'
                    return 'sale_cdnr_regular'
                if not is_reverse_charge_tax(line):
                    # CDN for SEZ exports with payment and without payment
                    if gst_treatment == 'special_economic_zone' and tags_have_categ(line_tags, ['igst', 'cess']):
                        if is_lut_tax(line):
                            return 'sale_cdnr_sez_wop'
                        return 'sale_cdnr_sez_wp'
                    # CDN for deemed exports
                    if gst_treatment == 'deemed_export' and tags_have_categ(line_tags, ['sgst', 'cgst', 'igst', 'cess']) and not is_lut_tax(line):
                        return 'sale_cdnr_deemed_export'
                    # CDN for B2CL (interstate > threshold)
                    if (
                        gst_treatment in ('unregistered', 'consumer')
                        and tags_have_categ(line_tags, ['igst', 'cess'])
                        and not is_lut_tax(line)
                        and transaction_type == 'inter_state'
                        and (
                            move.debit_origin_id and move.debit_origin_id.amount_total > amt_limit
                            or move.reversed_entry_id and move.reversed_entry_id.amount_total > amt_limit
                            or not move.reversed_entry_id and not move.is_inbound()
                        )
                    ):
                        return 'sale_cdnur_b2cl'
                    # CDN for exports with payment and without payment
                    if gst_treatment == 'overseas' and tags_have_categ(line_tags, ['igst', 'cess']):
                        if is_lut_tax(line):
                            return 'sale_cdnur_exp_wop'
                        return 'sale_cdnur_exp_wp'
            # If none of the above match, default to out of scope
            return 'sale_out_of_scope'

        def get_purchase_section(line):
            move = line.move_id
            gst_treatment = move.l10n_in_gst_treatment
            line_tags = line.tax_tag_ids.ids
            is_bill = is_move_bill(move)

            # Nil rated, Exempt, Non-GST purchases
            if gst_treatment != 'overseas':
                if any(tax.l10n_in_tax_type == 'nil_rated' for tax in line.tax_ids):
                    return 'purchase_nil_rated'
                elif any(tax.l10n_in_tax_type == 'exempt' for tax in line.tax_ids):
                    return 'purchase_exempt'
                elif any(tax.l10n_in_tax_type == 'non_gst' for tax in line.tax_ids):
                    return 'purchase_non_gst_supplies'

            # If no relevant tags are found, or the tags do not match any category, mark as out of scope
            if not line_tags or not tags_have_categ(line_tags, ['sgst', 'cgst', 'igst', 'cess']):
                return 'purchase_out_of_scope'

            if is_bill:
                # B2B Regular and Reverse Charge purchases
                if (gst_treatment in ('regular', 'composition', 'uin_holders') and tags_have_categ(line_tags, ['sgst', 'cgst', 'igst', 'cess'])):
                    if is_reverse_charge_tax(line):
                        return 'purchase_b2b_rcm'
                    return 'purchase_b2b_regular'

                if not is_reverse_charge_tax(line) and (
                    gst_treatment == 'deemed_export' and tags_have_categ(line_tags, ['sgst', 'cgst', 'igst', 'cess'])
                    or gst_treatment == 'special_economic_zone' and tags_have_categ(line_tags, ['igst', 'cess'])
                ):
                    return 'purchase_b2b_regular'

                # B2C Unregistered or Consumer sales with gst tags
                if gst_treatment in ('unregistered', 'consumer') and tags_have_categ(line_tags, ['sgst', 'cgst', 'igst', 'cess']) and is_reverse_charge_tax(line):
                    return 'purchase_b2c_rcm'

                # export service type products purchases
                if gst_treatment == 'overseas' and any(tax.tax_scope == 'service' for tax in line.tax_ids | line.tax_line_id) and tags_have_categ(line_tags, ['igst', 'cess']):
                    return 'purchase_imp_services'

                # export goods type products purchases
                if gst_treatment == 'overseas' and tags_have_categ(line_tags, ['igst', 'cess']) and not is_reverse_charge_tax(line):
                    return 'purchase_imp_goods'

            if not is_bill:
                # credit notes for b2b purchases
                if gst_treatment in ('regular', 'composition', 'uin_holders') and tags_have_categ(line_tags, ['sgst', 'cgst', 'igst', 'cess']):
                    if is_reverse_charge_tax(line):
                        return 'purchase_cdnr_rcm'
                    return 'purchase_cdnr_regular'

                # credit notes for b2c purchases
                if gst_treatment in ('unregistered', 'consumer') and tags_have_categ(line_tags, ['sgst', 'cgst', 'igst', 'cess']) and is_reverse_charge_tax(line):
                    return 'purchase_cdnur_rcm'

                if not is_reverse_charge_tax(line):
                    if gst_treatment == 'deemed_export' and tags_have_categ(line_tags, ['sgst', 'cgst', 'igst', 'cess'])\
                        or gst_treatment == 'special_economic_zone' and tags_have_categ(line_tags, ['igst', 'cess']):
                        return 'purchase_cdnr_regular'

                    if gst_treatment == 'overseas' and tags_have_categ(line_tags, ['igst', 'cess']):
                        return 'purchase_cdnur_regular'

            # If none of the above match, default to out of scope
            return 'purchase_out_of_scope'

        indian_sale_moves_lines = self.filtered(
            lambda l: l.move_id.country_code == 'IN'
            and l.move_id.is_sale_document(include_receipts=True)
            and l.display_type in ('product', 'tax')
        )
        indian_moves_purchase_lines = self.filtered(
            lambda l: l.move_id.country_code == 'IN'
            and l.move_id.is_purchase_document(include_receipts=True)
            and l.display_type in ('product', 'tax')
        )
        # No Indian sale or purchase lines to process
        if not indian_sale_moves_lines and not indian_moves_purchase_lines:
            return {}

        move_lines_by_gstr_section = {
            **indian_sale_moves_lines.grouped(get_sales_section),
            **indian_moves_purchase_lines.grouped(get_purchase_section),
        }

        return move_lines_by_gstr_section

    def _set_l10n_in_gstr_section(self, tax_tags_dict):
        move_lines_by_gstr_section = self._get_l10n_in_gstr_section(tax_tags_dict)
        if move_lines_by_gstr_section:
            for gstr_section, move_lines in move_lines_by_gstr_section.items():
                move_lines.l10n_in_gstr_section = gstr_section
