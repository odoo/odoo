# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PortalTest(models.Model):
    """ A very simple model only inheriting from mail.thread when only
    communication history is necessary. """
    _description = 'Simple Chatter Model'
    _name = 'portal.test.simple'
    _inherit = ['portal.mixin', 'mail.thread']

    name = fields.Char()
    email_from = fields.Char()
