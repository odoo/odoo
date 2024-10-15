# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import website


class Website(website.Website):

    karma_profile_min = fields.Integer(string="Minimal karma to see other user's profile", default=150)
