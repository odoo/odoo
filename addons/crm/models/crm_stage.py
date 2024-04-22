# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models

AVAILABLE_PRIORITIES = [
    ('0', 'Low'),
    ('1', 'Medium'),
    ('2', 'High'),
    ('3', 'Very High'),
]


class Stage(models.Model):
    """ Model for case stages. This models the main stages of a document
        management flow. Main CRM objects (leads, opportunities, project
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = "crm.stage"
    _description = "CRM Stages"
    _rec_name = 'name'
    _order = "sequence, name, id"

    @api.model
    def default_get(self, fields):
        """ As we have lots of default_team_id in context used to filter out
        leads and opportunities, we pop this key from default of stage creation.
        Otherwise stage will be created for a given team only which is not the
        standard behavior of stages. """
        if 'default_team_id' in self.env.context:
            ctx = dict(self.env.context)
            ctx.pop('default_team_id')
            self = self.with_context(ctx)
        return super(Stage, self).default_get(fields)

    name = fields.Char('Stage Name', required=True, translate=True)
    # Default needs to be high in order to have them set as end stage before computing frequencies when setting actual sequence.
    # Otherwise it starts low, frequencies are updated accordingly (almost max lost_count), then updated to max sequence -> all below stage
    sequence = fields.Integer('Sequence', default=1000, help="Used to order stages. Lower is better.")
    is_won = fields.Boolean('Is Won Stage?')
    requirements = fields.Text('Requirements', help="Enter here the internal requirements for this stage (ex: Offer sent to customer). It will appear as a tooltip over the stage's name.")
    team_id = fields.Many2one('crm.team', string='Sales Team', ondelete="set null",
        help='Specific team that uses this stage. Other teams will not be able to see or use this stage.')
    fold = fields.Boolean('Folded in Pipeline',
        help='This stage is folded in the kanban view when there are no records in that stage to display.')
    # This field for interface only
    team_count = fields.Integer('team_count', compute='_compute_team_count')

    @api.depends('team_id')
    def _compute_team_count(self):
        self.team_count = self.env['crm.team'].search_count([])

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    def write(self, vals):
        """ Since leads that are in a won stage must have their
        probability = 100%, this override ensures that setting a stage as won
        will set all the leads in that stage to probability = 100%.
        Inversely, if a won stage is not marked as won anymore, the lead
        probability should be recomputed based on automated probability.
        Note: If a user sets a stage as won and changes his mind right after,
        the manual probability will be lost in the process."""
        # Process frequency updates one write at a time
        for stage in self:
            stages_before = self.search([])
            super(Stage, stage).write(vals)
            stages_after = self.search([])

            # Do this separately of 'is_won' to avoid increased complexity
            if 'sequence' in vals and not self.env.context.get('install_mode') and stages_before.ids != stages_after.ids:
                print(f"ORDER {stages_before}\n To   {stages_after} \n")
                stage._update_stage_frequencies(stages_before, stages_after)

        # Both will create pending updates. For lost, as probas will not take into account new frequencies,
        # either we just compute, or we compute (will trigger process) + process + compute (more expensive)
        if 'is_won' in vals:
            won_leads = self.env['crm.lead'].search([('stage_id', 'in', self.ids)])
            if won_leads and vals.get('is_won'):
                won_leads.write({'probability': 100, 'automated_probability': 100})
            elif won_leads and not vals.get('is_won'):
                won_leads._compute_probabilities()
        return True

    def unlink(self):
        res = super().unlink()
        self.env['crm.lead.scoring.frequency'].sudo().search([
            ('variable', '=', 'stage_id'),
            ('value', 'in', [str(id) for id in self.ids])
        ]).unlink()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if not self.env.context.get('install_mode') and 'sequence' in [key for vals in vals_list for key in vals]:
            stages = self.search([])
            stages_with_index = [(index, stage) for index, stage in enumerate(stages) if stage in res]
            frequencies_per_team = self.env['crm.lead.scoring.frequency'].search([('variable', '=', 'stage_id')]).grouped("team_id")

            frequencies_vals = []
            for i, new_stage in stages_with_index:
                for team, frequencies in frequencies_per_team.items():
                    team_stages = frequencies.mapped('value')
                    if next_stage := next((stage for stage in stages[i+1:].filtered(lambda stage: str(stage.id) in team_stages)), False):
                        next_frequency = frequencies.filtered(lambda frequency: frequency.value == str(next_stage.id))
                        frequencies_vals.append(self._get_freq_create_vals(
                            next_frequency.lost_count, team.id, str(new_stage.id), 'stage_id', next_frequency.won_count
                        ))
            self.env['crm.lead.scoring.frequency'].sudo().create(frequencies_vals)
        return res

    def _update_stage_frequencies(self, stages_before, stages_after):
        self.ensure_one()
        index_before = stages_before.ids.index(self.id)
        index_after = stages_after.ids.index(self.id)
        if index_before == index_after or len(stages_after) != len(stages_before):
            return
        # Sudo!
        freqs_per_team = self.env['crm.lead.scoring.frequency'].sudo().search([('variable', '=', 'stage_id')]).grouped("team_id")
        freq_vals = []

        for team, freqs in freqs_per_team.items():
            lost_count_at_moved_stage = 0
            # Moving up in sequence
            if index_before < index_after:
                if f_moved_stage := self._get_stage_freq(freqs, self.id):
                    f_next_stage_before = self._get_stage_freq(freqs, stages_before[index_before + 1].id)
                    lost_count_at_moved_stage = max(0, round(f_moved_stage.lost_count - max(0.1, f_next_stage_before.lost_count)))

                    next_lost_count_after = 0
                    if self.id != stages_after[-1].id:
                        f_next_stage_after = self._get_stage_freq(freqs, stages_after[index_after + 1].id)
                        next_lost_count_after = f_next_stage_after.lost_count  # f may not exist for the team -> 0

                    # Update moved stage
                    f_moved_stage.lost_count = lost_count_at_moved_stage + max(0.1, next_lost_count_after)

                    if lost_count_at_moved_stage > 0:
                        stages_to_update = stages_after[index_before:index_after]
                        max_lost_count = f_moved_stage.lost_count
                        # Do in reverse
                        for stage in stages_to_update[::-1]:
                            if f_jumped_stage := self._get_stage_freq(freqs, stage.id):
                                # Update existing frequencies
                                f_jumped_stage.lost_count += lost_count_at_moved_stage
                                max_lost_count = max(max_lost_count, f_jumped_stage.lost_count)
                                continue
                            # Create missing frequencies
                            freq_vals.append(self._get_freq_create_vals(
                                max_lost_count, team.id, str(stage.id), 'stage_id', f_moved_stage.won_count
                            ))
            # Moving back in sequence
            else:
                next_lost_count_before = 0
                if self.id != stages_before[-1].id:
                    f_next_stage_before = self._get_stage_freq(freqs, stages_before[index_before + 1].id)
                    next_lost_count_before = f_next_stage_before.lost_count # f may not exist for the team -> 0

                if f_moved_stage := self._get_stage_freq(freqs, self.id):
                    lost_count_at_moved_stage = max(0, round(f_moved_stage.lost_count - max(0.1, next_lost_count_before)))
                    stages_to_update = stages_before[index_after:index_before]
                    # Decrease existing jumped frequencies by the lost count of moved stage
                    if lost_count_at_moved_stage > 0:
                        for stage in stages_to_update:
                            if f_jumped_stage := self._get_stage_freq(freqs, stage.id):
                                f_jumped_stage.lost_count -= lost_count_at_moved_stage

                # If there is a stage after in sequence after the update, use it to set lost_count
                # next() ? probably not needed (would have to update missing stages again?)
                if f_next_stage_after := self._get_stage_freq(freqs, stages_after[index_after + 1].id):
                    moved_stage_lost_count = f_next_stage_after.lost_count + lost_count_at_moved_stage
                    if f_moved_stage:
                        f_moved_stage.lost_count = moved_stage_lost_count
                    else:
                        # Create missing frequency
                        freq_vals.append(self._get_freq_create_vals(
                           moved_stage_lost_count, team.id, str(self.id), 'stage_id', f_next_stage_after.won_count
                        ))

        return self.env['crm.lead.scoring.frequency'].sudo().create(freq_vals)

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    @staticmethod
    def _get_freq_create_vals(lost_count, team_id, value, variable, won_count):
        return {
            'lost_count': lost_count,
            'team_id': team_id,
            'value': value,
            'variable': variable,
            'won_count': won_count,
        }

    @staticmethod
    def _get_stage_freq(frequencies, stage_id):
        return frequencies.filtered(lambda f: f.value == str(stage_id))
