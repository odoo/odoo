# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class L10nInAccountInvoiceReport(models.Model):
    _name = "l10n_in.account.invoice.report"
    _description = "Account Invoice Statistics"
    _auto = False
    _order = 'date desc'

    account_move_id = fields.Many2one('account.move', string="Account Move")
    company_id = fields.Many2one('res.company', string="Company")
    date = fields.Date(string="Accounting Date")
    name = fields.Char(string="Invoice Number")
    partner_id = fields.Many2one('res.partner', string="Customer")
    is_reverse_charge = fields.Char("Reverse Charge")
    l10n_in_export_type = fields.Selection([
        ('regular', 'Regular'), ('deemed', 'Deemed'),
        ('sale_from_bonded_wh', 'Sale from Bonded WH'),
        ('export_with_igst', 'Export with IGST'),
        ('sez_with_igst', 'SEZ with IGST payment'),
        ('sez_without_igst', 'SEZ without IGST payment')])
    journal_id = fields.Many2one('account.journal', string="Journal")
    state = fields.Selection([('draft', 'Unposted'), ('posted', 'Posted')], string='Status')
    igst_amount = fields.Float(string="IGST Amount")
    cgst_amount = fields.Float(string="CGST Amount")
    sgst_amount = fields.Float(string="SGST Amount")
    cess_amount = fields.Float(string="Cess Amount")
    price_total = fields.Float(string='Total Without Tax')
    total = fields.Float(string="Invoice Total")
    reversed_entry_id = fields.Many2one('account.move', string="Refund Invoice", help="From where this Refund is created")
    shipping_bill_number = fields.Char(string="Shipping Bill Number")
    shipping_bill_date = fields.Date(string="Shipping Bill Date")
    shipping_port_code_id = fields.Many2one('l10n_in.port.code', string='Shipping port code')
    ecommerce_partner_id = fields.Many2one('res.partner', string="E-commerce")
    move_type = fields.Selection(selection=[
        ('entry', 'Journal Entry'),
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Credit Note'),
        ('in_invoice', 'Vendor Bill'),
        ('in_refund', 'Vendor Credit Note'),
        ('out_receipt', 'Sales Receipt'),
        ('in_receipt', 'Purchase Receipt')])
    partner_vat = fields.Char(string="Customer GSTIN")
    ecommerce_vat = fields.Char(string="E-commerce GSTIN")
    tax_rate = fields.Float(string="Rate")
    place_of_supply = fields.Char(string="Place of Supply")
    is_pre_gst = fields.Char(string="Is Pre GST")
    is_ecommerce = fields.Char(string="Is E-commerce")
    b2cl_is_ecommerce = fields.Char(string="B2CL Is E-commerce")
    b2cs_is_ecommerce = fields.Char(string="B2CS Is E-commerce")
    supply_type = fields.Char(string="Supply Type")
    export_type = fields.Char(string="Export Type")  # String from GSTR column.
    refund_export_type = fields.Char(string="UR Type")  # String from GSTR column.
    b2b_type = fields.Char(string="B2B Invoice Type")
    refund_invoice_type = fields.Char(string="Document Type")
    gst_format_date = fields.Char(string="Formated Date")
    gst_format_refund_date = fields.Char(string="Formated Refund Date")
    gst_format_shipping_bill_date = fields.Char(string="Formated Shipping Bill Date")
    tax_id = fields.Many2one('account.tax', string="Tax")

    def _select(self):
        select_str = """
            SELECT min(sub.id) as id,
            sub.move_id,
            sub.account_move_id,
            sub.name,
            sub.state,
            sub.partner_id,
            sub.date,
            sub.l10n_in_export_type,
            sub.ecommerce_partner_id,
            sub.shipping_bill_number,
            sub.shipping_bill_date,
            sub.shipping_port_code_id,
            sub.total,
            sub.journal_id,
            sub.company_id,
            sub.move_type,
            sub.reversed_entry_id,
            sub.partner_vat,
            sub.ecommerce_vat,
            sub.tax_rate as tax_rate,
            (CASE WHEN count(sub.is_reverse_charge) > 0
                THEN 'Y'
                ELSE 'N'
                END) AS is_reverse_charge,
            sub.place_of_supply,
            sub.is_pre_gst,
            sub.is_ecommerce,
            sub.b2cl_is_ecommerce,
            sub.b2cs_is_ecommerce,
            sub.supply_type,
            sub.export_type,
            sub.refund_export_type,
            sub.b2b_type,
            sub.refund_invoice_type,
            sub.gst_format_date,
            sub.gst_format_refund_date,
            sub.gst_format_shipping_bill_date,
            sum(sub.igst_amount) * sub.amount_sign AS igst_amount,
            sum(sub.cgst_amount) * sub.amount_sign AS cgst_amount,
            sum(sub.sgst_amount) * sub.amount_sign AS sgst_amount,
            avg(sub.cess_amount) * sub.amount_sign AS cess_amount,
            sum(sub.price_total) AS price_total,
            sub.tax_id
        """
        return select_str

    def _sub_select(self):
        sub_select_str = """
            SELECT aml.id AS id,
                aml.move_id,
                aml.partner_id,
                am.id AS account_move_id,
                am.name,
                am.state,
                am.date,
                am.l10n_in_export_type AS l10n_in_export_type,
                am.l10n_in_reseller_partner_id AS ecommerce_partner_id,
                am.l10n_in_shipping_bill_number AS shipping_bill_number,
                am.l10n_in_shipping_bill_date AS shipping_bill_date,
                am.l10n_in_shipping_port_code_id AS shipping_port_code_id,
                ABS(am.amount_total_signed) AS total,
                am.journal_id,
                aj.company_id,
                am.type AS move_type,
                am.reversed_entry_id AS reversed_entry_id,
                p.vat AS partner_vat,
                CASE WHEN rp.vat IS NULL THEN '' ELSE rp.vat END AS ecommerce_vat,
                (CASE WHEN at.l10n_in_reverse_charge = True
                    THEN True
                    ELSE NULL
                    END)  AS is_reverse_charge,
                (CASE WHEN ps.l10n_in_tin IS NOT NULL
                    THEN concat(ps.l10n_in_tin,'-',ps.name)
                    WHEN ps.id IS NULL and cps.l10n_in_tin IS NOT NULL
                    THEN concat(cps.l10n_in_tin,'-',cps.name)
                    ELSE ''
                    END) AS place_of_supply,
                (CASE WHEN am.type in ('out_refund', 'in_refund') and refund_am.date <= to_date('2017-07-01', 'YYYY-MM-DD')
                    THEN 'Y'
                    ELSE 'N'
                    END) as is_pre_gst,

                (CASE WHEN am.l10n_in_reseller_partner_id IS NOT NULL
                    THEN 'Y'
                    ELSE 'N'
                    END) as is_ecommerce,
                (CASE WHEN am.l10n_in_reseller_partner_id IS NOT NULL
                    THEN 'Y'
                    ELSE 'N'
                    END) as b2cl_is_ecommerce,
                (CASE WHEN am.l10n_in_reseller_partner_id IS NOT NULL
                    THEN 'E'
                    ELSE 'OE'
                    END) as b2cs_is_ecommerce,
                (CASE WHEN ps.id = cp.state_id or p.id IS NULL
                    THEN 'Intra State'
                    WHEN ps.id != cp.state_id and p.id IS NOT NULL
                    THEN 'Inter State'
                    END) AS supply_type,
                (CASE WHEN am.l10n_in_export_type in ('deemed', 'export_with_igst', 'sez_with_igst')
                    THEN 'EXPWP'
                    WHEN am.l10n_in_export_type in ('sale_from_bonded_wh', 'sez_without_igst')
                    THEN 'EXPWOP'
                    ELSE ''
                    END) AS export_type,
                (CASE WHEN refund_am.l10n_in_export_type in ('deemed', 'export_with_igst', 'sez_with_igst')
                    THEN 'EXPWP'
                    WHEN refund_am.l10n_in_export_type in ('sale_from_bonded_wh', 'sez_without_igst')
                    THEN 'EXPWOP'
                    ELSE 'B2CL'
                    END) AS refund_export_type,
                (CASE WHEN am.l10n_in_export_type = 'regular'
                    THEN 'Regular'
                    WHEN am.l10n_in_export_type = 'deemed'
                    THEN 'Deemed'
                    WHEN am.l10n_in_export_type = 'sale_from_bonded_wh'
                    THEN 'Sale from Bonded WH'
                    WHEN am.l10n_in_export_type = 'export_with_igst'
                    THEN 'Export with IGST'
                    WHEN am.l10n_in_export_type = 'sez_with_igst'
                    THEN 'SEZ with IGST payment'
                    WHEN am.l10n_in_export_type = 'sez_without_igst'
                    THEN 'SEZ without IGST payment'
                    END) AS b2b_type,
                (CASE WHEN am.type = 'out_refund'
                    THEN 'C'
                    WHEN am.type = 'in_refund'
                    THEN 'D'
                    ELSE ''
                    END) as refund_invoice_type,
                (CASE WHEN am.date IS NOT NULL
                    THEN TO_CHAR(am.date, 'DD-MON-YYYY')
                    ELSE ''
                    END) as gst_format_date,
                (CASE WHEN refund_am.date IS NOT NULL
                    THEN TO_CHAR(refund_am.date, 'DD-MON-YYYY')
                    ELSE ''
                    END) as gst_format_refund_date,
                (CASE WHEN am.l10n_in_shipping_bill_date IS NOT NULL
                    THEN TO_CHAR(am.l10n_in_shipping_bill_date, 'DD-MON-YYYY')
                    ELSE ''
                    END) as gst_format_shipping_bill_date,
                CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                    (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name='tax_report_line_igst')
                    THEN aml.balance
                    ELSE 0
                    END AS igst_amount,
                CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                    (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name='tax_report_line_cgst')
                    THEN aml.balance
                    ELSE 0
                    END AS cgst_amount,
                CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                    (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name='tax_report_line_sgst')
                    THEN aml.balance
                    ELSE 0
                    END AS sgst_amount,
                (SELECT sum(temp_aml.balance) from account_move_line temp_aml
                    JOIN account_account_tag_account_move_line_rel aat_aml_rel_temp ON aat_aml_rel_temp.account_move_line_id = temp_aml.id
                    JOIN account_account_tag aat_temp ON aat_temp.id = aat_aml_rel_temp.account_account_tag_id
                    JOIN account_tax_report_line_tags_rel tag_rep_ln_temp ON aat_temp.id = tag_rep_ln_temp.account_account_tag_id
                    where temp_aml.move_id = aml.move_id and temp_aml.product_id = aml.product_id
                    and tag_rep_ln_temp.account_tax_report_line_id IN (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name='tax_report_line_cess')
                    ) AS cess_amount,
                CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                    (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name='tax_report_line_sgst') OR at.l10n_in_reverse_charge = True
                    THEN NULL
                    ELSE (CASE WHEN aml.tax_base_amount <> 0 THEN aml.tax_base_amount ELSE NULL END)
                    END AS price_total,
                (CASE WHEN aj.type = 'sale' AND (am.type IS NULL OR am.type != 'out_refund') THEN -1 ELSE 1 END) AS amount_sign,
                (CASE WHEN atr.parent_tax IS NOT NULL THEN atr.parent_tax
                    ELSE at.id END) AS tax_id,
                (CASE WHEN atr.parent_tax IS NOT NULL THEN parent_at.amount
                    ELSE at.amount END) AS tax_rate
        """
        return sub_select_str

    def _from(self):
        from_str = """
            FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                JOIN account_journal aj ON aj.id = am.journal_id
                JOIN res_company c ON c.id = aj.company_id
                LEFT JOIN account_tax at ON at.id = aml.tax_line_id
                JOIN account_account_tag_account_move_line_rel aat_aml_rel ON aat_aml_rel.account_move_line_id = aml.id
                JOIN account_account_tag aat ON aat.id = aat_aml_rel.account_account_tag_id
                JOIN account_tax_report_line_tags_rel tag_rep_ln ON aat.id = tag_rep_ln.account_account_tag_id
                LEFT JOIN res_partner cp ON cp.id = c.partner_id
                LEFT JOIN res_country_state cps ON cps.id = cp.state_id
                LEFT JOIN account_move refund_am ON refund_am.id = am.reversed_entry_id
                LEFT JOIN res_partner p ON p.id = aml.partner_id
                LEFT JOIN res_country_state ps ON ps.id = p.state_id
                LEFT JOIN res_partner rp ON rp.id = am.l10n_in_reseller_partner_id
                LEFT JOIN account_tax_filiation_rel atr ON atr.child_tax = at.id
                LEFT JOIN account_tax parent_at ON parent_at.id = atr.parent_tax
                """
        return from_str

    def _where(self):
        return """
                WHERE am.state = 'posted'
                    AND tag_rep_ln.account_tax_report_line_id in (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_igst','tax_report_line_cgst','tax_report_line_sgst','tax_report_line_zero_rated'))
        """

    def _group_by(self):
        group_by_str = """
        GROUP BY sub.move_id,
            sub.account_move_id,
            sub.name,
            sub.state,
            sub.partner_id,
            sub.date,
            sub.l10n_in_export_type,
            sub.ecommerce_partner_id,
            sub.shipping_bill_number,
            sub.shipping_bill_date,
            sub.shipping_port_code_id,
            sub.total,
            sub.journal_id,
            sub.company_id,
            sub.move_type,
            sub.reversed_entry_id,
            sub.partner_vat,
            sub.ecommerce_vat,
            sub.place_of_supply,
            sub.is_pre_gst,
            sub.is_ecommerce,
            sub.b2cl_is_ecommerce,
            sub.b2cs_is_ecommerce,
            sub.supply_type,
            sub.export_type,
            sub.refund_export_type,
            sub.b2b_type,
            sub.refund_invoice_type,
            sub.gst_format_date,
            sub.gst_format_refund_date,
            sub.gst_format_shipping_bill_date,
            sub.amount_sign,
            sub.tax_id,
            sub.tax_rate
        """
        return group_by_str

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s AS (
            %s
            FROM (
                %s %s %s
            ) AS sub %s)""" % (self._table, self._select(), self._sub_select(),
                self._from(), self._where(), self._group_by()))
