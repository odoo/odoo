# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.fields import Domain


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    lead_ids = fields.Many2many('crm.lead', string='Leads', groups="sales_team.group_sale_salesman")
    lead_count = fields.Integer('# Leads', compute="_compute_lead_count", groups="sales_team.group_sale_salesman")

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        for visitor in self:
            visitor.lead_count = len(visitor.lead_ids)

    @api.depends('partner_id.email_normalized', 'partner_id.phone', 'lead_ids.email_normalized', 'lead_ids.phone')
    def _compute_email_phone(self):
        super(WebsiteVisitor, self)._compute_email_phone()

        left_visitors = self.filtered(lambda visitor: not visitor.email or not visitor.mobile)
        leads = left_visitors.mapped('lead_ids').sorted('create_date', reverse=True)
        visitor_to_lead_ids = dict((visitor.id, visitor.lead_ids.ids) for visitor in left_visitors)

        for visitor in left_visitors:
            visitor_leads = leads.filtered(lambda lead: lead.id in visitor_to_lead_ids[visitor.id])
            if not visitor.email:
                visitor.email = next((lead.email_normalized for lead in visitor_leads if lead.email_normalized), False)
            if not visitor.mobile:
                visitor.mobile = next((lead.phone for lead in visitor_leads if lead.phone), False)

    def _check_for_message_composer(self):
        check = super(WebsiteVisitor, self)._check_for_message_composer()
        if not check and self.lead_ids:
            sorted_leads = self.lead_ids._sort_by_confidence_level(reverse=True)
            partners = sorted_leads.mapped('partner_id')
            if not partners:
                main_lead = self.lead_ids[0]
                main_lead._handle_partner_assignment(create_missing=True)
                self.partner_id = main_lead.partner_id.id
            return True
        return check

    def _inactive_visitors_domain(self):
        """ Visitors tied to leads are considered always active and should not be deleted. """
        return super()._inactive_visitors_domain() & Domain('lead_ids', '=', False)

    def _merge_visitor(self, target):
        """ Link the leads to the main visitor to avoid them being lost. """
        if self.lead_ids:
            target.write({
                'lead_ids': [(4, lead.id) for lead in self.lead_ids]
            })

        return super()._merge_visitor(target)

    def _prepare_message_composer_context(self):
        if not self.partner_id and self.lead_ids:
            sorted_leads = self.lead_ids._sort_by_confidence_level(reverse=True)
            lead_partners = sorted_leads.mapped('partner_id')
            partner = lead_partners[0] if lead_partners else False
            if partner:
                return {
                    'default_model': 'crm.lead',
                    'default_res_id': sorted_leads[0].id,
                    'default_partner_ids': partner.ids,
                }
        return super(WebsiteVisitor, self)._prepare_message_composer_context()
