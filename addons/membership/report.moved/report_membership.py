# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from osv import fields, osv
import tools


class ReportPartnerMemberYear(osv.osv):
    '''Membership by Years'''

    _name = 'report.partner_member.year'
    _description = __doc__
    _auto = False
    _rec_name = 'year'
    _columns = {
        'year': fields.char('Year', size='4', readonly=True, select=1),
        'canceled_number': fields.integer('Canceled', readonly=True),
        'waiting_number': fields.integer('Waiting', readonly=True),
        'invoiced_number': fields.integer('Invoiced', readonly=True),
        'paid_number': fields.integer('Paid', readonly=True),
        'canceled_amount': fields.float('Canceled', digits=(16, 2), readonly=True),
        'waiting_amount': fields.float('Waiting', digits=(16, 2), readonly=True),
        'invoiced_amount': fields.float('Invoiced', digits=(16, 2), readonly=True),
        'paid_amount': fields.float('Paid', digits=(16, 2), readonly=True),
        'currency': fields.many2one('res.currency', 'Currency', readonly=True,
            select=2),
    }

    def init(self, cr):
        '''Create the view'''
        cr.execute("""
    CREATE OR REPLACE VIEW report_partner_member_year AS (
        SELECT
        MIN(id) AS id,
        COUNT(ncanceled) as canceled_number,
        COUNT(npaid) as paid_number,
        COUNT(ninvoiced) as invoiced_number,
        COUNT(nwaiting) as waiting_number,
        SUM(acanceled) as canceled_amount,
        SUM(apaid) as paid_amount,
        SUM(ainvoiced) as invoiced_amount,
        SUM(awaiting) as waiting_amount,
        year,
        currency
        FROM (SELECT
            CASE WHEN ai.state = 'cancel' THEN ml.id END AS ncanceled,
            CASE WHEN ai.state = 'paid' THEN ml.id END AS npaid,
            CASE WHEN ai.state = 'open' THEN ml.id END AS ninvoiced,
            CASE WHEN (ai.state = 'draft' OR ai.state = 'proforma')
                THEN ml.id END AS nwaiting,
            CASE WHEN ai.state = 'cancel'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS acanceled,
            CASE WHEN ai.state = 'paid'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS apaid,
            CASE WHEN ai.state = 'open'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS ainvoiced,
            CASE WHEN (ai.state = 'draft' OR ai.state = 'proforma')
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS awaiting,
            TO_CHAR(ml.date_from, 'YYYY') AS year,
            ai.currency_id AS currency,
            MIN(ml.id) AS id
            FROM membership_membership_line ml
            JOIN (account_invoice_line ail
                LEFT JOIN account_invoice ai
                ON (ail.invoice_id = ai.id))
            ON (ml.account_invoice_line = ail.id)
            JOIN res_partner p
            ON (ml.partner = p.id)
            GROUP BY TO_CHAR(ml.date_from, 'YYYY'), ai.state,
            ai.currency_id, ml.id) AS foo
        GROUP BY year, currency)
                """)
ReportPartnerMemberYear()

class ReportPartnerMemberYearNew(osv.osv):
    '''New Membership by Years'''

    _name = 'report.partner_member.year_new'
    _description = __doc__
    _auto = False
    _rec_name = 'year'
    _columns = {
        'year': fields.char('Year', size='4', readonly=True, select=1),
        'canceled_number': fields.integer('Canceled', readonly=True),
        'waiting_number': fields.integer('Waiting', readonly=True),
        'invoiced_number': fields.integer('Invoiced', readonly=True),
        'paid_number': fields.integer('Paid', readonly=True),
        'canceled_amount': fields.float('Canceled', digits=(16, 2), readonly=True),
        'waiting_amount': fields.float('Waiting', digits=(16, 2), readonly=True),
        'invoiced_amount': fields.float('Invoiced', digits=(16, 2), readonly=True),
        'paid_amount': fields.float('Paid', digits=(16, 2), readonly=True),
        'currency': fields.many2one('res.currency', 'Currency', readonly=True,
            select=2),
    }

    def init(self, cursor):
        '''Create the view'''
        cursor.execute("""
        CREATE OR REPLACE VIEW report_partner_member_year_new AS (
        SELECT
        MIN(id) AS id,
        COUNT(ncanceled) AS canceled_number,
        COUNT(npaid) AS paid_number,
        COUNT(ninvoiced) AS invoiced_number,
        COUNT(nwaiting) AS waiting_number,
        SUM(acanceled) AS canceled_amount,
        SUM(apaid) AS paid_amount,
        SUM(ainvoiced) AS invoiced_amount,
        SUM(awaiting) AS waiting_amount,
        year,
        currency
        FROM (SELECT
            CASE WHEN ai.state = 'cancel' THEN ml2.id END AS ncanceled,
            CASE WHEN ai.state = 'paid' THEN ml2.id END AS npaid,
            CASE WHEN ai.state = 'open' THEN ml2.id END AS ninvoiced,
            CASE WHEN (ai.state = 'draft' OR ai.state = 'proforma')
                THEN ml2.id END AS nwaiting,
            CASE WHEN ai.state = 'cancel'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS acanceled,
            CASE WHEN ai.state = 'paid'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS apaid,
            CASE WHEN ai.state = 'open'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS ainvoiced,
            CASE WHEN (ai.state = 'draft' OR ai.state = 'proforma')
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS awaiting,
            TO_CHAR(ml2.date_from, 'YYYY') AS year,
            ai.currency_id AS currency,
            MIN(ml2.id) AS id
            FROM (SELECT
                    partner AS id,
                    MIN(date_from) AS date_from
                    FROM membership_membership_line
                    GROUP BY partner
                ) AS ml1
                JOIN membership_membership_line ml2
                JOIN (account_invoice_line ail
                    LEFT JOIN account_invoice ai
                    ON (ail.invoice_id = ai.id))
                ON (ml2.account_invoice_line = ail.id)
                ON (ml1.id = ml2.partner AND ml1.date_from = ml2.date_from)
            JOIN res_partner p
            ON (ml2.partner = p.id)
            GROUP BY TO_CHAR(ml2.date_from, 'YYYY'), ai.state,
            ai.currency_id, ml2.id) AS foo
        GROUP BY year, currency
        )
    """)

ReportPartnerMemberYearNew()