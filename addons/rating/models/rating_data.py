# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import operator

from odoo.tools.float_utils import float_compare

RATING_AVG_TOP = 3.66
RATING_AVG_OK = 2.33
RATING_AVG_MIN = 1

RATING_LIMIT_SATISFIED = 4
RATING_LIMIT_OK = 3
RATING_LIMIT_MIN = 1
RATING_TEXT = [
    ('top', 'Satisfied'),
    ('ok', 'Okay'),
    ('ko', 'Dissatisfied'),
    ('none', 'No Rating yet'),
]

OPERATOR_MAPPING = {
    '=': operator.eq,
    '!=': operator.ne,
    '<': operator.lt,
    '<=': operator.le,
    '>': operator.gt,
    '>=': operator.ge,
}

def _rating_avg_to_text(rating_avg):
    if float_compare(rating_avg, RATING_AVG_TOP, 2) >= 0:
        return 'top'
    if float_compare(rating_avg, RATING_AVG_OK, 2) >= 0:
        return 'ok'
    if float_compare(rating_avg, RATING_AVG_MIN, 2) >= 0:
        return 'ko'
    return 'none'

def _rating_assert_value(rating_value):
    assert 0 <= rating_value <= 5

def _rating_to_grade(rating_value):
    """ From a rating value give a text-based mean value. """
    _rating_assert_value(rating_value)
    if rating_value >= RATING_LIMIT_SATISFIED:
        return 'great'
    if rating_value >= RATING_LIMIT_OK:
        return 'okay'
    return 'bad'

def _rating_to_text(rating_value):
    """ From a rating value give a text-based mean value. """
    _rating_assert_value(rating_value)
    if rating_value >= RATING_LIMIT_SATISFIED:
        return 'top'
    if rating_value >= RATING_LIMIT_OK:
        return 'ok'
    if rating_value >= RATING_LIMIT_MIN:
        return 'ko'
    return 'none'

def _rating_to_threshold(rating_value):
    """ From a rating value, return the thresholds in form of 0-1-3-5 used
    notably for images. """
    _rating_assert_value(rating_value)
    if rating_value >= RATING_LIMIT_SATISFIED:
        return 5
    if rating_value >= RATING_LIMIT_OK:
        return 3
    if rating_value >= RATING_LIMIT_MIN:
        return 1
    return 0
