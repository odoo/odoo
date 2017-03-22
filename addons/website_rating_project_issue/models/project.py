# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Project(models.Model):

    _name = "project.project"
    _inherit = ['project.project', 'website.published.mixin']

    @api.multi
    def action_view_all_rating(self):
        """ Override this method without calling parent to redirect to rating website project page """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Redirect to the Website Projcet Rating Page",
            'target': 'self',
            'url': "/project/rating/%s" % (self.id,)
        }

    @api.multi
    def _compute_website_url(self):
        super(Project, self)._compute_website_url()
        for project in self:
            project.website_url = "/project/rating/%s" % project.id


class ProjectTask(models.AbstractModel):
    _name = 'project.rating'

    def _get_partner_rating(self, table, model, project_id, limit=None):
        self.env.cr.execute("""
            SELECT
                RATING.rated_partner_id,
                array_agg(rating) as rating,
                array_agg(RATING.id) as rating_ids,
                CASE
                    WHEN now()::date - RATING.create_date::date BETWEEN 0 AND 6 Then 'week'
                    WHEN now()::date - RATING.create_date::date BETWEEN 0 AND 15 Then '15 days'
                    WHEN now()::date - RATING.create_date::date BETWEEN 0 AND 30  Then '1 month'
                    WHEN now()::date - RATING.create_date::date BETWEEN 0 AND 90  Then '3 month'
                END AS days
            FROM
                rating_rating as RATING
            LEFT JOIN
                %s as TASK ON RATING.res_id = TASK.id
            WHERE
                RATING.res_model = '%s' AND RATING.rated_partner_id IS NOT NULL AND RATING.create_date >= current_date - interval '90' day AND TASK.project_id = %s AND RATING.rating IN (1,5,10)
            GROUP BY
                RATING.rated_partner_id, days, RATING.write_date
            ORDER BY RATING.write_date desc
        """ % (table, model, project_id))

        all_record = self.env.cr.dictfetchall()
        rating_ids = []
        partner_ids = map(lambda x: x['rated_partner_id'], all_record)
        partner_ratings = [{
            'rated_partner_id': self.env['res.partner'].sudo().browse(rated_partner_id),
            'week': {'happy': 0, 'avg': 0, 'unhappy': 0, 'total': 0},
            '15 days': {'happy': 0, 'avg': 0, 'unhappy': 0, 'total': 0},
            '1 month': {'happy': 0, 'avg': 0, 'unhappy': 0, 'total': 0},
            '3 month': {'happy': 0, 'avg': 0, 'unhappy': 0, 'total': 0},
        } for rated_partner_id in set(partner_ids)]

        def increment_rating(partner, days, rating):
            if rating == 10:
                partner[days]['happy'] += 1
            if rating == 5:
                partner[days]['avg'] += 1
            if rating == 1:
                partner[days]['unhappy'] += 1
            partner[days]['total'] += 1

        for record in all_record:
            partner = filter(lambda x: x['rated_partner_id'].id == record['rated_partner_id'], partner_ratings)[0]
            if record['days'] == 'week':
                for rating in record['rating']:
                    increment_rating(partner, '15 days', rating)
                    increment_rating(partner, '1 month', rating)
                    increment_rating(partner, '3 month', rating)
            if record['days'] == '15 days':
                for rating in record['rating']:
                    increment_rating(partner, '1 month', rating)
                    increment_rating(partner, '3 month', rating)
            if record['days'] == '1 month':
                for rating in record['rating']:
                    increment_rating(partner, '3 month', rating)

        for record in all_record:
            rating_ids += record['rating_ids']
            partner = filter(lambda x: x['rated_partner_id'].id == record['rated_partner_id'], partner_ratings)[0]
            for rating in record['rating']:
                increment_rating(partner, record['days'], rating)

        statistic = {
            'week': {'avg': 0, 'happy': 0, 'unhappy': 0, 'total': 0},
            '1 month': {'avg': 0, 'happy': 0, 'unhappy': 0, 'total': 0},
            '3 month': {'avg': 0, 'happy': 0, 'unhappy': 0, 'total': 0},
        }
        days = ['week', '1 month', '3 month']
        ratings = ['avg', 'happy', 'unhappy']
        matrix = [(x, y) for x in days for y in ratings]
        for partner in partner_ratings:
            for day, rating in matrix:
                statistic[day][rating] += partner[day][rating]
                statistic[day]['total'] += partner[day][rating]
        for day, rating in matrix:
            total = statistic[day]['total']
            percentage = 'percentage_%s' % rating
            statistic[day][percentage] = total and "%.1f" % ((statistic[day][rating] * 100 / float(total))) or 0.0

        partner_ratings = sorted(partner_ratings, key=lambda k: k['15 days']['total'], reverse=True)[:5]
        for rating in partner_ratings:
            ratring = rating['15 days']
            total = ratring['happy'] * 100 + ratring['avg'] * 50
            rating['15 days']['%'] = total and total/ratring['total'] or 0

        return {
            'partner_rating': partner_ratings,
            'statistic': statistic,
            # we could not pass limit in query because we need all rating up to
            # last three months so limit apply here
            'ratings': self.env['rating.rating'].sudo().browse(rating_ids)[:limit]
        }
