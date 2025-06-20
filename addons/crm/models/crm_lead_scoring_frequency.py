# -*- coding: utf-8 -*-
from random import randint

from odoo import api, fields, models


class CrmLeadScoringFrequency(models.Model):
    _name = 'crm.lead.scoring.frequency'
    _description = 'Lead Scoring Frequency'

    variable = fields.Char('Variable', index=True)
    value = fields.Char('Value')
    won_count = fields.Float('Won Count', digits=(16, 1))  # Float because we add 0.1 to avoid zero Frequency issue
    lost_count = fields.Float('Lost Count', digits=(16, 1))  # Float because we add 0.1 to avoid zero Frequency issue
    team_id = fields.Many2one('crm.team', 'Sales Team', ondelete="cascade")


class CrmLeadScoringFrequencyField(models.Model):
    _name = 'crm.lead.scoring.frequency.field'
    _description = 'Fields that can be used for predictive lead scoring computation'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(related="field_id.field_description")
    field_id = fields.Many2one(
        'ir.model.fields', domain=[('model_id.model', '=', 'crm.lead')], required=True,
        ondelete='cascade',
    )
    color = fields.Integer('Color', default=_get_default_color)


class CrmLeadScoringPendingUpdate(models.Model):
    _name = 'crm.lead.scoring.pending.update'
    _description = 'Lead Scoring Pending Update'
    _order = 'create_date ASC, id'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete="cascade")
    from_lost = fields.Boolean('From Lost', required=True)
    from_won = fields.Boolean('From Won', required=True)
    to_lost = fields.Boolean('To Lost', required=True)
    to_won = fields.Boolean('To Won', required=True)

    @api.model
    def _extract_state_change_per_lead(self):
        """ As a lead could change of won_status more than once in between the CRON running, we can
            use this method to return the net won_status update per lead for the full table, as well
            as the ids of records in table crm.lead.scoring.pending.update, to be deleted once they
            have been correctly processed. """
        state_change_per_lead = {}
        pending_update_ids = []
        pending_updates_per_lead = self._read_group(
            domain=[],
            groupby=['lead_id'],
            aggregates=[
                'from_lost:array_agg',
                'from_won:array_agg',
                'to_lost:array_agg',
                'to_won:array_agg',
                'id:array_agg'
            ]
        )
        for lead, from_lost, from_won, to_lost, to_won, ids in pending_updates_per_lead:
            from_state = 'lost' if from_lost[0] else 'won' if from_won[0] else 'pending'
            to_state = 'lost' if to_lost[-1] else 'won' if to_won[-1] else 'pending'
            if from_state != to_state:
                state_change_per_lead[lead.id] = {
                    'from_state': from_state,
                    'to_state': to_state,
                }
            pending_update_ids += ids
        return state_change_per_lead, pending_update_ids
