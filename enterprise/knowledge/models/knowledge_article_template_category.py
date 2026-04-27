# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ArticleTemplateCategory(models.Model):
    """This model represents the categories of the article templates."""
    _name = "knowledge.article.template.category"
    _description = "Article Template Category"
    _order = "sequence ASC, id ASC"

    name = fields.Char(string="Title", translate=True, required=True)
    sequence = fields.Integer("Category Sequence", default=0, required=True,
        help="It determines the display order of the category")
