# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class CrmActivity(models.Model):
    ''' CrmActivity is a model introduced in Odoo v9 that models activities
    performed in CRM, like phonecalls, sending emails, making demonstrations,
    ... Users are able to configure their custom activities.

    Each activity has up to three next activities. This allows to model light
    custom workflows. This way sales manager can configure their crm workflow
    that salepersons will use in their daily job.

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
    activity_1_id = fields.Many2one('crm.activity', string="Next Activity 1")
    activity_2_id = fields.Many2one('crm.activity', string="Next Activity 2")
    activity_3_id = fields.Many2one('crm.activity', string="Next Activity 3")

    @api.model
    def create(self, values):
        ''' Override to set the res_model of inherited subtype to crm.lead.
        This cannot be achieved using a default on res_model field because
        of the inherits. Indeed a new field would be created. However the
        field on the subtype would still exist. Being void, the subtype
        will be present for every model in Odoo. That's quite an issue. '''
        if not values.get('res_model') and 'default_res_model' not in self._context:
            values['res_model'] = 'crm.lead'
        if 'internal' not in values and 'default_internal' not in self._context:
            values['internal'] = True
        return super(CrmActivity, self).create(values)
