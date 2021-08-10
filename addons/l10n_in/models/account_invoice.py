# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        for invoice in self:
            invoice.amount_total_words = invoice.currency_id.amount_to_text(invoice.amount_total)

    amount_total_words = fields.Char("Total (In Words)", compute="_compute_amount_total_words")
    l10n_in_gst_treatment = fields.Selection([
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export')
        ], string="GST Treatment", readonly=True, states={'draft': [('readonly', False)]})
    # We need this to show in invoice because there are many complex cases where we don't decided this automatically
    l10n_in_state_id = fields.Many2one(
        "res.country.state",
        string="Place of supply",
        domain=[("country.code", "=", "IN")],
        compute="_compute_l10n_in_state_id",
        store=True,
    )

    # For Export invoice this data is need in GSTR report
    l10n_in_shipping_bill_number = fields.Char('Shipping bill number', readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_shipping_bill_date = fields.Date('Shipping bill date', readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_shipping_port_code_id = fields.Many2one('l10n_in.port.code', 'Port code', states={'draft': [('readonly', False)]})
    l10n_in_reseller_partner_id = fields.Many2one('res.partner', 'Reseller', domain=[('vat', '!=', False)], help="Only Registered Reseller", readonly=True, states={'draft': [('readonly', False)]})

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Use journal type to define document type because not miss state in any entry including POS entry"""
        if self.country_code == 'IN':
            self.l10n_in_gst_treatment = self.partner_id.l10n_in_gst_treatment
        return super()._onchange_partner_id()

    @api.depends("partner_id", "journal_id", "l10n_in_gst_treatment")
    def _compute_l10n_in_state_id(self):
        for move in self:
            l10n_in_state_id = False
            if move.country_code == "IN" and move.journal_id.type == "sale":
                company_unit_partner = (
                    move.journal_id.l10n_in_gstin_partner_id
                    or move.journal_id.company_id.partner_id
                )
                l10n_in_state_id = self._l10n_in_get_indian_state(move.partner_id)
                # still state is not set then assumed that transaction is local like PoS so set state of company
                if not l10n_in_state_id and not move.partner_id.country_id:
                    l10n_in_state_id = company_unit_partner.state_id
            move.l10n_in_state_id = l10n_in_state_id

    @api.model
    def _l10n_in_get_indian_state(self, partner):
        """In tax return filing, If customer is not Indian in that case place of supply is must set to Other Territory.
        So we set Other Territory in l10n_in_state_id when customer(partner) is not Indian
        State is big role under GST because tax type is depend on.for more information check this https://www.cbic.gov.in/resources//htdocs-cbec/gst/Integrated%20goods%20&%20Services.pdf"""
        indian_state = False
        if partner.state_id and partner.state_id.country_id.code == "IN":
            indian_state = partner.state_id
        return indian_state

    def _post(self, soft=True):
        """Use journal type to define document type because not miss state in any entry including POS entry"""
        posted = super()._post(soft)
        gst_treatment_name_mapping = {k: v for k, v in
                             self._fields['l10n_in_gst_treatment']._description_selection(self.env)}
        for move in posted.filtered(lambda m: m.country_code == 'IN'):
            """Check state is set in company/sub-unit"""
            company_unit_partner = (
                move.journal_id.l10n_in_gstin_partner_id or move.journal_id.company_id
            )
            if not company_unit_partner.state_id:
                raise ValidationError(
                    _(
                        "State is missing from your company/unit %(company_name)s (%(company_id)s).\nFirst set state in your company/unit.",
                        company_name=company_unit_partner.name,
                        company_id=company_unit_partner.id,
                    )
                )
            if not move.commercial_partner_id.vat and move.l10n_in_gst_treatment in [
                "regular",
                "composition",
                "special_economic_zone",
                "deemed_export",
            ]:
                raise ValidationError(
                    _(
                        "Partner %(partner_name)s (%(partner_id)s) GSTIN is required under GST Treatment %(name)s",
                        partner_name=move.commercial_partner_id.name,
                        partner_id=move.commercial_partner_id.id,
                        name=gst_treatment_name_mapping.get(move.l10n_in_gst_treatment),
                    )
                )
            if not move.l10n_in_state_id and move.l10n_in_gst_treatment and move.l10n_in_gst_treatment != 'overseas' and move.move_type in [
                'out_invoice',
                'out_refund',
                'out_receipt'
            ]:
                raise ValidationError(
                    _(
                        "Place of supply is required under GST Treatment %(name)s",
                        name=gst_treatment_name_mapping.get(move.l10n_in_gst_treatment),
                    )
                )
        return posted
