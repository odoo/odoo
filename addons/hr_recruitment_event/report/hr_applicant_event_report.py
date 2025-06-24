# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class HrApplicantEventReport(models.Model):
    _auto = False
    _name = 'hr.applicant.event.report'
    _description = 'Applicant Event Report'

    active = fields.Boolean(readonly=True)
    event_id = fields.Many2one('event.event', readonly=True)
    event_name = fields.Char(readonly=True)
    applicant_name = fields.Char(readonly=True)
    event_country_id = fields.Many2one('res.country', readonly=True)
    number_of_attendees = fields.Integer('Number of participants', readonly=True)
    number_of_applicants = fields.Integer('Number of applicants', readonly=True)
    number_of_signed_contracts = fields.Integer('Number of signed contracts', readonly=True)
    date_begin = fields.Date(readonly=True)

    def _select(self):
        return """
                event.active AS active,
                e.event_id AS event_id,
                event.name AS event_name,
                a.name AS applicant_name,
                date_begin AS date_begin,
                event.country_id AS event_country_id,
                COUNT(e.id) AS number_of_attendees,
                COUNT(a.id) AS number_of_applicants,
                COUNT(a.id) FILTER (
                                    WHERE a.active
                                          AND refuse_reason_id IS NULL
                                          AND a.date_closed IS NOT NULL ) AS number_of_signed_contracts
        """

    def _from(self):
        return """
                event_registration e
                LEFT JOIN hr_applicant a ON e.email = a.email_from
                LEFT JOIN event_event event ON e.event_id = event.id
        """

    def _where(self):
        return """
                e.state = 'done'
        """

    def _group_by(self):
        return """
                event_id,
                date_begin,
                event.active,
                event.name,
                a.name,
                event.country_id
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
        CREATE OR REPLACE VIEW %s AS (
            SELECT %s
            FROM %s
            WHERE %s
            GROUP BY %s
        )
        """ % (self._table, self._select(), self._from(), self._where(), self._group_by()))
