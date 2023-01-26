# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.iap.tools import iap_tools


class CrmLead(models.Model):
    """ Add a new field for searching duplicates on emails, improve lead duplicates
    computation to be more efficient. """
    _name = 'crm.lead'
    _inherit = 'crm.lead'

    email_domain_criterion = fields.Char(
        string='Email Domain Criterion',
        compute="_compute_email_domain_criterion",
        store=True,
        index='btree',  # used for exact match
    )

    @api.depends('email_normalized')
    def _compute_email_domain_criterion(self):
        self.email_domain_criterion = False
        for lead in self.filtered('email_normalized'):
            lead.email_domain_criterion = iap_tools.mail_prepare_for_domain_search(
                lead.email_normalized
            )

    @api.depends('email_domain_criterion', 'email_normalized', 'partner_id',
                 'phone_sanitized')
    def _compute_potential_lead_duplicates(self):
        """ Override potential lead duplicates computation to be more efficient
        with high lead volume.

        Criterions:
          * email domain exact match;
          * phone_sanitized exact match;
          * same commercial entity;
        """
        SEARCH_RESULT_LIMIT = 21

        def return_if_relevant(model_name, domain):
            """ Returns the recordset obtained by performing a search on the provided
            model with the provided domain if the cardinality of that recordset is
            below a given threshold (i.e: `SEARCH_RESULT_LIMIT`). Otherwise, returns
            an empty recordset of the provided model as it indicates search term
            was not relevant.

            Note: The function will use the administrator privileges to guarantee
            that a maximum amount of leads will be included in the search results
            and transcend multi-company record rules. It also includes archived
            records. Idea is that counter indicates duplicates are present and
            the lead could be escalated to managers.
            """
            model = self.env[model_name].sudo().with_context(active_test=False)
            res = model.search(domain, limit=SEARCH_RESULT_LIMIT)
            return res if len(res) < SEARCH_RESULT_LIMIT else model

        for lead in self:
            lead_id = lead._origin.id if isinstance(lead.id, models.NewId) else lead.id
            common_lead_domain = [
                ('id', '!=', lead_id)
            ]

            duplicate_lead_ids = self.env['crm.lead']

            # check the "company" email domain duplicates
            if lead.email_domain_criterion:
                duplicate_lead_ids |= return_if_relevant('crm.lead', common_lead_domain + [
                    ('email_domain_criterion', '=', lead.email_domain_criterion)
                ])
            # check for "same commercial entity" duplicates
            if lead.partner_id and lead.partner_id.commercial_partner_id:
                duplicate_lead_ids |= lead.with_context(active_test=False).search(common_lead_domain + [
                    ("partner_id", "child_of", lead.partner_id.commercial_partner_id.id)
                ])
            # check the phone number duplicates, based on phone_sanitized. Only
            # exact matches are found, and the single one stored in phone_sanitized
            # in case phone and mobile are both set.
            if lead.phone_sanitized:
                duplicate_lead_ids |= return_if_relevant('crm.lead', common_lead_domain + [
                    ('phone_sanitized', '=', lead.phone_sanitized)
                ])

            lead.duplicate_lead_ids = duplicate_lead_ids + lead
            lead.duplicate_lead_count = len(duplicate_lead_ids)
