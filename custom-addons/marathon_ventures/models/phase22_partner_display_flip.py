# -*- coding: utf-8 -*-
"""Marathon Ventures overrides on res.partner.

Two independent tweaks, combined into one class since they both
just inherit res.partner:

1. Contact-first display order (opt-in via context flag)
   -------------------------------------------------------
   Odoo's default res.partner._compute_display_name renders
   "Account Name, Contact Name". On the Deal form's contact
   lookup users need to scan by contact name first, so any m2o
   field that sets `context="{'partner_display_contact_first': True}"`
   gets the reversed order: "Contact Name, Account Name". Other
   partner displays (invoices, emails, mail-thread, ...) keep
   Odoo's default.

2. Disable Odoo's Partner Autocomplete web suggestions
   ------------------------------------------------------
   Odoo's built-in partner_autocomplete module hooks into
   res.partner._get_view and stamps `widget="field_partner_autocomplete"`
   onto the name/vat/duns fields, which pulls suggestions from an
   IAP web service. Marathon Ventures deliberately does NOT want
   those - an operator could accidentally pick a similarly-named
   agency from the web instead of the one already in the DB.
   We call super() so partner_autocomplete's stamp is applied,
   then strip the widget back off before the arch reaches the
   client. The IAP module itself stays installed for any other
   programmatic use.
"""
from odoo import models, api


class ResPartnerMvOverrides(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    # ------------------------------------------------------------------
    # 1. Contact-first display swap
    # ------------------------------------------------------------------
    @api.depends_context('partner_display_contact_first')
    def _compute_display_name(self):
        """Fire the reversed order only when the context flag is on;
        every other path falls back to Odoo's default compute."""
        if self.env.context.get('partner_display_contact_first'):
            for partner in self:
                name = (partner.name or '').strip()
                # commercial_company_name is Odoo's own "effective
                # parent company" field - matches whatever the default
                # compute would have used for its "Account Name" part.
                company = (partner.commercial_company_name or '').strip()
                if company and name and company != name:
                    partner.display_name = '%s, %s' % (name, company)
                else:
                    partner.display_name = name or company or ''
        else:
            return super()._compute_display_name()

    # ------------------------------------------------------------------
    # 2. Strip web-autocomplete widget from partner forms
    # ------------------------------------------------------------------
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form' and arch is not None:
            try:
                for node in arch.xpath(
                    "//field[@name='name' or @name='vat' or @name='duns']"
                ):
                    if node.get('widget') == 'field_partner_autocomplete':
                        node.attrib.pop('widget', None)
            except Exception:
                # Never let view-strip fail the form load. Worst case:
                # widget stays and users see the web suggestions again.
                pass
        return arch, view
