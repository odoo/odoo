from odoo import api, fields, models


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    best_profile_id = fields.Many2one(
        'job.match.profile', string='Best Job Match',
        compute='_compute_best_profile_id', store=True,
        help="Job profile that best matches this submission's answers.")

    @api.depends('user_input_line_ids.suggested_answer_id', 'state', 'survey_id.is_job_match')
    def _compute_best_profile_id(self):
        for user_input in self:
            results = user_input._get_job_match_results()
            user_input.best_profile_id = results[0]['profile'] if results else False

    def _get_job_match_results(self):
        """ Compute the score per job profile for this submission.

        :return: a list of dicts sorted by descending score::

            [{'profile': <job.match.profile>, 'score': int, 'max': int, 'percentage': int}, ...]

        Returns an empty list for surveys that are not job-matching games.
        The percentage is the score relative to the maximum points obtainable
        for that profile, clamped to the 0-100 range (the "match meter" value).
        """
        self.ensure_one()
        if not self.survey_id.is_job_match:
            return []

        # All profiles that are weighted anywhere in this survey.
        survey_answers = self.survey_id.question_ids.suggested_answer_ids
        profiles = survey_answers.match_weight_ids.profile_id
        if not profiles:
            return []

        # Answers actually chosen by the participant (single/multiple choice).
        chosen_answers = self.user_input_line_ids.filtered(
            lambda line: line.answer_type == 'suggestion' and line.suggested_answer_id
        ).suggested_answer_id
        chosen_weights = chosen_answers.match_weight_ids

        # Hard requirements: a chosen answer flagged as eliminating removes the
        # profile from the results entirely, regardless of points.
        disqualified = chosen_weights.filtered('is_eliminating').profile_id

        scores = dict.fromkeys(profiles.ids, 0)
        for weight in chosen_weights:
            if not weight.is_eliminating:
                scores[weight.profile_id.id] += weight.points

        # Maximum obtainable per profile: the best answer per question toward
        # that profile (sum of positives for multi-select, best single otherwise).
        max_scores = dict.fromkeys(profiles.ids, 0)
        for question in self.survey_id.question_ids:
            question_weights = question.suggested_answer_ids.match_weight_ids.filtered(
                lambda w: not w.is_eliminating)
            for profile in profiles:
                points = question_weights.filtered(
                    lambda w: w.profile_id == profile).mapped('points')
                positives = [p for p in points if p > 0]
                if not positives:
                    continue
                if question.question_type == 'multiple_choice':
                    max_scores[profile.id] += sum(positives)
                else:
                    max_scores[profile.id] += max(positives)

        results = []
        for profile in profiles:
            if profile in disqualified:
                continue
            score = scores[profile.id]
            maximum = max_scores[profile.id]
            percentage = round(100 * score / maximum) if maximum > 0 else 0
            results.append({
                'profile': profile,
                'score': score,
                'max': maximum,
                'percentage': max(0, min(100, percentage)),
            })
        results.sort(key=lambda r: (r['score'], r['percentage']), reverse=True)
        return results
