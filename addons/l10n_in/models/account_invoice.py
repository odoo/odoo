# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_total_words = fields.Char("Total (In Words)", compute="_compute_amount_total_words")
    l10n_in_gst_treatment = fields.Selection([
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export'),
            ('uin_holders', 'UIN Holders'),
        ], string="GST Treatment", compute="_compute_l10n_in_gst_treatment", store=True, readonly=False, copy=True)
    l10n_in_state_id = fields.Many2one('res.country.state', string="Place of supply", compute="_compute_l10n_in_state_id", store=True, readonly=False)
    l10n_in_gstin = fields.Char(string="GSTIN")
    # For Export invoice this data is need in GSTR report
    l10n_in_shipping_bill_number = fields.Char('Shipping bill number', readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_shipping_bill_date = fields.Date('Shipping bill date', readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_shipping_port_code_id = fields.Many2one('l10n_in.port.code', 'Port code', readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_reseller_partner_id = fields.Many2one('res.partner', 'Reseller', domain=[('vat', '!=', False)], help="Only Registered Reseller", readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_journal_type = fields.Selection(string="Journal Type", related='journal_id.type')

    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        for invoice in self:
            invoice.amount_total_words = invoice.currency_id.amount_to_text(invoice.amount_total)

    @api.depends('partner_id')
    def _compute_l10n_in_gst_treatment(self):
        indian_invoice = self.filtered(lambda m: m.country_code == 'IN')
        for record in indian_invoice:
            gst_treatment = record.partner_id.l10n_in_gst_treatment
            if not gst_treatment:
                gst_treatment = 'unregistered'
                if record.partner_id.country_id.code == 'IN' and record.partner_id.vat:
                    gst_treatment = 'regular'
                elif record.partner_id.country_id and record.partner_id.country_id.code != 'IN':
                    gst_treatment = 'overseas'
            record.l10n_in_gst_treatment = gst_treatment
        (self - indian_invoice).l10n_in_gst_treatment = False

    @api.depends('partner_id', 'company_id')
    def _compute_l10n_in_state_id(self):
        for move in self:
            if move.country_code == 'IN' and move.journal_id.type == 'sale':
                country_code = move.partner_id.country_id.code
                if country_code == 'IN':
                    move.l10n_in_state_id = move.partner_id.state_id
                elif country_code:
                    move.l10n_in_state_id = self.env.ref('l10n_in.state_in_oc', raise_if_not_found=False)
                else:
                    move.l10n_in_state_id = move.company_id.state_id
            elif move.country_code == 'IN' and move.journal_id.type == 'purchase':
                move.l10n_in_state_id = move.company_id.state_id
            else:
                move.l10n_in_state_id = False

    def _post(self, soft=True):
        """Use journal type to define document type because not miss state in any entry including POS entry"""
        posted = super()._post(soft)
        gst_treatment_name_mapping = {k: v for k, v in
                             self._fields['l10n_in_gst_treatment']._description_selection(self.env)}
        for move in posted.filtered(lambda m: m.country_code == 'IN'):
            """Check state is set in company/sub-unit"""
            company_unit_partner = move.journal_id.l10n_in_gstin_partner_id or move.journal_id.company_id
            if not company_unit_partner.state_id:
                msg = _("Your company %s needs to have a correct address in order to validate this invoice.\n"
                "Set the address of your company (Don't forget the State field)") % (company_unit_partner.name)
                action = {
                    "view_mode": "form",
                    "res_model": "res.company",
                    "type": "ir.actions.act_window",
                    "res_id" : move.company_id.id,
                    "views": [[self.env.ref("base.view_company_form").id, "form"]],
                }
                raise RedirectWarning(msg, action, _('Go to Company configuration'))

            move.l10n_in_gstin = move.partner_id.vat
            if not move.l10n_in_gstin and move.l10n_in_gst_treatment in ['regular', 'composition', 'special_economic_zone', 'deemed_export']:
                raise ValidationError(_(
                    "Partner %(partner_name)s (%(partner_id)s) GSTIN is required under GST Treatment %(name)s",
                    partner_name=move.partner_id.name,
                    partner_id=move.partner_id.id,
                    name=gst_treatment_name_mapping.get(move.l10n_in_gst_treatment)
                ))
        return posted

    def _l10n_in_get_warehouse_address(self):
        """Return address where goods are delivered/received for Invoice/Bill"""
        # TO OVERRIDE
        self.ensure_one()
        return False

    @api.ondelete(at_uninstall=False)
    def _unlink_l10n_in_except_once_post(self):
        # Prevent deleting entries once it's posted for Indian Company only
        if any(m.country_code == 'IN' and m.posted_before for m in self) and not self._context.get('force_delete'):
            raise UserError(_("To keep the audit trail, you can not delete journal entries once they have been posted.\nInstead, you can cancel the journal entry."))

    def unlink(self):
        # Add logger here becouse in api ondelete account.move.line is deleted and we can't get total amount
        logger_msg = False
        if any(m.country_code == 'IN' and m.posted_before for m in self):
            if self._context.get('force_delete'):
                moves_details = ", ".join("{entry_number} ({move_id}) amount {amount_total} {currency} and partner {partner_name}".format(
                    entry_number=m.name,
                    move_id=m.id,
                    amount_total=m.amount_total,
                    currency=m.currency_id.name,
                    partner_name=m.partner_id.display_name)
                    for m in self)
                logger_msg = 'Force deleted Journal Entries %s by %s (%s)' % (moves_details, self.env.user.name, self.env.user.id)
        res = super().unlink()
        if logger_msg:
            _logger.info(logger_msg)
        return res

    def _l10n_in_get_hsn_summary(self):
        self.ensure_one()
        igst_tag_id = self.env.ref("l10n_in.tax_tag_igst").id
        cgst_tag_id = self.env.ref("l10n_in.tax_tag_cgst").id
        sgst_tag_id = self.env.ref("l10n_in.tax_tag_sgst").id
        cess_tag_id = self.env.ref("l10n_in.tax_tag_cess").id
        all_gst_tag = (igst_tag_id, cgst_tag_id, sgst_tag_id)
        tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details_from_domain(domain=[('move_id', '=', self.id)])
        self._cr.execute(f'''
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
                    where (at_rl.invoice_tax_id = any(tax_child.child_ids) OR at_rl.invoice_tax_id = aml_taxs.account_tax_id)
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
                 pt.l10n_in_hsn_code,
                 aml.move_id,
                 tax_detail.*
             FROM ({tax_details_query}) AS tax_detail
        LEFT JOIN account_tax at ON at.id = tax_detail.tax_id
        LEFT JOIN base_line_with_gst_rate aml_gst_rate ON aml_gst_rate.id = tax_detail.base_line_id
        LEFT JOIN account_move_line aml ON aml.id = tax_detail.base_line_id
        LEFT JOIN product_product p ON p.id = aml.product_id
        LEFT JOIN product_template pt ON pt.id = p.product_tmpl_id
        LEFT JOIN tax_line_with_tags aml_tags ON aml_tags.id = tax_detail.tax_line_id
         ''', tax_details_params)
        hsn_tax_details = {}
        for tax_details in self._cr.dictfetchall():
            sign = -1 if self.is_inbound(include_receipts=True) else 1
            key = "%s-%s" % (tax_details.get('l10n_in_hsn_code'), tax_details.get('gst_tax_rate'))
            hsn_tax_details.setdefault(key, {
                'l10n_in_hsn_code': tax_details.get('l10n_in_hsn_code'),
                'gst_tax_rate': tax_details.get('gst_tax_rate'),
                'SGST_amount_currency': 0.00,
                'CGST_amount_currency': 0.00,
                'IGST_amount_currency': 0.00,
                'CESS_amount_currency': 0.00,
                'tax_details': []
            })
            hsn_tax_details[key]['tax_details'].append(tax_details)
            if tax_details['tax_type'] in ['IGST', 'CGST', 'SGST', 'CESS']:
                hsn_tax_details[key]['%s_amount_currency' % tax_details['tax_type']] += tax_details['tax_amount_currency'] * sign
        return hsn_tax_details
