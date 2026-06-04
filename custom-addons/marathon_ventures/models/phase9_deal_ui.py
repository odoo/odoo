# -*- coding: utf-8 -*-
"""Phase 9 — Deal UI helpers.

Adds a non-stored toggle (`show_additional_details`) used by the redesigned
Deal form to collapse / expand the "Additional details" block inline, the
way the mockup shows it (`▸ Additional details ...  collapsed by default`).
The default value is False so the section is collapsed on open; the user
flips it via a button in the form view.
"""
from odoo import models, fields


class MvDealUiPhase9(models.Model):
    _name = 'mv.deal'
    _inherit = 'mv.deal'

    # Pure UI flag — not stored. Default False = section collapsed.
    show_additional_details = fields.Boolean(
        string='Show Additional Details',
        default=False,
        store=False,
        copy=False,
        help='UI-only toggle for the Phase 9 redesigned Deal form. Controls '
             'whether the "Additional details" block is visible inline.',
    )

    def action_toggle_additional_details(self):
        """Flip the inline-collapse flag for the Additional Details section."""
        for rec in self:
            rec.show_additional_details = not rec.show_additional_details
        return False

    def action_cancel_deal(self):
        """Footer Cancel button.

        Navigates back to the Deal list. Any unsaved field edits on the
        current form trigger Odoo's standard "Discard changes?" prompt
        because the navigation leaves a dirty form.
        """
        action = self.env['ir.actions.act_window']._for_xml_id(
            'marathon_ventures.action_mv_deal'
        )
        action['target'] = 'current'
        return action
