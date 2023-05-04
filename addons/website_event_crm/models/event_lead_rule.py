from odoo import models


class EventLeadRule(models.Model):

    _inherit = "event.lead.rule"

    def _run_on_registrations(self, registrations):
        leads = super()._run_on_registrations(registrations)
        if len(self.env['res.lang'].get_installed()) < 2:
            return leads

        for lead in leads:
            # When a lead has several registrations, they should all relate to the same visitor
            visitors = lead.registration_ids.visitor_id
            if visitors:
                lead.visitor_ids = visitors
                if not lead.lang_id and visitors.lang_id and visitors[0].website_id.language_count > 1:
                    lead.lang_id = visitors.lang_id[0]

        return leads
