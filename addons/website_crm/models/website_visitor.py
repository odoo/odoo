from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class WebsiteVisitor(models.Model):
    _inherit = "website.visitor"

    lead_ids = fields.Many2many(
        comodel_name="crm.lead",
        string="Leads",
        groups="sale.group_sale_salesman",
    )
    lead_count = fields.Count(
        count_of="lead_ids",
        string="# Leads",
        groups="sale.group_sale_salesman",
    )

    @api.depends(
        "partner_id.email_normalized",
        "partner_id.phone_ids",
        "lead_ids.email_normalized",
        "lead_ids.phone_ids",
    )
    def _compute_email_phone(self):
        super()._compute_email_phone()

        left_visitors = self.filtered(
            lambda visitor: not visitor.email or not visitor.mobile
        )
        leads = left_visitors.mapped("lead_ids").sorted("create_date", reverse=True)
        visitor_to_lead_ids = {
            visitor.id: visitor.lead_ids.ids for visitor in left_visitors
        }
        _debug.pipeline(
            "email_phone_from_leads",
            visitors=self,
            incomplete=len(left_visitors),
            leads=leads,
        )

        for visitor in left_visitors:
            visitor_leads = leads.filtered(
                lambda lead, visitor=visitor: lead.id in visitor_to_lead_ids[visitor.id]
            )
            if not visitor.email:
                visitor.email = next(
                    (
                        lead.email_normalized
                        for lead in visitor_leads
                        if lead.email_normalized
                    ),
                    False,
                )
            if not visitor.mobile:
                visitor.mobile = next(
                    (
                        lead._phone_get_number().number
                        for lead in visitor_leads
                        if lead.phone_ids
                    ),
                    False,
                )

    def _check_for_message_composer(self):
        check = super()._check_for_message_composer()
        if not check and self.lead_ids:
            sorted_leads = self.lead_ids._sort_by_confidence_level(reverse=True)
            partners = sorted_leads.mapped("partner_id")
            if not partners:
                main_lead = self.lead_ids[0]
                main_lead._handle_partner_assignment(create_missing=True)
                _debug.lifecycle(
                    "partner_created_for_visitor",
                    visitor=self,
                    lead=main_lead,
                    partner=main_lead.partner_id,
                )
                self.partner_id = main_lead.partner_id.id
            return True
        return check

    def _get_domain_inactive_visitors(self):
        return super()._get_domain_inactive_visitors() & Domain("lead_ids", "=", False)

    def _merge_visitor(self, target):
        if self.lead_ids:
            _debug.lifecycle(
                "leads_reassigned", visitor=self, target=target, leads=self.lead_ids
            )
            target.write({"lead_ids": [(4, lead.id) for lead in self.lead_ids]})

        return super()._merge_visitor(target)

    def _prepare_message_composer_context(self):
        if not self.partner_id and self.lead_ids:
            sorted_leads = self.lead_ids._sort_by_confidence_level(reverse=True)
            lead_partners = sorted_leads.mapped("partner_id")
            partner = lead_partners[0] if lead_partners else False
            if partner:
                return {
                    "default_model": "crm.lead",
                    "default_res_id": sorted_leads[0].id,
                    "default_partner_ids": partner.ids,
                }
        return super()._prepare_message_composer_context()
