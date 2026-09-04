# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None):
        """ 停用订阅功能. """
        ir_config = self.env['ir.config_parameter'].sudo()
        app_stop_subscribe = True if ir_config.get_param('app_stop_subscribe', False) == "True" else False
        if app_stop_subscribe:
            return True
        return super(MailThread, self).message_subscribe(partner_ids, subtype_ids)

    def _message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None, customer_ids=None):
        """ 停用订阅功能. """
        ir_config = self.env['ir.config_parameter'].sudo()
        app_stop_subscribe = True if ir_config.get_param('app_stop_subscribe', False) == "True" else False
        if app_stop_subscribe:
            return True
        return super(MailThread, self)._message_subscribe(partner_ids, subtype_ids, customer_ids)

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        """ 停用订阅功能. """
        ir_config = self.env['ir.config_parameter'].sudo()
        app_stop_subscribe = True if ir_config.get_param('app_stop_subscribe', False) == "True" else False
        if app_stop_subscribe:
            return []
        return super(MailThread, self)._message_auto_subscribe_followers(updated_values, default_subtype_ids)

    def _message_auto_subscribe_notify(self, partner_ids, template):
        """ 停用订阅功能. """
        ir_config = self.env['ir.config_parameter'].sudo()
        app_stop_subscribe = True if ir_config.get_param('app_stop_subscribe', False) == "True" else False
        if app_stop_subscribe:
            return True
        return super(MailThread, self)._message_auto_subscribe_notify(partner_ids, template)
