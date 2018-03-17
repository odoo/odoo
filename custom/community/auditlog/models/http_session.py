# -*- coding: utf-8 -*-
# © 2015 ABF OSIELL <http://osiell.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.http import request


class AuditlogtHTTPSession(models.Model):
    _name = 'auditlog.http.session'
    _description = u"Auditlog - HTTP User session log"
    _order = "create_date DESC"

    display_name = fields.Char(
        u"Name", compute="_compute_display_name", store=True)
    name = fields.Char(u"Session ID", index=True)
    user_id = fields.Many2one(
        'res.users', string=u"User", index=True)
    http_request_ids = fields.One2many(
        'auditlog.http.request', 'http_session_id', string=u"HTTP Requests")

    @api.depends('create_date', 'user_id')
    def _compute_display_name(self):
        for httpsession in self:
            create_date = fields.Datetime.from_string(httpsession.create_date)
            tz_create_date = fields.Datetime.context_timestamp(
                httpsession, create_date)
            httpsession.display_name = u"%s (%s)" % (
                httpsession.user_id and httpsession.user_id.name or '?',
                fields.Datetime.to_string(tz_create_date))

    @api.multi
    def name_get(self):
        return [(session.id, session.display_name) for session in self]

    @api.model
    def current_http_session(self):
        """Create a log corresponding to the current HTTP user session, and
        returns its ID. This method can be called several times during the
        HTTP query/response cycle, it will only log the user session on the
        first call.
        If no HTTP user session is available, returns `False`.
        """
        if not request:
            return False
        httpsession = request.session
        if httpsession:
            existing_session = self.search(
                [('name', '=', httpsession.sid),
                 ('user_id', '=', request.uid)],
                limit=1)
            if existing_session:
                return existing_session.id
            vals = {
                'name': httpsession.sid,
                'user_id': request.uid,
            }
            httpsession.auditlog_http_session_id = self.create(vals).id
            return httpsession.auditlog_http_session_id
        return False
