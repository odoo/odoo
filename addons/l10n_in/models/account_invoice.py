# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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
            ('deemed_export', 'Deemed Export')
        ], string="GST Treatment", compute="_compute_l10n_in_gst_treatment", store=True, readonly=False)
    l10n_in_state_id = fields.Many2one('res.country.state', string="Location of supply")
    l10n_in_company_country_code = fields.Char(related='company_id.country_id.code', string="Country code")
    l10n_in_gstin = fields.Char(string="GSTIN")
    # For Export invoice this data is need in GSTR report
    l10n_in_shipping_bill_number = fields.Char('Shipping bill number', readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_shipping_bill_date = fields.Date('Shipping bill date', readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_shipping_port_code_id = fields.Many2one('l10n_in.port.code', 'Port code', states={'draft': [('readonly', False)]})
    l10n_in_reseller_partner_id = fields.Many2one('res.partner', 'Reseller', domain=[('vat', '!=', False)], help="Only Registered Reseller", readonly=True, states={'draft': [('readonly', False)]})

    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        for invoice in self:
            invoice.amount_total_words = invoice.currency_id.amount_to_text(invoice.amount_total)

    @api.depends('partner_id')
    def _compute_l10n_in_gst_treatment(self):
        for record in self:
            record.l10n_in_gst_treatment = record.partner_id.l10n_in_gst_treatment

    @api.model
    def _l10n_in_get_indian_state(self, partner):
        """In tax return filing, If customer is not Indian in that case place of supply is must set to Other Territory.
        So we set Other Territory in l10n_in_state_id when customer(partner) is not Indian
        Also we raise if state is not set in Indian customer.
        State is big role under GST because tax type is depend on.for more information check this https://www.cbic.gov.in/resources//htdocs-cbec/gst/Integrated%20goods%20&%20Services.pdf"""
        if partner.country_id and partner.country_id.code == 'IN' and not partner.state_id:
            raise ValidationError(_("State is missing from address in '%s'. First set state after post this invoice again.", partner.name))
        elif partner.country_id and partner.country_id.code != 'IN':
            return self.env.ref('l10n_in.state_in_ot')
        return partner.state_id


    @api.model
    def _get_tax_grouping_key_from_tax_line(self, tax_line):
        # OVERRIDE to group taxes also by product.
        res = super()._get_tax_grouping_key_from_tax_line(tax_line)
        if tax_line.move_id.journal_id.company_id.country_id.code == 'IN':
            res['product_id'] = tax_line.product_id.id
            res['product_uom_id'] = tax_line.product_uom_id.id
        return res

    @api.model
    def _get_tax_grouping_key_from_base_line(self, base_line, tax_vals):
        # OVERRIDE to group taxes also by product.
        res = super()._get_tax_grouping_key_from_base_line(base_line, tax_vals)
        if base_line.move_id.journal_id.company_id.country_id.code == 'IN':
            res['product_id'] = base_line.product_id.id
            res['product_uom_id'] = base_line.product_uom_id.id
        return res

    @api.model
    def _get_tax_key_for_group_add_base(self, line):
        # DEPRECATED: TO BE REMOVED IN MASTER
        tax_key = super(AccountMove, self)._get_tax_key_for_group_add_base(line)

        tax_key += [
            line.product_id.id,
            line.product_uom_id.id,
        ]
        return tax_key

    def _l10n_in_get_shipping_partner(self):
        """Overwrite in sale"""
        self.ensure_one()
        return self.partner_id

    @api.model
    def _l10n_in_get_shipping_partner_gstin(self, shipping_partner):
        """Overwrite in sale"""
        return shipping_partner.vat

    def _post(self, soft=True):
        """Use journal type to define document type because not miss state in any entry including POS entry"""
        posted = super()._post(soft)
        gst_treatment_name_mapping = {k: v for k, v in
                             self._fields['l10n_in_gst_treatment']._description_selection(self.env)}
        for move in posted.filtered(lambda m: m.l10n_in_company_country_code == 'IN'):
            """Check state is set in company/sub-unit"""
            company_unit_partner = move.journal_id.l10n_in_gstin_partner_id or move.journal_id.company_id
            if not company_unit_partner.state_id:
                raise ValidationError(_(
                    "State is missing from your company/unit %(company_name)s (%(company_id)s).\nFirst set state in your company/unit.",
                    company_name=company_unit_partner.name,
                    company_id=company_unit_partner.id
                ))
            elif move.journal_id.type == 'purchase':
                move.l10n_in_state_id = company_unit_partner.state_id

            shipping_partner = move._l10n_in_get_shipping_partner()
            # In case of shipping address does not have GSTN then also check customer(partner_id) GSTN
            # This happens when Bill-to Ship-to transaction where shipping(Ship-to) address is unregistered and customer(Bill-to) is registred.
            move.l10n_in_gstin = move._l10n_in_get_shipping_partner_gstin(shipping_partner) or move.partner_id.vat
            if not move.l10n_in_gstin and move.l10n_in_gst_treatment in ['regular', 'composition', 'special_economic_zone', 'deemed_export']:
                raise ValidationError(_(
                    "Partner %(partner_name)s (%(partner_id)s) GSTIN is required under GST Treatment %(name)s",
                    partner_name=shipping_partner.name,
                    partner_id=shipping_partner.id,
                    name=gst_treatment_name_mapping.get(move.l10n_in_gst_treatment)
                ))
            if move.journal_id.type == 'sale':
                move.l10n_in_state_id = self._l10n_in_get_indian_state(shipping_partner)
                if not move.l10n_in_state_id:
                    move.l10n_in_state_id = self._l10n_in_get_indian_state(move.partner_id)
                #still state is not set then assumed that transaction is local like PoS so set state of company unit
                if not move.l10n_in_state_id:
                    move.l10n_in_state_id = company_unit_partner.state_id
        return posted
