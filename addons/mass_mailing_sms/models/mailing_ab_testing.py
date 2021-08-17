# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv import expression


class MassMailingSmsTestingCamapign(models.Model):
    _inherit = 'mailing.ab.testing'

    mailing_type = fields.Selection(selection_add=[
        ('sms', 'SMS')
    ], ondelete={'sms': 'set default'})
    sms_based_on = fields.Selection([('clicked', 'Most Clicks')], string="SMS Based on", default="clicked")

    def action_add_mailing(self):
        action = super().action_add_mailing()
        if self.mailing_type == 'sms':
            action['context'].update({
                'default_sms_force_send': True,
            })
        return action

    def _get_sort_by_field(self):
        sorted_by = super()._get_sort_by_field()
        if self.mailing_type == 'sms':
            sorted_by = self.sms_based_on
        return sorted_by

    # --------------------------------------------------
    # TOOLS
    # --------------------------------------------------

    def _get_default_mailing_domain(self):
        mailing_domain = super()._get_default_mailing_domain()
        if self.mailing_type == 'sms' and 'phone_sanitized_blacklisted' in self.env[self.mailing_model_name]._fields:
            mailing_domain = expression.AND([mailing_domain, [('phone_sanitized_blacklisted', '=', False)]])

        return mailing_domain
