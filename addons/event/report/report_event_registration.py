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

class report_event_registration(osv.osv):

    _name = "report.event.registration"
    _description = "Events Analysis"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Event Start Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month': fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'event_id': fields.many2one('event.event', 'Event', required=True),
        'draft_state': fields.integer(' # No of Draft Registrations', size=20),
        'confirm_state': fields.integer(' # No of Confirmed Registrations', size=20),
        'register_max': fields.integer('Maximum Registrations'),
        'nbevent': fields.integer('Number Of Events'),
        'type': fields.many2one('event.type', 'Event Type'),
        'state': fields.selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', readonly=True, required=True),
        'user_id': fields.many2one('res.users', 'Responsible', readonly=True),
        'speaker_id': fields.many2one('res.partner', 'Speaker', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'total': fields.float('Total'),
        'section_id': fields.related('event_id', 'section_id', type='many2one', relation='crm.case.section', string='Sale Team', store=True, readonly=True),
    }
    _order = 'date desc'
    def init(self, cr):
        """
        initialize the sql view for the event registration
        cr -- the cursor
        """
        tools.drop_view_if_exists(cr, 'report_event_registration')
        cr.execute("""
         CREATE OR REPLACE view report_event_registration AS (
                SELECT
                id,
                event_id,
                date,
                user_id,
                section_id,
                company_id,
                product_id,
                speaker_id,
                year,
                month,
                nbevent,
                type,
                SUM(draft_state) AS draft_state,
                SUM(confirm_state) AS confirm_state,
                SUM(total) AS total,
                register_max,
                state
                FROM(
                SELECT
                MIN(e.id) AS id,
                e.id AS event_id,
                e.date_begin AS date,
                e.user_id AS user_id,
                e.section_id AS section_id,
                e.company_id AS company_id,
                e.product_id AS product_id,
                e.main_speaker_id AS speaker_id,
                to_char(e.date_begin, 'YYYY') AS year,
                to_char(e.date_begin, 'MM') AS month,
                count(e.id) AS nbevent,
                t.id AS type,
                CASE WHEN c.state IN ('draft') THEN c.nb_register ELSE 0 END AS draft_state,
                CASE WHEN c.state IN ('open','done') THEN c.nb_register ELSE 0 END AS confirm_state,
                CASE WHEN c.state IN ('done') THEN c.price_subtotal ELSE 0 END AS total,
                e.register_max AS register_max,
                e.state AS state
                FROM
                event_event e
                LEFT JOIN
                    event_registration c ON (e.id=c.event_id)
                LEFT JOIN
                    event_type t ON (e.type=t.id)
               GROUP BY
                    to_char(e.date_begin, 'YYYY'),
                    to_char(e.date_begin, 'MM'),
                    c.state,
                    c.nb_register,
                    t.id, e.id, e.date_begin, e.main_speaker_id,
                    e.register_max, e.type, e.state, c.event_id, e.user_id,e.company_id,e.product_id,e.section_id,
                    to_char(e.date_begin, 'YYYY-MM-DD'), c.id, c.price_subtotal )AS foo
                GROUP BY
                id,
                event_id,
                date,
                user_id,
                section_id,
                company_id,
                product_id,
                speaker_id,
                year,
                month,
                nbevent,
                type,
                register_max,
                state
              )
                """)

report_event_registration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: