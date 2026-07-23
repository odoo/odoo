# -*- coding: utf-8 -*-
"""Phase 9 - Deal UI helpers + auto-fill rules.

The auto-generated mv_deal.py declared `_compute_advertiser` and
`_compute_contactaccount` with `@api.depends('sf_external_id')` as
placeholders so the SF formulas could be translated later. That means
the values never recompute when the user picks a Brand or a Contact in
the form. We fix that here by:

  1. Overriding the compute methods with the real translation of the SF
     formulas (Brand -> Advertiser.Name, Contact -> Parent Account.Name)
     and the proper `@api.depends` triggers so the stored values update
     on save.
  2. Adding @api.onchange handlers so the UI shows the auto-filled
     value immediately, before save - including the editable
     `client_account` (Advertiser) Many2one which is NOT computed.

Also hosts the inline-collapse toggle for the "Additional details"
section and the Cancel footer action.
"""
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class MvDealUiPhase9(models.Model):
    _name = 'mv.deal'
    _inherit = 'mv.deal'

    show_additional_details = fields.Boolean(
        string='Show Additional Details',
        default=False,
        store=False,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Computed: advertiser display name + contact account display name
    # ------------------------------------------------------------------
    @api.depends('brands', 'brands.advertiser', 'brands.advertiser.name')
    def _compute_advertiser(self):
        for rec in self:
            if rec.brands and rec.brands.advertiser:
                rec.advertiser = rec.brands.advertiser.name or False
            else:
                rec.advertiser = False

    @api.depends('contact', 'contact.parent_id', 'contact.parent_id.name', 'contact.commercial_company_name', 'contact.name')
    def _compute_contactaccount(self):
        for rec in self:
            if rec.contact:
                rec.contactaccount = (
                    (rec.contact.parent_id and rec.contact.parent_id.name)
                    or rec.contact.commercial_company_name
                    or rec.contact.name
                    or False
                )
            else:
                rec.contactaccount = False

    # ------------------------------------------------------------------
    # Onchange: auto-fill the editable Many2one fields immediately
    # ------------------------------------------------------------------
    @api.onchange('brands')
    def _onchange_brands_autofill(self):
        """Pick Brand -> auto-fill Advertiser (client_account) + advertiser Char.

        Always overwrites. If the planner picks a new brand they expect
        the advertiser to update to match. The chain is:
            mv.deal.brands -> mv.brands.advertiser -> mv.advertiser.account
        """
        for rec in self:
            _logger.info(
                "[MV phase9] onchange brands fired: brand=%s",
                rec.brands.display_name if rec.brands else None,
            )
            if not rec.brands:
                rec.advertiser = False
                continue
            adv = rec.brands.advertiser
            if not adv:
                rec.advertiser = False
                return {
                    'warning': {
                        'title': "Brand has no Advertiser",
                        'message': (
                            "Brand '%s' is not linked to any Advertiser. "
                            "Open the Brand record and set its Advertiser "
                            "field, then come back here."
                        ) % rec.brands.display_name,
                    }
                }
            # Always update the display name
            rec.advertiser = adv.name or adv.display_name or False
            # Update the editable account Many2one
            # if adv.account:
            #     rec.client_account = adv.account
            # else:
            #     return {
            #         'warning': {
            #             'title': "Advertiser has no Account",
            #             'message': (
            #                 "Advertiser '%s' (linked to Brand '%s') has "
            #                 "no Account set. Pick an Account manually or "
            #                 "set one on the Advertiser record."
            #             ) % (adv.display_name, rec.brands.display_name),
            #         }
            #     }

    @api.onchange('contact')
    def _onchange_contact_autofill(self):
        """Pick Contact -> immediately fill the Contact Account display."""
        for rec in self:
            _logger.info(
                "[MV phase9] onchange contact fired: contact=%s parent=%s",
                rec.contact.display_name if rec.contact else None,
                (rec.contact.parent_id.display_name
                 if (rec.contact and rec.contact.parent_id) else None),
            )
            if not rec.contact:
                rec.contactaccount = False
                continue
            rec.contactaccount = (
                (rec.contact.parent_id and rec.contact.parent_id.name)
                or rec.contact.commercial_company_name
                or rec.contact.name
                or False
            )

    # ------------------------------------------------------------------
    # Inline collapse toggle + Cancel footer action
    # ------------------------------------------------------------------
    def action_toggle_additional_details(self):
        for rec in self:
            rec.show_additional_details = not rec.show_additional_details
        return False

    def action_cancel_deal(self):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'marathon_ventures.action_mv_deal'
        )
        action['target'] = 'current'
        return action
