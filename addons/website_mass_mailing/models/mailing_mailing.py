# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class MassMailing(models.Model):
    _name = 'mailing.mailing'
    _inherit = ['mailing.mailing', 'website.multi.mixin']
