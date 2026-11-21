# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Website(models.Model):
    _inherit = 'website'

    def _is_tracking_enabled(self, main_object):
        # Survey pages are not tracked, their URL contains the answer token, would give access to user's answer
        if main_object._name == 'survey.survey':
            return False
        return super()._is_tracking_enabled(main_object)
