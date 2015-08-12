# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_intervalTypes = {
    'hours': lambda interval: relativedelta(hours=interval),
    'days': lambda interval: relativedelta(days=interval),
    'months': lambda interval: relativedelta(months=interval),
    'years': lambda interval: relativedelta(years=interval),
}


class MarketingCampaignTransition(models.Model):
    _name = "marketing.campaign.transition"
    _description = "Campaign Transition"

    name = fields.Char(compute='_compute_get_name')
    activity_from_id = fields.Many2one(
        'marketing.campaign.activity', string='Previous Activity', index=1, required=True, ondelete="cascade")
    activity_to_id = fields.Many2one(
        'marketing.campaign.activity', string='Next Activity', required=True, ondelete="cascade")
    interval_nbr = fields.Integer(
        string='Interval Value', required=True, default=1)
    interval_type = fields.Selection([
                                    ('hours', 'Hour(s)'),
                                    ('days', 'Day(s)'),
                                    ('months', 'Month(s)'),
                                    ('years', 'Year(s)')], string='Interval Unit', required=True, default='days')
    trigger = fields.Selection([('auto', 'Automatic'),
                                ('time', 'Time'),
                                # fake plastic transition
                                ('cosmetic', 'Cosmetic'),
                                ], required=True, default='time', help="How is the destination workitem triggered")

    def _compute_get_name(self):
        # name formatters that depend on trigger
        formatters = {
            'auto': _('Automatic transition'),
            'time': _('After %(interval_nbr)d %(interval_type)s'),
            'cosmetic': _('Cosmetic'),
        }
        # get the translations of the values of selection field 'interval_type'
        fields = self.fields_get(['interval_type'])
        interval_type_selection = dict(fields['interval_type']['selection'])
        for trans in self:
            values = {
                'interval_nbr': trans.interval_nbr,
                'interval_type': interval_type_selection.get(trans.interval_type, ''),
            }
            trans.name = formatters[trans.trigger] % values

    def _delta(self):
        self.ensure_one()
        if self.trigger != 'time':
            raise ValidationError('Delta is only relevant for timed transition.')
        return relativedelta(**{str(self.interval_type): self.interval_nbr})

    @api.constrains('activity_from_id', 'activity_to_id')
    def _check_campaign(self):
        for transition in self:
            if transition.activity_from_id.campaign_id != transition.activity_to_id.campaign_id:
                raise ValidationError(
                _('The To/From Activity of transition must be of the same Campaign'))

    _sql_constraints = [
        ('interval_positive', 'CHECK(interval_nbr >= 0)', 'The interval must be positive or zero')
    ]
