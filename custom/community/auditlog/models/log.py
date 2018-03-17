# -*- coding: utf-8 -*-
# © 2015 ABF OSIELL <http://osiell.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class AuditlogLog(models.Model):
    _name = 'auditlog.log'
    _description = "Auditlog - Log"
    _order = "create_date desc"

    name = fields.Char("Resource Name", size=64)
    model_id = fields.Many2one(
        'ir.model', string=u"Model")
    res_id = fields.Integer(u"Resource ID")
    user_id = fields.Many2one(
        'res.users', string=u"User")
    method = fields.Char(u"Method", size=64)
    line_ids = fields.One2many(
        'auditlog.log.line', 'log_id', string=u"Fields updated")
    http_session_id = fields.Many2one(
        'auditlog.http.session', string=u"Session")
    http_request_id = fields.Many2one(
        'auditlog.http.request', string=u"HTTP Request")
    log_type = fields.Selection(
        [('full', u"Full log"),
         ('fast', u"Fast log"),
         ],
        string=u"Type")


class AuditlogLogLine(models.Model):
    _name = 'auditlog.log.line'
    _description = "Auditlog - Log details (fields updated)"

    field_id = fields.Many2one(
        'ir.model.fields', ondelete='cascade', string=u"Field", required=True)
    log_id = fields.Many2one(
        'auditlog.log', string=u"Log", ondelete='cascade', index=True)
    old_value = fields.Text(u"Old Value")
    new_value = fields.Text(u"New Value")
    old_value_text = fields.Text(u"Old value Text")
    new_value_text = fields.Text(u"New value Text")
    field_name = fields.Char(u"Technical name", related='field_id.name')
    field_description = fields.Char(
        u"Description", related='field_id.field_description')
