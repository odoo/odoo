# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp import tools


class MassMailingnReport(osv.Model):
    _name = 'mail.mass_mailing.report'
    _auto = False
    _description = 'Mass Mailing Analysis'
    _rec_name = 'mailing_date'

    _columns = {
        'mailing_date': fields.datetime('Mailing Date', readonly=True),
    }

    def init(self, cr):
        """ Mass Mailing Report: based on mail.mass_mailing model that models the
        various mailing performed, and mail.mail.statistics that models the various
        statistics collected for each mailing. """
        tools.drop_view_if_exists(cr, 'mail_mass_mailing_report')
        cr.execute("""
            CREATE OR REPLACE VIEW mail_mass_mailing_report AS (
                SELECT
                    id,

                    date_trunc('day', m.sent_date) as mailing_date
                FROM
                    mail_mass_mailing m
            )""")
