# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
                visitor = next((visitor for visitor in visitors if visitor.current_lang_id), False)
                if not lead.lang_id and visitor.current_lang_id and visitor.website_id.language_count > 1:
                    lead.lang_id = visitor.current_lang_id

        return leads
