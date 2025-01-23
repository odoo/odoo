from datetime import date
import re

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
        string="GSTR-1 Section",
        compute="_compute_l10n_in_gstr_section",
        search="_search_l10n_in_gstr_section",
    )

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

    @api.depends('move_id.l10n_in_gst_treatment', 'move_id.amount_total', 'move_id.l10n_in_state_id', 'company_id', 'tax_tag_ids')
    def _compute_l10n_in_gstr_section(self):

        def has_tags(tags):
            return any(tag in tax_tags for tag in tags)

        def is_invoice(move):
            return (
                move.is_inbound() and not move.debit_origin_id
            )

        def get_transaction_type(move):
            if move.l10n_in_state_id and move.l10n_in_state_id == move.company_id.state_id:
                return 'intra_state'
            else:
                return 'inter_state'

        def is_b2b_rcm(line):
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment in ('regular', 'composition', 'uin_holders') and
                has_tags(gst_rc_tags)
            )

        def is_b2b_regular(line):
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment in ('regular', 'composition', 'uin_holders') and
                has_tags(gst_tags)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                
            )

        def is_b2cl(line):
            amount_limit = 100000 if line.invoice_date >= date(2024, 11, 1) else 250000
            return (
                is_invoice(line.move_id) and                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
                line.move_id.l10n_in_gst_treatment in ('unregistered', 'consumer') and
                has_tags(gst_tags) and
                get_transaction_type(line.move_id) == 'inter_state' and
                line.move_id.amount_total > amount_limit
            )

        def is_b2cs(line):
            amount_limit = 100000 if line.invoice_date >= date(2024, 11, 1) else 250000
            return (
                line.move_id.l10n_in_gst_treatment in ('unregistered', 'consumer') and
                has_tags(gst_tags) and
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
                has_tags(export_tags)
            )

        def is_exp_wop(line):
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'overseas' and
                has_tags(igst_lut_tag)
            )

        def is_sez_wp(line):
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'special_economic_zone' and
                has_tags(export_tags)
            )

        def is_sez_wop(line):
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'special_economic_zone' and
                has_tags(igst_lut_tag)
            )

        def is_deemed_export(line):
            return (
                is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'deemed_export' and
                has_tags(gst_tags)
            )

        def is_nil_rated(line):
            return (
                line.move_id.l10n_in_gst_treatment not in ('overseas', 'special_economic_zone') and
                has_tags(nil_tags)
            )

        def is_cdnr_rcm(line):
            return (
                not is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment in ('regular', 'composition', 'uin_holders') and
                has_tags(gst_rc_tags)
            )

        def is_cdnr_regular(line):
            return (
                not is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment in ('regular', 'composition', 'uin_holders') and
                has_tags(gst_tags)
            )

        def is_cdnr_sez(line):
            return (
                not is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'special_economic_zone' and
                has_tags(export_tags)
            )

        def is_cdnr_deemed_export(line):
            return (
                not is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'deemed_export' and
                has_tags(gst_tags)
            )

        def is_cdnur_b2cl(line):
            amount_limit = 100000 if line.invoice_date >= date(2024, 11, 1) else 250000
            return (
                not is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment in ('unregistered', 'consumer') and
                has_tags(gst_tags) and
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
                has_tags(export_tags)
            )

        def is_cdnur_exp_wop(line):
            return (
                not is_invoice(line.move_id) and
                line.move_id.l10n_in_gst_treatment == 'overseas' and
                has_tags(igst_lut_tag)
            )

        indian_moves_lines = self.filtered(lambda l: l.move_id.country_code == 'IN' and l.move_id.is_sale_document(include_receipts=True) and l.parent_state == 'posted')
        (self - indian_moves_lines).l10n_in_gstr_section = False
        if not indian_moves_lines:
            return
        gst_tags = self.env.ref('l10n_in.tax_tag_base_sgst') + self.env.ref('l10n_in.tax_tag_sgst')\
                    + self.env.ref('l10n_in.tax_tag_base_cgst') + self.env.ref('l10n_in.tax_tag_cgst')\
                    + self.env.ref('l10n_in.tax_tag_base_igst') + self.env.ref('l10n_in.tax_tag_igst')\
                    + self.env.ref('l10n_in.tax_tag_base_cess') + self.env.ref('l10n_in.tax_tag_cess')
        gst_rc_tags = self.env.ref('l10n_in.tax_tag_base_sgst_rc') + self.env.ref('l10n_in.tax_tag_sgst_rc')\
                        + self.env.ref('l10n_in.tax_tag_base_cgst_rc') + self.env.ref('l10n_in.tax_tag_cgst_rc')\
                        + self.env.ref('l10n_in.tax_tag_base_igst_rc') + self.env.ref('l10n_in.tax_tag_igst_rc')\
                        + self.env.ref('l10n_in.tax_tag_base_cess_rc') + self.env.ref('l10n_in.tax_tag_cess_rc')
        nil_tags = self.env.ref('l10n_in.tax_tag_exempt') + self.env.ref('l10n_in.tax_tag_nil_rated') + self.env.ref('l10n_in.tax_tag_non_gst_supplies')
        export_tags = self.env.ref('l10n_in.tax_tag_zero_rated') + self.env.ref('l10n_in.tax_tag_base_igst') + self.env.ref('l10n_in.tax_tag_igst') + self.env.ref('l10n_in.tax_tag_base_cess') + self.env.ref('l10n_in.tax_tag_cess')
        igst_lut_tag = self.env.ref('l10n_in.tax_tag_igst_lut')

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
        for line in indian_moves_lines:
            tax_tags = line.tax_tag_ids
            line.l10n_in_gstr_section = next(
                (section for section, function in gstr_mapping_fun.items() if function(line)),
                'out_of_scope'
            )

    def _search_l10n_in_gstr_section(self, operator, value):
        if operator not in ['in', '=', 'not in']:
            raise NotImplementedError(f"Operator '{operator}' not supported")
        gst_rc_tags = (self.env.ref('l10n_in.tax_tag_base_sgst_rc') + self.env.ref('l10n_in.tax_tag_sgst_rc') + self.env.ref('l10n_in.tax_tag_base_cgst_rc') + self.env.ref('l10n_in.tax_tag_cgst_rc') + self.env.ref('l10n_in.tax_tag_base_igst_rc') + self.env.ref('l10n_in.tax_tag_igst_rc') + self.env.ref('l10n_in.tax_tag_base_cess_rc') + self.env.ref('l10n_in.tax_tag_cess_rc')).ids
        gst_tags = (self.env.ref('l10n_in.tax_tag_base_sgst') + self.env.ref('l10n_in.tax_tag_sgst') + self.env.ref('l10n_in.tax_tag_base_cgst') + self.env.ref('l10n_in.tax_tag_cgst') + self.env.ref('l10n_in.tax_tag_base_igst') + self.env.ref('l10n_in.tax_tag_igst') + self.env.ref('l10n_in.tax_tag_base_cess') + self.env.ref('l10n_in.tax_tag_cess')).ids
        nil_tags = self.env.ref('l10n_in.tax_tag_exempt') + self.env.ref('l10n_in.tax_tag_nil_rated') + self.env.ref('l10n_in.tax_tag_non_gst_supplies')
        export_tags = self.env.ref('l10n_in.tax_tag_zero_rated') + self.env.ref('l10n_in.tax_tag_base_igst') + self.env.ref('l10n_in.tax_tag_igst') + self.env.ref('l10n_in.tax_tag_base_cess') + self.env.ref('l10n_in.tax_tag_cess')
        igst_lut_tag = self.env.ref('l10n_in.tax_tag_igst_lut')
        if operator == '=':
            if value != 'b2b_rcm':
                pass
            if value == 'b2b_rcm':
                query = """
                    SELECT aml.id
                      FROM account_move_line aml
                      JOIN account_move am ON aml.move_id = am.id
                      JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                      JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                     WHERE am.move_type IN ('out_invoice', 'out_receipt')
                       AND am.debit_origin_id IS NULL
                       AND am.l10n_in_gst_treatment IN ('regular', 'composition', 'uin_holders')
                       AND tag.id IN %s
                """
                params = [tuple(gst_rc_tags)]
                lines = self.env.cr.execute(query, params)
            if value == 'b2b_regular':
                query = """
                    SELECT aml.id
                      FROM account_move_line aml
                      JOIN account_move am ON aml.move_id = am.id
                      JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                      JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                     WHERE am.move_type IN ('out_invoice', 'out_receipt')
                       AND am.debit_origin_id IS NULL
                       AND am.l10n_in_gst_treatment IN ('regular', 'composition', 'uin_holders')
                       AND tag.id IN %s
                """
                params = [tuple(gst_tags)]
                lines = self.env.cr.execute(query, params)
            if value == 'b2cl':
                query = """
                    SELECT aml.id
                      FROM account_move_line aml
                      JOIN account_move am ON aml.move_id = am.id
                      JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                      JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                     WHERE am.move_type IN ('out_invoice', 'out_receipt')
                       AND am.debit_origin_id IS NULL
                       AND am.l10n_in_gst_treatment IN ('unregistered', 'consumer')
                       AND tag.id IN %s
                       AND am.amount_total > CASE
                           WHEN am.invoice_date >= '2024-11-01' THEN 100000
                           ELSE 250000
                       END
                       AND am.l10n_in_transaction_type = 'inter_state'
                """
                params = [tuple(gst_tags)]
                lines = self.env.cr.execute(query, params)
            if value == 'b2cs':
                query = """
                    SELECT aml.id
                      FROM account_move_line aml
                      JOIN account_move am ON aml.move_id = am.id
                      JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                      JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                     WHERE am.l10n_in_gst_treatment IN ('unregistered', 'consumer')
                       AND tag.id IN %s
                       AND (
                           am.l10n_in_transaction_type = 'intra_state' OR
                           (
                               am.l10n_in_transaction_type = 'inter_state' AND
                               (
                                    (am.move_type IN ('out_invoice', 'out_receipt') AND am.amount_total <= CASE WHEN am.invoice_date >= '2024-11-01' THEN 100000 ELSE 250000 END) OR
                                    (am.debit_origin_id IS NOT NULL AND am.debit_origin_id IN (
                                        SELECT id FROM account_move WHERE amount_total <= CASE WHEN invoice_date >= '2024-11-01' THEN 100000 ELSE 250000 END
                                    )) OR
                                    (am.reversed_entry_id IS NOT NULL AND am.reversed_entry_id IN (
                                        SELECT id FROM account_move WHERE amount_total <= CASE WHEN invoice_date >= '2024-11-01' THEN 100000 ELSE 250000 END
                                    ))
                                )
                            )
                       )
                """
                params = [tuple(gst_tags)]
                lines = self.env.cr.execute(query, params)
            if value == 'exp_wp':
                query = """
                    SELECT aml.id
                      FROM account_move_line aml
                      JOIN account_move am ON aml.move_id = am.id
                      JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                      JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                     WHERE am.move_type IN ('out_invoice', 'out_receipt')
                       AND am.debit_origin_id IS NULL
                       AND am.l10n_in_gst_treatment = 'overseas'
                       AND tag.id IN %s
                """
                params = [tuple(export_tags)]
                lines = self.env.cr.execute(query, params)
            if value == 'exp_wop':
                query = """
                    SELECT aml.id
                      FROM account_move_line aml
                      JOIN account_move am ON aml.move_id = am.id
                      JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                      JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                     WHERE am.move_type IN ('out_invoice', 'out_receipt')
                       AND am.debit_origin_id IS NULL
                       AND am.l10n_in_gst_treatment = 'overseas'
                       AND tag.id IN %s
                """
                params = [tuple(igst_lut_tag)]
                lines = self.env.cr.execute(query, params)
            if value == 'sez_wp':
                query = """
                    SELECT aml.id
                      FROM account_move_line aml
                      JOIN account_move am ON aml.move_id = am.id
                      JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                      JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                     WHERE am.move_type IN ('out_invoice', 'out_receipt')
                       AND am.debit_origin_id IS NULL
                       AND am.l10n_in_gst_treatment = 'special_economic_zone'
                       AND tag.id IN %s
                """
                params = [tuple(export_tags)]
                lines = self.env.cr.execute(query, params)
            if value == 'sez_wop':
                query = """
                    SELECT aml.id
                      FROM account_move_line aml
                      JOIN account_move am ON aml.move_id = am.id
                      JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                      JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                     WHERE am.move_type IN ('out_invoice', 'out_receipt')
                       AND am.debit_origin_id IS NULL
                       AND am.l10n_in_gst_treatment = 'special_economic_zone'
                       AND tag.id IN %s
                """
                params = [tuple(igst_lut_tag)]
                lines = self.env.cr.execute(query, params)
            if value == 'deemed_export':
                query = """
                    SELECT aml.id
                      FROM account_move_line aml
                      JOIN account_move am ON aml.move_id = am.id
                      JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                      JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                     WHERE am.move_type IN ('out_invoice', 'out_receipt')
                       AND am.debit_origin_id IS NULL
                       AND am.l10n_in_gst_treatment = 'deemed_export'
                       AND tag.id IN %s
                """
                params = [tuple(gst_tags)]
                lines = self.env.cr.execute(query, params)
            if value == 'cdnr_rcm':
                query = """
                    SELECT aml.id
                    FROM account_move_line aml
                    JOIN account_move am ON aml.move_id = am.id
                    JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                    JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                    WHERE (
                        (am.debit_origin_id IS NOT NULL AND am.move_type = 'out_invoice') OR
                        (am.debit_origin_id IS NULL AND am.move_type = 'out_refund')
                        )
                    AND am.l10n_in_gst_treatment IN ('regular', 'composition', 'uin_holders')
                    AND tag.id IN %s
                """
                params = [tuple(gst_rc_tags)]
                lines = self.env.cr.execute(query, params)
            if value == 'cdnr_regular':
                query = """
                    SELECT aml.id
                    FROM account_move_line aml
                    JOIN account_move am ON aml.move_id = am.id
                    JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                    JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                    WHERE (
                        (am.debit_origin_id IS NOT NULL AND am.move_type = 'out_invoice') OR
                        (am.debit_origin_id IS NULL AND am.move_type = 'out_refund')
                        )
                    AND am.l10n_in_gst_treatment IN ('regular', 'composition', 'uin_holders')
                    AND tag.id IN %s
                """
                params = [tuple(gst_tags)]
                lines = self.env.cr.execute(query, params)
            if value == 'cdnr_sez':
                query = """
                    SELECT aml.id
                    FROM account_move_line aml
                    JOIN account_move am ON aml.move_id = am.id
                    JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                    JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                    WHERE (
                        (am.debit_origin_id IS NOT NULL AND am.move_type = 'out_invoice') OR
                        (am.debit_origin_id IS NULL AND am.move_type = 'out_refund')
                        )
                    AND am.l10n_in_gst_treatment = 'special_economic_zone'
                    AND tag.id IN %s
                """
                params = [tuple(export_tags)]
                lines = self.env.cr.execute(query, params)
            if value == 'cdnr_deemed_export':
                query = """
                    SELECT aml.id
                    FROM account_move_line aml
                    JOIN account_move am ON aml.move_id = am.id
                    JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                    JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                    WHERE (
                        (am.debit_origin_id IS NOT NULL AND am.move_type = 'out_invoice') OR
                        (am.debit_origin_id IS NULL AND am.move_type = 'out_refund')
                        )
                    AND am.l10n_in_gst_treatment = 'deemed_export'
                    AND tag.id IN %s
                """
                params = [tuple(gst_tags)]
                lines = self.env.cr.execute(query, params)
            if value == 'cdnur_b2cl':
                query = """
                    SELECT aml.id
                    FROM account_move_line aml
                    JOIN account_move am ON aml.move_id = am.id
                    JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                    JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                    WHERE (
                        (am.debit_origin_id IS NOT NULL AND am.move_type = 'out_invoice') OR
                        (am.debit_origin_id IS NULL AND am.move_type = 'out_refund')
                        )
                    AND am.l10n_in_gst_treatment IN ('unregistered', 'consumer')
                    AND tag.id IN %s
                    AND am.l10n_in_transaction_type = 'inter_state'
                    AND (
                        (am.debit_origin_id IS NOT NULL AND am.debit_origin_id IN (
                            SELECT id FROM account_move WHERE amount_total > CASE WHEN invoice_date >= '2024-11-01' THEN 100000 ELSE 250000 END
                        )) OR
                        (am.reversed_entry_id IS NOT NULL AND am.reversed_entry_id IN (
                            SELECT id FROM account_move WHERE amount_total > CASE WHEN invoice_date >= '2024-11-01' THEN 100000 ELSE 250000 END
                        )) OR
                        (am.reversed_entry_id IS NULL AND am.move_type = 'out_refund')
                    )
                """
                params = [tuple(gst_tags)]
                lines = self.env.cr.execute(query, params)
            if value == 'cdnur_exp_wp':
                query = """
                    SELECT aml.id
                    FROM account_move_line aml
                    JOIN account_move am ON aml.move_id = am.id
                    JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                    JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                    WHERE (
                        (am.debit_origin_id IS NOT NULL AND am.move_type = 'out_invoice') OR
                        (am.debit_origin_id IS NULL AND am.move_type = 'out_refund')
                        )
                    AND am.l10n_in_gst_treatment = 'overseas'
                    AND tag.id IN %s
                """
                params = [tuple(export_tags)]
                lines = self.env.cr.execute(query, params)
            if value == 'cdnur_exp_wop':
                query = """
                    SELECT aml.id
                    FROM account_move_line aml
                    JOIN account_move am ON aml.move_id = am.id
                    JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                    JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                    WHERE (
                        (am.debit_origin_id IS NOT NULL AND am.move_type = 'out_invoice') OR
                        (am.debit_origin_id IS NULL AND am.move_type = 'out_refund')
                        )
                    AND am.l10n_in_gst_treatment = 'overseas'
                    AND tag.id IN %s
                """
                params = [tuple(igst_lut_tag)]
                lines = self.env.cr.execute(query, params)
            if value == 'nil_rated':
                query = """
                    SELECT aml.id
                    FROM account_move_line aml
                    JOIN account_account_tag_account_move_line_rel tag_rel ON aml.id = tag_rel.account_move_line_id
                    JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
                    WHERE tag.id IN %s
                """
                params = [tuple(nil_tags.ids)]
                lines = self.env.cr.execute(query, params)
