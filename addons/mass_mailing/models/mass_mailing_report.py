# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp import tools


class MassMailingReport(osv.Model):
    _name = 'mail.statistics.report'
    _auto = False
    _description = 'Mass Mailing Statistics'

    _columns = {
        'scheduled_date': fields.datetime('Scheduled Date', readonly=True),
        'name': fields.char('Mass Mail', readonly=True),
        'campaign': fields.char('Mass Mail Campaign', readonly=True),
        'sent': fields.integer('Sent', readonly=True),
        'delivered': fields.integer('Delivered', readonly=True),
        'opened': fields.integer('Opened', readonly=True),
        'bounced': fields.integer('Bounced', readonly=True),
        'replied': fields.integer('Replied', readonly=True),
        'state': fields.selection(
            [('draft', 'Draft'), ('test', 'Tested'), ('done', 'Sent')],
            string='Status', readonly=True,
        ),
        'email_from': fields.char('From', readonly=True),
    }

    def init(self, cr):
        """Mass Mail Statistical Report: based on mail.mail.statistics that models the various
        statistics collected for each mailing, and mail.mass_mailing model that models the
        various mailing performed. """
        tools.drop_view_if_exists(cr, 'mail_statistics_report')
        cr.execute("""
            CREATE OR REPLACE VIEW mail_statistics_report AS (
                SELECT
                    min(ms.id) as id,
                    ms.scheduled as scheduled_date,
                    utm_source.name as name,
                    utm_campaign.name as campaign,
                    count(ms.bounced) as bounced,
                    count(ms.sent) as sent,
                    (count(ms.sent) - count(ms.bounced)) as delivered,
                    count(ms.opened) as opened,
                    count(ms.replied) as replied,
                    mm.state,
                    mm.email_from
                FROM
                    mail_mail_statistics as ms
                    left join mail_mass_mailing as mm ON (ms.mass_mailing_id=mm.id)
                    left join mail_mass_mailing_campaign as mc ON (ms.mass_mailing_campaign_id=mc.id)
                    left join utm_campaign as utm_campaign ON (mc.campaign_id = utm_campaign.id)
                    left join utm_source as utm_source ON (mm.source_id = utm_source.id)
                GROUP BY ms.scheduled, utm_source.name, utm_campaign.name, mm.state, mm.email_from
            )""")
