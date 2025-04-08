import re
from datetime import date

from odoo import _, api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_in_hsn_code = fields.Char(string="HSN/SAC Code", compute="_compute_l10n_in_hsn_code", store=True, readonly=False, copy=False)
    l10n_in_gstr_section = fields.Selection(
        selection=[
            ("b2b_rcm", "B2B RCM"),
            ("b2b_regular", "B2B Regular"),
            ("b2cl", "B2CL"),
            ("b2cs", "B2CS"),
            ("exp_wp", "EXP(WP)"),
            ("exp_wop", "EXP(WOP)"),
            ("sez_wp", "SEZ(WP)"),
            ("sez_wop", "SEZ(WOP)"),
            ("deemed_export", "Deemed Export"),
            ("cdnr_rcm", "CDNR RCM"),
            ("cdnr_regular", "CDNR Regular"),
            ("cdnr_deemed_export", "CDNR(Deemed Export)"),
            ("cdnr_sez", "CDNR(SEZ)"),
            ("cdnur_b2cl", "CDNUR(B2CL)"),
            ("cdnur_exp_wp", "CDNUR(EXP-WP)"),
            ("cdnur_exp_wop", "CDNUR(EXP-WOP)"),
            ("nil_rated", "Nil Rated"),
            ("out_of_scope", "Out of Scope")
            ],
        string="GSTR Section",
        compute="_compute_l10n_in_gstr_section",
        store=True,
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

    def get_l10n_in_tax_tag_ids(self):

        def get_tag_ids(*refs):
            return [self.env.ref(ref).id for ref in refs]

        return {
            'gst_rc': get_tag_ids(
                'l10n_in.tax_tag_base_sgst_rc', 'l10n_in.tax_tag_sgst_rc',
                'l10n_in.tax_tag_base_cgst_rc', 'l10n_in.tax_tag_cgst_rc',
                'l10n_in.tax_tag_base_igst_rc', 'l10n_in.tax_tag_igst_rc',
                'l10n_in.tax_tag_base_cess_rc', 'l10n_in.tax_tag_cess_rc'
            ),
            'gst': get_tag_ids(
                'l10n_in.tax_tag_base_sgst', 'l10n_in.tax_tag_sgst',
                'l10n_in.tax_tag_base_cgst', 'l10n_in.tax_tag_cgst',
                'l10n_in.tax_tag_base_igst', 'l10n_in.tax_tag_igst',
                'l10n_in.tax_tag_base_cess', 'l10n_in.tax_tag_cess'
            ),
            'nil': get_tag_ids(
                'l10n_in.tax_tag_exempt', 'l10n_in.tax_tag_nil_rated', 'l10n_in.tax_tag_non_gst_supplies'
            ),
            'export': get_tag_ids(
                'l10n_in.tax_tag_zero_rated', 'l10n_in.tax_tag_base_igst', 'l10n_in.tax_tag_igst',
                'l10n_in.tax_tag_base_cess', 'l10n_in.tax_tag_cess'
            ),
            'igst_lut': get_tag_ids('l10n_in.tax_tag_igst_lut')
        }

    @api.depends('move_id.l10n_in_gst_treatment', 'move_id.amount_total', 'move_id.l10n_in_state_id', 'company_id', 'tax_tag_ids')
    def _compute_l10n_in_gstr_section(self):

        def has_tags(category):
            return any(tag in tax_tags for tag in tax_tags_ids[category])

        def is_invoice(move):
            return (
                move.is_inbound() and not move.debit_origin_id
            )

        def get_transaction_type(move):
            return 'intra_state' if move.l10n_in_state_id == move.company_id.state_id else 'inter_state'

        def is_b2b_rcm(line):
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment in ('regular', 'composition', 'uin_holders') and
                has_tags('gst_rc')
            )

        def is_b2b_regular(line):
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment in ('regular', 'composition', 'uin_holders') and
                has_tags('gst')
            )

        def is_b2cl(line):
            amount_limit = 100000 if line.invoice_date >= date(2024, 11, 1) else 250000
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment in ('unregistered', 'consumer') and
                has_tags('gst') and
                get_transaction_type(line.move_id) == 'inter_state' and
                line.move_id.amount_total > amount_limit
            )

        def is_b2cs(line):
            amount_limit = 100000 if line.invoice_date >= date(2024, 11, 1) else 250000
            return (
                line.move_id.l10n_in_gst_treatment in ('unregistered', 'consumer') and
                has_tags('gst') and
                (get_transaction_type(line.move_id) == 'intra_state' or
                (get_transaction_type(line.move_id) == 'inter_state' and
                    (is_invoice(line.move_id) and line.move_id.amount_total <= amount_limit) or
                    (line.move_id.debit_origin_id and line.move_id.debit_origin_id.amount_total <= amount_limit) or
                    (line.move_id.reversed_entry_id and line.move_id.reversed_entry_id.amount_total <= amount_limit)
                ))
            )

        def is_exp_wp(line):
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'overseas' and
                has_tags('export')
            )

        def is_exp_wop(line):
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'overseas' and
                has_tags('igst_lut')
            )

        def is_sez_wp(line):
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'special_economic_zone' and
                has_tags('export')
            )

        def is_sez_wop(line):
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'special_economic_zone' and
                has_tags('igst_lut')
            )

        def is_deemed_export(line):
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'deemed_export' and
                has_tags('gst')
            )

        def is_nil_rated(line):
            return (
                line.move_id.l10n_in_gst_treatment not in ('overseas', 'special_economic_zone') and
                has_tags('nil')
            )

        def is_cdnr_rcm(line):
            return (
                not is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment in ('regular', 'composition', 'uin_holders') and
                has_tags('gst_rc')
            )

        def is_cdnr_regular(line):
            return (
                not is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment in ('regular', 'composition', 'uin_holders') and
                has_tags('gst')
            )

        def is_cdnr_sez(line):
            return (
                not is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'special_economic_zone' and
                has_tags('export')
            )

        def is_cdnr_deemed_export(line):
            return (
                not is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'deemed_export' and
                has_tags('gst')
            )

        def is_cdnur_b2cl(line):
            amount_limit = 100000 if line.invoice_date >= date(2024, 11, 1) else 250000
            return (
                not is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment in ('unregistered', 'consumer') and
                has_tags('gst') and
                get_transaction_type(line.move_id) == 'inter_state' and
                (
                    (line.move_id.debit_origin_id and line.move_id.debit_origin_id.amount_total > amount_limit) or
                    (line.move_id.reversed_entry_id and line.move_id.reversed_entry_id.amount_total > amount_limit) or
                    (not line.move_id.reversed_entry_id and not line.move_id.is_inbound())
                )
            )

        def is_cdnur_exp_wp(line):
            return (
                not is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'overseas' and
                has_tags('export')
            )

        def is_cdnur_exp_wop(line):
            return (
                not is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'overseas' and
                has_tags('igst_lut')
            )

        indian_moves_lines = self.filtered(lambda l: l.move_id.country_code == 'IN' and l.move_id.is_sale_document(include_receipts=True) and l.parent_state == 'posted')
        (self - indian_moves_lines).l10n_in_gstr_section = False
        if not indian_moves_lines:
            return


        gstr_mapping_fun = {
            "b2b_rcm": is_b2b_rcm,
            "b2b_regular": is_b2b_regular,
            "b2cl": is_b2cl,
            "b2cs": is_b2cs,
            "exp_wp": is_exp_wp,
            "exp_wop": is_exp_wop,
            "sez_wp": is_sez_wp,
            "sez_wop": is_sez_wop,
            "deemed_export": is_deemed_export,
            "cdnr_rcm": is_cdnr_rcm,
            "cdnr_regular": is_cdnr_regular,
            "cdnr_sez": is_cdnr_sez,
            "cdnr_deemed_export": is_cdnr_deemed_export,
            "cdnur_b2cl": is_cdnur_b2cl,
            "cdnur_exp_wp": is_cdnur_exp_wp,
            "cdnur_exp_wop": is_cdnur_exp_wop,
            "nil_rated": is_nil_rated
        }
        tax_tags_ids = self.get_l10n_in_tax_tag_ids()
        for line in indian_moves_lines:
            tax_tags = line.tax_tag_ids.ids
            line.l10n_in_gstr_section = next(
                (section for section, function in gstr_mapping_fun.items() if function(line)),
                'out_of_scope'
            )
