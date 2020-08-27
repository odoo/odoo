# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml.builder import E

from odoo import models, api


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    # ------------------------------------------------------------
    # ACTIVITY
    # -----------------------------------------------------------

    @api.model
    def _get_default_activity_view(self):
        """ Generates an empty activity view.

        :returns: a activity view as an lxml document
        :rtype: etree._Element
        """
        field = E.field(name=self._rec_name_fallback())
        activity_box = E.div(field, {'t-name': "activity-box"})
        templates = E.templates(activity_box)
        return E.activity(templates, string=self._description)

    # ------------------------------------------------------------
    # GATEWAY: NOTIFICATION
    # ------------------------------------------------------------

    def _notify_email_headers(self):
        """
            Generate the email headers based on record
        """
        if not self:
            return {}
        self.ensure_one()
        return repr(self._notify_email_header_dict())

    def _notify_email_header_dict(self):
        return {
            'X-Odoo-Objects': "%s-%s" % (self._name, self.id),
        }
