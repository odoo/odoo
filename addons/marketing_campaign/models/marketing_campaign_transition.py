# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import base64
import itertools
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from traceback import format_exception
from sys import exc_info
from openerp.tools.safe_eval import safe_eval as eval
import re
from openerp.addons.decimal_precision import decimal_precision as dp

from openerp import api
from openerp.osv import fields, osv
from openerp.report import render_report
from openerp.tools.translate import _
from openerp.exceptions import UserError

_intervalTypes = {
    'hours': lambda interval: relativedelta(hours=interval),
    'days': lambda interval: relativedelta(days=interval),
    'months': lambda interval: relativedelta(months=interval),
    'years': lambda interval: relativedelta(years=interval),
}

DT_FMT = '%Y-%m-%d %H:%M:%S'


class marketing_campaign_transition(osv.osv):
    _name = "marketing.campaign.transition"
    _description = "Campaign Transition"

    _interval_units = [
        ('hours', 'Hour(s)'),
        ('days', 'Day(s)'),
        ('months', 'Month(s)'),
        ('years', 'Year(s)'),
    ]

    def _get_name(self, cr, uid, ids, fn, args, context=None):
        # name formatters that depend on trigger
        formatters = {
            'auto': _('Automatic transition'),
            'time': _('After %(interval_nbr)d %(interval_type)s'),
            'cosmetic': _('Cosmetic'),
        }
        # get the translations of the values of selection field 'interval_type'
        fields = self.fields_get(cr, uid, ['interval_type'], context=context)
        interval_type_selection = dict(fields['interval_type']['selection'])

        result = dict.fromkeys(ids, False)
        for trans in self.browse(cr, uid, ids, context=context):
            values = {
                'interval_nbr': trans.interval_nbr,
                'interval_type': interval_type_selection.get(trans.interval_type, ''),
            }
            result[trans.id] = formatters[trans.trigger] % values
        return result


    def _delta(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        transition = self.browse(cr, uid, ids[0], context=context)
        if transition.trigger != 'time':
            raise ValueError('Delta is only relevant for timed transition.')
        return relativedelta(**{str(transition.interval_type): transition.interval_nbr})


    _columns = {
        'name': fields.function(_get_name, string='Name',
                                type='char', size=128),
        'activity_from_id': fields.many2one('marketing.campaign.activity',
                                            'Previous Activity', select=1,
                                            required=True, ondelete="cascade"),
        'activity_to_id': fields.many2one('marketing.campaign.activity',
                                          'Next Activity',
                                          required=True, ondelete="cascade"),
        'interval_nbr': fields.integer('Interval Value', required=True),
        'interval_type': fields.selection(_interval_units, 'Interval Unit',
                                          required=True),

        'trigger': fields.selection([('auto', 'Automatic'),
                                     ('time', 'Time'),
                                     ('cosmetic', 'Cosmetic'),  # fake plastic transition
                                    ],
                                    'Trigger', required=True,
                                    help="How is the destination workitem triggered"),
    }

    _defaults = {
        'interval_nbr': 1,
        'interval_type': 'days',
        'trigger': 'time',
    }
    def _check_campaign(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.activity_from_id.campaign_id != obj.activity_to_id.campaign_id:
                return False
        return True

    _constraints = [
            (_check_campaign, 'The To/From Activity of transition must be of the same Campaign ', ['activity_from_id,activity_to_id']),
        ]

    _sql_constraints = [
        ('interval_positive', 'CHECK(interval_nbr >= 0)', 'The interval must be positive or zero')
    ]