# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Section(models.Model):
    _name = "knowledge.section"
    _description = "Regroup multiple knowledge articles."

    title = fields.Char("Title")
    article_ids = fields.One2many("knowledge.article")
