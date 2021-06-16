# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from odoo import fields, models


class MassMailingVersion(models.Model):
    _name = 'mailing.mailing.version'
    _description = "Mailing Version"

    def _default_color(self):
        return random.randint(1, 11)

    name = fields.Char('Version', index=True, required=True)
    color = fields.Integer('Color Index', default=lambda self: self._default_color())

    _sql_constraints = [('name_uniq', 'unique (name)', "Version name already exists !")]

    def _search_create_version_id(self, name):
        version = self.search([('name', '=', name)])
        if not version:
            version = self.create({'name': name})
        return version


class MassMailingTestingCampaignTag(models.Model):
    _name = 'mailing.ab.testing.tag'
    _description = 'Testing Mailing Tag'

    def _default_color(self):
        return random.randint(1, 11)

    name = fields.Char('Name')
    color = fields.Integer('Color Index', default=lambda self: self._default_color())
