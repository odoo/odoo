from odoo import models, api, fields
from odoo.tools.sql import SQL
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED
import logging

_logger = logging.getLogger(__name__)


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    def _upsert_visitor(self, access_token, force_track_values=None):
        """
        Prevent PostgreSQL SERIALIZATION_FAILURE ('could not serialize access
        due to concurrent update') on concurrent website visitor tracking requests.
        """
        access_token_str = str(access_token)

        # 1. Fast path: If the visitor record was already updated within the last 10 seconds,
        # skip updating website_visitor.last_connection_datetime.
        # This completely avoids concurrent row update conflicts on website_visitor.
        existing_visitor = self.sudo().search([('access_token', '=', access_token_str)], limit=1)
        if existing_visitor and existing_visitor.last_connection_datetime:
            delta = fields.Datetime.now() - existing_visitor.last_connection_datetime
            if delta.total_seconds() < 10:
                if force_track_values:
                    try:
                        self.env['website.track'].sudo().create({
                            'visitor_id': existing_visitor.id,
                            'url': force_track_values['url'],
                            'page_id': force_track_values.get('page_id'),
                            'visit_datetime': fields.Datetime.now(),
                        })
                    except Exception as e:
                        _logger.debug("Failed to record website track: %s", e)
                return (existing_visitor.id, 'updated')

        # 2. When an update is required, execute the upsert in a dedicated cursor with
        # ISOLATION_LEVEL_READ_COMMITTED. In READ COMMITTED, PostgreSQL serializes row
        # updates without raising SerializationFailure, preventing request retries and delays.
        try:
            with self.pool.cursor() as tracking_cr:
                tracking_cr.connection.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
                tracking_env = self.env(cr=tracking_cr)

                lang_id = 1
                country_code = None
                website_id = 1
                from odoo.http import request
                if request:
                    if hasattr(request, 'lang') and request.lang:
                        lang_id = request.lang.id
                    if hasattr(request, 'geoip') and request.geoip:
                        country_code = request.geoip.get('country_code')
                    if hasattr(request, 'website') and request.website:
                        website_id = request.website.id

                create_values = {
                    'access_token': access_token,
                    'lang_id': lang_id,
                    'country_code': country_code,
                    'website_id': website_id,
                    'timezone': self._get_visitor_timezone() or None,
                    'write_uid': self.env.uid or 1,
                    'create_uid': self.env.uid or 1,
                    'partner_id': None if len(access_token_str) == 32 else access_token,
                }

                query = SQL("""
                    INSERT INTO website_visitor (
                        partner_id, access_token, last_connection_datetime, visit_count, lang_id,
                        website_id, timezone, write_uid, create_uid, write_date, create_date, country_id)
                    VALUES (
                        %(partner_id)s, %(access_token)s, now() at time zone 'UTC', 1, %(lang_id)s,
                        %(website_id)s, %(timezone)s, %(create_uid)s, %(write_uid)s,
                        now() at time zone 'UTC', now() at time zone 'UTC', (
                            SELECT id FROM res_country WHERE code = %(country_code)s
                        )
                    )
                    ON CONFLICT (access_token)
                    DO UPDATE SET
                        last_connection_datetime=excluded.last_connection_datetime,
                        visit_count = CASE WHEN website_visitor.last_connection_datetime < NOW() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
                                            THEN website_visitor.visit_count + 1
                                            ELSE website_visitor.visit_count
                                        END
                    RETURNING id, CASE WHEN create_date = now() at time zone 'UTC' THEN 'inserted' ELSE 'updated' END AS upsert
                """, **create_values)

                if force_track_values:
                    query = SQL("""
                        WITH visitor AS (
                            %(query)s, %(url)s AS url, %(page_id)s AS page_id
                        ), track AS (
                            INSERT INTO website_track (visitor_id, url, page_id, visit_datetime)
                            SELECT id, url, page_id::integer, now() at time zone 'UTC' FROM visitor
                        )
                        SELECT id, upsert from visitor;
                        """,
                        query=query,
                        url=force_track_values['url'],
                        page_id=force_track_values.get('page_id'),
                    )

                [result] = tracking_env.execute_query(query)
                tracking_cr.commit()
                return result
        except Exception as e:
            _logger.warning("Website visitor upsert fallback triggered: %s", e)
            visitor = self.sudo().search([('access_token', '=', access_token_str)], limit=1)
            return (visitor.id if visitor else False, 'updated')
