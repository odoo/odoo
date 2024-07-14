# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.osv import expression


class CrmLead(models.Model):
    _inherit = "crm.lead"

    rental_quotation_count = fields.Integer(
        compute="_compute_rental_count", string="Number of Rental Quotations")
    rental_amount_total = fields.Monetary(
        compute='_compute_rental_count', string="Sum of Rental Orders",
        help="Untaxed Total of Confirmed Orders", currency_field='company_currency')
    rental_order_count = fields.Integer(
        compute='_compute_rental_count', string="Number of Rental Orders")
    rental_order_ids = fields.One2many(
        "sale.order", "opportunity_id", string="Rental Orders",
        domain=[("is_rental_order", "=", True)])

    def _compute_rental_count(self):
        for lead in self:
            total = 0.0
            company_currency = lead.company_currency or self.env.company.currency_id
            sale_orders = lead.rental_order_ids.filtered(lambda l: l.state == 'sale')
            for order in sale_orders:
                total += order.currency_id._convert(
                    order.amount_untaxed, company_currency, order.company_id, order.date_order or fields.Date.today())
            lead.rental_quotation_count = len(lead.rental_order_ids.filtered(lambda l: l.state in ["draft", "sent"]))
            lead.rental_order_count = len(sale_orders)
            lead.rental_amount_total = total

    def _get_action_view_sale_quotation_domain(self):
        # over-ride to exclude rental quotations linked to lead
        action_lead_quotation_domain = super()._get_action_view_sale_quotation_domain()
        return expression.AND([action_lead_quotation_domain, [("is_rental_order", "=", False)]])

    def _get_lead_quotation_domain(self):
        # over-ride to exclude rental quotations linked to lead
        lead_quotation_domain = super()._get_lead_quotation_domain()
        return expression.AND([lead_quotation_domain, [("is_rental_order", "=", False)]])

    def _get_lead_sale_order_domain(self):
        # over-ride to exclude rental sale orders linked to lead
        lead_sale_order_domain = super()._get_lead_sale_order_domain()
        return expression.AND([lead_sale_order_domain, [("is_rental_order", "=", False)]])

    def action_rental_quotations_new(self):
        if not self.partner_id:
            return self.env["ir.actions.actions"]._for_xml_id("sale_renting_crm.crm_lead_to_rental_action")
        return self.action_new_rental_quotation()

    def _get_action_rental_context(self):
        self.ensure_one()
        rental_quotation_context = {
            "search_default_opportunity_id": self.id,
            "default_opportunity_id": self.id,
            "default_partner_id": self.partner_id.id,
            "default_team_id": self.team_id.id,
            "default_campaign_id": self.campaign_id.id,
            "default_medium_id": self.medium_id.id,
            "default_origin": self.name,
            "default_source_id": self.source_id.id,
            "default_company_id": self.company_id.id or self.env.company.id,
            "in_rental_app": True,
        }
        if self.user_id:
            rental_quotation_context['default_user_id'] = self.user_id.id
        return rental_quotation_context

    def action_new_rental_quotation(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Rental Orders"),
            "res_model": "sale.order",
            "view_mode": "form",
            "views": [(self.env.ref("sale_renting.rental_order_primary_form_view").id, "form")],
            "context": self._get_action_rental_context(),
        }

    def action_view_rental_quotation(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale_renting.rental_order_action")
        action.update({
            'context': self._get_action_rental_context(),
            'domain': [("opportunity_id", "=", self.id), ('is_rental_order', '=', True)]
        })

        if not self._context.get('is_rental_order'):
            action['domain'].append(("state", "in", ["draft", "sent"]))
            orders = self.rental_order_ids.filtered(lambda l: l.state in ("draft", "sent"))
        else:
            action['domain'].append(("state", "=", "sale"))
            orders = self.rental_order_ids.filtered(lambda l: l.state == "sale")

        if len(orders) == 1:
            action.update({
                'views': [(self.env.ref("sale_renting.rental_order_primary_form_view").id, "form")],
                'res_id': orders.id,
            })
        return action
