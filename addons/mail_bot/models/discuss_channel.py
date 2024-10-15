# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.addons import mail


class DiscussChannel(mail.DiscussChannel):

    def execute_command_help(self, **kwargs):
        super().execute_command_help(**kwargs)
        self.env['mail.bot']._apply_logic(self, kwargs, command="help")  # kwargs are not usefull but...
