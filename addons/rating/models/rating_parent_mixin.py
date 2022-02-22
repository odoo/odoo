# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import operator

from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models
from odoo.addons.rating.models.rating import RATING_LIMIT_OK, RATING_LIMIT_MIN
from odoo.addons.rating.models.rating_mixin import OPERATOR_MAPPING
from odoo.osv import expression
from odoo.tools.float_utils import float_compare


class RatingParentMixin(models.AbstractModel):
    _name = 'rating.parent.mixin'
    _description = "Rating Parent Mixin"
    _rating_satisfaction_days = False  # Number of last days used to compute parent satisfaction. Set to False to include all existing rating.

    rating_ids = fields.One2many(
        'rating.rating', 'parent_res_id', string='Ratings',
        auto_join=True, groups='base.group_user',
        domain=lambda self: [('parent_res_model', '=', self._name)])
    rating_percentage_satisfaction = fields.Integer(
        "Rating Satisfaction",
        compute="_compute_rating_percentage_satisfaction", compute_sudo=True,
        store=False, help="Percentage of happy ratings")
    rating_count = fields.Integer(string='# Ratings', compute="_compute_rating_percentage_satisfaction", compute_sudo=True)
    rating_avg = fields.Float('Average Rating', groups='base.group_user',
        compute='_compute_rating_percentage_satisfaction', compute_sudo=True, search='_search_rating_avg')
    rating_avg_percentage = fields.Float('Average Rating (%)', groups='base.group_user',
        compute='_compute_rating_percentage_satisfaction', compute_sudo=True)
    rating_last_value = fields.Float('Rating Last Value', groups='base.group_user', related='rating_ids.rating')

    @api.depends('rating_ids.rating', 'rating_ids.consumed')
    def _compute_rating_percentage_satisfaction(self):
        # build domain and fetch data
        domain = [('parent_res_model', '=', self._name), ('parent_res_id', 'in', self.ids), ('rating', '>=', RATING_LIMIT_MIN), ('consumed', '=', True)]
        if self._rating_satisfaction_days:
            domain += [('write_date', '>=', fields.Datetime.to_string(fields.datetime.now() - timedelta(days=self._rating_satisfaction_days)))]
        data = self.env['rating.rating'].read_group(domain, ['parent_res_id', 'rating'], ['parent_res_id', 'rating'], lazy=False)

        # get repartition of grades per parent id
        default_grades = {'great': 0, 'okay': 0, 'bad': 0}
        grades_per_parent = dict((parent_id, dict(default_grades)) for parent_id in self.ids)  # map: {parent_id: {'great': 0, 'bad': 0, 'ok': 0}}
        rating_scores_per_parent = defaultdict(int)  # contains the total of the rating values per record
        for item in data:
            parent_id = item['parent_res_id']
            rating = item['rating']
            if rating > RATING_LIMIT_OK:
                grades_per_parent[parent_id]['great'] += item['__count']
            elif rating > RATING_LIMIT_MIN:
                grades_per_parent[parent_id]['okay'] += item['__count']
            else:
                grades_per_parent[parent_id]['bad'] += item['__count']
            rating_scores_per_parent[parent_id] += rating * item['__count']

        # compute percentage per parent
        for record in self:
            repartition = grades_per_parent.get(record.id, default_grades)
            rating_count = sum(repartition.values())
            record.rating_count = rating_count
            record.rating_percentage_satisfaction = repartition['great'] * 100 / rating_count if rating_count else -1
            record.rating_avg = rating_scores_per_parent[record.id] / rating_count if rating_count else 0
            record.rating_avg_percentage = record.rating_avg / 5

    def _search_rating_avg(self, operator, value):
        if operator not in OPERATOR_MAPPING:
            raise NotImplementedError('This operator %s is not supported in this search method.' % operator)
        domain = [('parent_res_model', '=', self._name), ('consumed', '=', True), ('rating', '>=', RATING_LIMIT_MIN)]
        if self._rating_satisfaction_days:
            min_date = fields.datetime.now() - timedelta(days=self._rating_satisfaction_days)
            domain = expression.AND([domain, [('write_date', '>=', fields.Datetime.to_string(min_date))]])
        rating_read_group = self.env['rating.rating'].sudo().read_group(domain, ['parent_res_id', 'rating_avg:avg(rating)'], ['parent_res_id'])
        parent_res_ids = [
            res['parent_res_id']
            for res in rating_read_group
            if OPERATOR_MAPPING[operator](float_compare(res['rating_avg'], value, 2), 0)
        ]
        return [('id', 'in', parent_res_ids)]
