# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo import tools

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_in_hsn_code = fields.Char(string="HSN/SAC Code", compute="_compute_l10n_in_hsn_code", store=True, readonly=False, copy=False)
    l10n_in_gst_rate = fields.Float('GST Rate', compute="_compute_l10n_in_tax_details", store=False, readonly=False)
    l10n_in_cgst_amount_currency = fields.Monetary('CGST', compute="_compute_l10n_in_tax_details", store=False, readonly=True, currency_field='company_currency_id')
    l10n_in_sgst_amount_currency = fields.Monetary('SGST', compute='_compute_l10n_in_tax_details', store=False, readonly=True, currency_field='company_currency_id')
    l10n_in_igst_amount_currency = fields.Monetary('IGST', compute='_compute_l10n_in_tax_details', store=False, readonly=True, currency_field='company_currency_id')
    l10n_in_cess_amount_currency = fields.Monetary('CESS', compute="_compute_l10n_in_tax_details", store=False, readonly=True, currency_field='company_currency_id')
    vat = fields.Char(related="partner_id.vat")

    @api.depends('product_id')
    def _compute_l10n_in_hsn_code(self):
        indian_lines = self.filtered(lambda line: line.company_id.account_fiscal_country_id.code == 'IN')
        (self - indian_lines).l10n_in_hsn_code = False
        for line in indian_lines:
            if line.product_id:
                line.l10n_in_hsn_code = line.product_id.l10n_in_hsn_code

    def init(self):
        tools.create_index(self._cr, 'account_move_line_move_product_index', self._table, ['move_id', 'product_id'])

    @api.depends('move_id.line_ids', 'move_id.line_ids.tax_line_id', 'move_id.line_ids.debit', 'move_id.line_ids.credit')
    def _compute_tax_base_amount(self):
        aml = self.filtered(lambda l: l.company_id.account_fiscal_country_id.code == 'IN' and l.tax_line_id  and l.product_id)
        for move_line in aml:
            base_lines = move_line.move_id.line_ids.filtered(lambda line: move_line.tax_line_id in line.tax_ids and move_line.product_id == line.product_id)
            move_line.tax_base_amount = abs(sum(base_lines.mapped('balance')))
        remaining_aml = self - aml
        if remaining_aml:
            return super(AccountMoveLine, remaining_aml)._compute_tax_base_amount()

    def _format_l10n_in_tax_detail_by_move_line_id(self, tax_data):
        formatted_data = {}
        for data in tax_data:
            base_line_id = data['base_line_id']
            tax_type = data['tax_type']
            if not formatted_data.get(base_line_id):
                formatted_data.setdefault(base_line_id, {'gst_tax_rate': data['gst_tax_rate']})
            if not formatted_data[base_line_id].get(tax_type):
                formatted_data[base_line_id].setdefault(tax_type, 0)
            formatted_data[base_line_id][tax_type] += data['tax_amount']
        return formatted_data

    def _compute_l10n_in_tax_details(self):
        domain = [
            ("move_id.id", "in", self.move_id.ids)
        ]
        tax_query, tax_params = self._get_l10n_in_tax_details_query(domain)
        self._cr.execute(tax_query, tax_params)
        tax_data = self._cr.dictfetchall()
        data_by_aml_id = self._format_l10n_in_tax_detail_by_move_line_id(tax_data)
        for record in self:
            sign = record.move_id.is_inbound() and -1 or 1
            tax_details = data_by_aml_id.get(record.id, {})
            record.l10n_in_gst_rate = tax_details.get('gst_tax_rate', 0)
            record.l10n_in_sgst_amount_currency = sign*tax_details.get('SGST', 0)
            record.l10n_in_cgst_amount_currency = sign*tax_details.get('CGST', 0)
            record.l10n_in_igst_amount_currency = sign*tax_details.get('IGST', 0)
            record.l10n_in_cess_amount_currency = sign*tax_details.get('CESS', 0)

    @api.model
    def _get_l10n_in_tax_details_query(self, domain):
        igst_tag_id = self.env.ref("l10n_in.tax_tag_igst").id
        cgst_tag_id = self.env.ref("l10n_in.tax_tag_cgst").id
        sgst_tag_id = self.env.ref("l10n_in.tax_tag_sgst").id
        cess_tag_id = self.env.ref("l10n_in.tax_tag_cess").id
        all_gst_tag = (igst_tag_id, cgst_tag_id, sgst_tag_id)
        tax_details_query, tax_details_params = self._get_query_tax_details_from_domain(domain=domain)
        return f'''
             WITH RECURSIVE tax_child_tree(id, child_ids) AS (
                SELECT tax_fil_rel.parent_tax,
                       ARRAY_AGG(tax_fil_rel.child_tax)
                  FROM account_tax_filiation_rel tax_fil_rel
              GROUP BY tax_fil_rel.parent_tax
             UNION ALL
                SELECT tax_fil_rel.parent_tax, ARRAY_APPEND(ct.child_ids, tax_fil_rel.parent_tax)
                  FROM account_tax_filiation_rel tax_fil_rel
                  JOIN tax_child_tree ct ON ct.id = tax_fil_rel.child_tax
            ),
            base_line_with_gst_rate AS (
                SELECT aml.id, sum(CASE WHEN at.amount_type != 'group' THEN at.amount ELSE 0 END) as gst_rate
                FROM account_move_line aml
                JOIN account_move_line_account_tax_rel aml_taxs ON aml_taxs.account_move_line_id = aml.id
                LEFT JOIN tax_child_tree tax_child ON aml_taxs.account_tax_id = tax_child.id
                JOIN account_tax at ON at.id = aml_taxs.account_tax_id or at.id = any(tax_child.child_ids)
                WHERE EXISTS(SELECT 1
                    FROM account_tax_repartition_line at_rl
                    JOIN account_account_tag_account_tax_repartition_line_rel tax_tag ON tax_tag.account_tax_repartition_line_id = at_rl.id
                   where (at_rl.tax_id = at.id OR at_rl.tax_id = aml_taxs.account_tax_id)
                     and tax_tag.account_account_tag_id in {all_gst_tag}
                )
                GROUP BY aml.id
            ),
            tax_line_with_tags AS (
                SELECT aml.id, array_agg(aml_tag.account_account_tag_id) as tag_ids
                FROM account_move_line aml
                JOIN account_account_tag_account_move_line_rel aml_tag ON aml_tag.account_move_line_id = aml.id
                GROUP BY aml.id
            )
            SELECT
                COALESCE(aml_gst_rate.gst_rate, 0) as gst_tax_rate,
                aml_tags.tag_ids,
                at.l10n_in_reverse_charge,
                CASE
                    WHEN {igst_tag_id} = any(aml_tags.tag_ids) THEN 'IGST'
                    WHEN {cgst_tag_id} = any(aml_tags.tag_ids) THEN 'CGST'
                    WHEN {sgst_tag_id} = any(aml_tags.tag_ids) THEN 'SGST'
                    WHEN {cess_tag_id} = any(aml_tags.tag_ids) THEN 'CESS'
                END as tax_type,
                tax_detail.*
            FROM ({tax_details_query}) AS tax_detail
        LEFT JOIN account_tax at ON at.id = tax_detail.tax_id
        LEFT JOIN base_line_with_gst_rate aml_gst_rate ON aml_gst_rate.id = tax_detail.base_line_id
        LEFT JOIN tax_line_with_tags aml_tags ON aml_tags.id = tax_detail.tax_line_id
        ''', tax_details_params
