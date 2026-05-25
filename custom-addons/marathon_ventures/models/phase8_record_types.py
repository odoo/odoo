# -*- coding: utf-8 -*-
"""Phase 8 — SF Record Types as `sf_record_type` Selection fields.

SF objects with multiple Record Types need their DeveloperName preserved so the
business logic (per-record-type validation rules, layouts, etc.) can be wired up
later. We add `sf_record_type` Selection fields on the affected models with the
exact SF DeveloperNames as keys and SF labels as display strings.

Objects covered here:
  * Deal__c        → mv.deal           — 4 types (Bundle / Digital / Paid Programming / Short Form)
  * Schedules__c   → mv.schedules      — 4 types (Bundle / Digital / Paid Programming / Short Form)
  * Task           → mail.activity     — 5 types (TODO: add when needed)
  * Contact        → res.partner       — 4 types (TODO)
  * Credit_App     → mv.credit_app     — 2 types (TODO)
  * Contracts__c   → mv.contracts      — 1 type (TODO)
  * PrelogFuzzy    → mv.prelog_fuzzy   — 1 type (TODO)
  * Time_and_Exp   → mv.time_and_exp   — 1 type (TODO)
"""
from odoo import models, fields


# DealRecord types and DealsRecord schedule record types — both share the same 4 types.
DEAL_RECORD_TYPES = [
    ('Bundle',           'Bundle'),
    ('Digital',          'Digital'),
    ('Paid_Programming', 'Paid Programming'),
    ('Short_Form',       'Short Form'),
]


class MvDealRecordType(models.Model):
    _name = 'mv.deal'
    _inherit = 'mv.deal'

    sf_record_type = fields.Selection(
        selection=DEAL_RECORD_TYPES,
        string='Record Type',
        default='Short_Form',
        help='SF Deal Record Type — drives downstream behavior (paid-programming has Long Form length restrictions, etc.).',
    )


class MvSchedulesRecordType(models.Model):
    _name = 'mv.schedules'
    _inherit = 'mv.schedules'

    sf_record_type = fields.Selection(
        selection=DEAL_RECORD_TYPES,  # same 4 types as Deal
        string='Record Type',
        default='Short_Form',
        help='SF Schedule Record Type — must match the parent Deal\'s Record Type.',
    )
