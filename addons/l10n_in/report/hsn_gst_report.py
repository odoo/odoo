# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class L10nInProductHsnReport(models.Model):
    _name = "l10n_in.product.hsn.report"
    _description = "Product HSN Statistics"
    _auto = False
    _order = 'date desc'

    account_move_id = fields.Many2one('account.move', string="Account Move")
    partner_id = fields.Many2one('res.partner', string="Customer")
    product_id = fields.Many2one("product.product", string="Product")
    uom_id = fields.Many2one('uom.uom', string="UOM")
    quantity = fields.Float(string="Product Qty")
    date = fields.Date(string="Date")
    price_total = fields.Float(string='Taxable Value')
    total = fields.Float(string="Total Value")
    igst_amount = fields.Float(string="Integrated Tax Amount")
    cgst_amount = fields.Float(string="Central Tax Amount")
    sgst_amount = fields.Float(string="State/UT Tax Amount")
    cess_amount = fields.Float(string="Cess Amount")
    company_id = fields.Many2one('res.company', string="Company")
    journal_id = fields.Many2one('account.journal', string="Journal")

    hsn_code = fields.Char(string="HSN")
    hsn_description = fields.Char(string="HSN description")

    l10n_in_uom_code = fields.Char(string="UQC")

    def _select(self):
        select_str = """SELECT aml.id AS id,
            aml.move_id AS account_move_id,
            aml.partner_id AS partner_id,
            aml.product_id,
            aml.product_uom_id AS uom_id,
            am.date,
            am.journal_id,
            aj.company_id,
            CASE WHEN pt.l10n_in_hsn_code IS NULL THEN '' ELSE pt.l10n_in_hsn_code END AS hsn_code,
            CASE WHEN pt.l10n_in_hsn_description IS NULL THEN '' ELSE pt.l10n_in_hsn_description END AS hsn_description,
            CASE WHEN uom.l10n_in_code IS NULL THEN '' ELSE uom.l10n_in_code END AS l10n_in_uom_code,
            CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_sgst', 'tax_report_line_sgst_rc')) OR at.l10n_in_reverse_charge = True
                THEN 0
                ELSE aml.quantity
                END AS quantity,
            CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_igst', 'tax_report_line_igst_rc'))
                THEN aml.balance * (CASE WHEN aj.type = 'sale' THEN -1 ELSE 1 END)
                ELSE 0
                END AS igst_amount,
            CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_cgst', 'tax_report_line_cgst_rc'))
                THEN aml.balance * (CASE WHEN aj.type = 'sale' THEN -1 ELSE 1 END)
                ELSE 0
                END AS cgst_amount,
            CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_sgst', 'tax_report_line_sgst_rc'))
                THEN aml.balance * (CASE WHEN aj.type = 'sale' THEN -1 ELSE 1 END)
                ELSE 0
                END AS sgst_amount,
            CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_cess', 'tax_report_line_cess_rc'))
                THEN aml.balance * (CASE WHEN aj.type = 'sale' THEN -1 ELSE 1 END)
                ELSE 0
                END AS cess_amount,
            CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_sgst', 'tax_report_line_sgst_rc'))
                THEN 0
                ELSE (CASE WHEN aml.tax_line_id IS NOT NULL THEN aml.tax_base_amount ELSE aml.balance * (CASE WHEN aj.type = 'sale' THEN -1 ELSE 1 END) END)
                END AS price_total,
            (CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_sgst', 'tax_report_line_sgst_rc'))
                THEN 0
                ELSE (CASE WHEN aml.tax_line_id IS NOT NULL THEN aml.tax_base_amount ELSE 1 END)
                END) + (aml.balance * (CASE WHEN aj.type = 'sale' THEN -1 ELSE 1 END))  AS total
        """
        return select_str

    def _from(self):
        from_str = """FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
            JOIN account_journal aj ON aj.id = am.journal_id
            JOIN product_product pp ON pp.id = aml.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN account_tax at ON at.id = aml.tax_line_id
            LEFT JOIN account_account_tag_account_move_line_rel aat_aml_rel ON aat_aml_rel.account_move_line_id = aml.id
            LEFT JOIN account_account_tag aat ON aat.id = aat_aml_rel.account_account_tag_id
            LEFT JOIN account_tax_report_line_tags_rel tag_rep_ln ON aat.id = tag_rep_ln.account_account_tag_id
            LEFT JOIN account_move_line_account_tax_rel mt ON mt.account_move_line_id = aml.id
            LEFT JOIN uom_uom uom ON uom.id = aml.product_uom_id
            WHERE aa.internal_type = 'other' AND (aml.tax_line_id IS NOT NULL OR mt.account_tax_id IS NULL)
        """
        return from_str

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE OR REPLACE VIEW %s AS (%s %s)""" % (
            self._table, self._select(), self._from()))
