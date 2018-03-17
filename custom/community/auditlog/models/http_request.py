# -*- coding: utf-8 -*-
# © 2015 ABF OSIELL <http://osiell.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2.extensions import AsIs

from odoo import models, fields, api
from odoo.http import request


class AuditlogHTTPRequest(models.Model):
    _name = 'auditlog.http.request'
    _description = u"Auditlog - HTTP request log"
    _order = "create_date DESC"

    display_name = fields.Char(
        u"Name", compute="_compute_display_name", store=True)
    name = fields.Char(u"Path")
    root_url = fields.Char(u"Root URL")
    user_id = fields.Many2one(
        'res.users', string=u"User")
    http_session_id = fields.Many2one(
        'auditlog.http.session', string=u"Session")
    user_context = fields.Char(u"Context")
    log_ids = fields.One2many(
        'auditlog.log', 'http_request_id', string=u"Logs")

    @api.depends('create_date', 'name')
    def _compute_display_name(self):
        for httprequest in self:
            create_date = fields.Datetime.from_string(httprequest.create_date)
            tz_create_date = fields.Datetime.context_timestamp(
                httprequest, create_date)
            httprequest.display_name = u"%s (%s)" % (
                httprequest.name or '?',
                fields.Datetime.to_string(tz_create_date))

    @api.multi
    def name_get(self):
        return [(request.id, request.display_name) for request in self]

    @api.model
    def current_http_request(self):
        """Create a log corresponding to the current HTTP request, and returns
        its ID. This method can be called several times during the
        HTTP query/response cycle, it will only log the request on the
        first call.
        If no HTTP request is available, returns `False`.
        """
        if not request:
            return False
        http_session_model = self.env['auditlog.http.session']
        httprequest = request.httprequest
        if httprequest:
            if hasattr(httprequest, 'auditlog_http_request_id'):
                # Verify existence. Could have been rolled back after a
                # concurrency error
                self.env.cr.execute(
                    "SELECT id FROM %s WHERE id = %s", (
                        AsIs(self._table),
                        httprequest.auditlog_http_request_id))
                if self.env.cr.fetchone():
                    return httprequest.auditlog_http_request_id
            vals = {
                'name': httprequest.path,
                'root_url': httprequest.url_root,
                'user_id': request.uid,
                'http_session_id': http_session_model.current_http_session(),
                'user_context': request.context,
            }
            httprequest.auditlog_http_request_id = self.create(vals).id
            return httprequest.auditlog_http_request_id
        return False
