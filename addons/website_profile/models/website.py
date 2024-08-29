# -*- coding: utf-8 -*-
from odoo.addons import website
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model, website.Website):

    karma_profile_min = fields.Integer(string="Minimal karma to see other user's profile", default=150)
