# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CrmActivity(models.Model):
    ''' CrmActivity is a model introduced in Odoo v9 that models activities
    performed in CRM, like phone calls, sending emails, making demonstrations,
    ... Users are able to configure their custom activities.

    Each activity can configure recommended next activities. This allows to model
    light custom workflows. This way sales manager can configure their crm
    workflow that salepersons will use in their daily job.

    CrmActivity inherits from mail.message.subtype. This allows users to follow
    some activities through subtypes. Each activity will generate messages with
    the matching subtypes, allowing reporting and statistics computation based
    on mail.message.subtype model. '''

    _name = 'crm.activity'
    _description = 'CRM Activity'
    _inherits = {'mail.message.subtype': 'subtype_id'}
    _rec_name = 'name'
    _order = "sequence"

    days = fields.Integer('Number of days', default=0,
                          help='Number of days before executing the action, allowing you to plan the date of the action.')
    sequence = fields.Integer('Sequence', default=0)
    team_id = fields.Many2one('crm.team', string='Sales Team')
    subtype_id = fields.Many2one('mail.message.subtype', string='Message Subtype', required=True, ondelete='cascade')
    recommended_activity_ids = fields.Many2many(
        'crm.activity', 'crm_activity_rel', 'activity_id', 'recommended_id',
        string='Recommended Next Activities')
    preceding_activity_ids = fields.Many2many(
        'crm.activity', 'crm_activity_rel', 'recommended_id', 'activity_id',
        string='Preceding Activities')

    # setting a default value on inherited fields is a bit involved
    res_model = fields.Char('Model', related='subtype_id.res_model', inherited=True, default='crm.lead')
    internal = fields.Boolean('Internal Only', related='subtype_id.internal', inherited=True, default=True)
    default = fields.Boolean('Default', related='subtype_id.default', inherited=True, default=False)

    @api.multi
    def unlink(self):
        activities = self.search([('subtype_id', '=', self.subtype_id.id)])
        # to ensure that the subtype is only linked the current activity
        if len(activities) == 1:
            self.subtype_id.unlink()
        return super(CrmActivity, self).unlink()
