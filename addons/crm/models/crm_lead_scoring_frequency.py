# -*- coding: utf-8 -*-

import logging

from datetime import datetime

from odoo import fields, models

_logger = logging.getLogger(__name__)


class LeadScoringFrequency(models.Model):
    _name = 'crm.lead.scoring.frequency'
    _description = 'Lead Scoring Frequency'

    variable = fields.Char('Variable', index=True)
    value = fields.Char('Value')
    won_count = fields.Float('Won Count', digits=(16, 1))  # Float because we add 0.1 to avoid zero Frequency issue
    lost_count = fields.Float('Lost Count', digits=(16, 1))  # Float because we add 0.1 to avoid zero Frequency issue
    team_id = fields.Many2one('crm.team', 'Sales Team', ondelete="cascade")

class FrequencyField(models.Model):
    _name = 'crm.lead.scoring.frequency.field'
    _description = 'Fields that can be used for predictive lead scoring computation'

    name = fields.Char(related="field_id.field_description")
    field_id = fields.Many2one(
        'ir.model.fields', domain=[('model_id.model', '=', 'crm.lead')], required=True,
        ondelete='cascade',
    )

class LeadScoringPendingUpdate(models.Model):
    _name = 'crm.lead.scoring.pending.update'
    _description = 'Lead Scoring Pending Update'
    _order = 'create_date ASC'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete="cascade")
    to_state = fields.Selection([
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('other', 'Other')
    ], default='other', required=True)
    from_state = fields.Selection([
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('other', 'Other')
    ], default='other', required=True)

    def _cron_process_pls_pending_updates(self):
        """ CRON : Processes all the pending frequency updates and applies the corresponding
            frequency updates on the crm.lead.scoring.frequency table. The pending updates
            track the different status update of leads between states 'won', 'lost' and 'other'. """
        cron_start_date = datetime.now()
        self.env['crm.lead']._process_pls_pending_updates()
        _logger.info("Predictive Lead Scoring - Processing Pending Updates : Cron duration = %d seconds" % ((datetime.now() - cron_start_date).total_seconds()))

    def _extract_state_change_per_lead(self):
        """ Returns the net update per lead for the full the table, as well as the ids of records
            in table crm.lead.scoring.pending.update, to be deleted after processing them. """
        state_change_per_lead = {}
        pending_update_ids = []

        pending_updates_per_lead = self._read_group(
            domain=[],
            groupby=['lead_id'],
            aggregates=['from_state:array_agg', 'to_state:array_agg', 'id:array_agg']
        )  # The create_date order must be applied here to take net update below

        for lead, from_values, to_values, ids in pending_updates_per_lead:
            if from_values[0] != to_values[-1]:
                state_change_per_lead[lead.id] = {
                    'from_state': from_values[0],
                    'to_state': to_values[-1],
                }
            pending_update_ids += ids

        return state_change_per_lead, pending_update_ids
