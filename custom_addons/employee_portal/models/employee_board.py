# -*- coding: utf-8 -*-
from odoo import fields, models


class EmployeeBoardCategory(models.Model):
    _name = "employee.board.category"
    _description = "Employee Board Category"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)


class EmployeeBoardPost(models.Model):
    _name = "employee.board.post"
    _description = "Employee Board Post"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "publish_from desc, create_date desc"

    name = fields.Char(required=True, tracking=True)
    category_id = fields.Many2one("employee.board.category", string="Category", tracking=True)
    type = fields.Selection([
        ("manual", "Manual"),
        ("menu", "Menu"),
        ("notice", "Notice"),
    ], string="Type", tracking=True)
    body_html = fields.Html(string="Content")
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    publish_from = fields.Date(string="Publish From")
    publish_to = fields.Date(string="Publish To")
    is_pinned = fields.Boolean(string="Pinned")
    active = fields.Boolean(default=True)
