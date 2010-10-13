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
    _description = "Events on registrations and Events on type"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month': fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'day': fields.char('Date', size=128, readonly=True),
        'event_id': fields.many2one('event.event', 'Event Related', required=True),
        'draft_state': fields.integer(' # No of draft Registration.', size=20),
        'confirm_state': fields.integer(' # No of Confirm Registration', size=20),
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
                e.id AS id,
                c.event_id AS event_id,
                e.date_begin AS date,
                e.user_id AS user_id,
                e.section_id AS section_id,
                e.company_id AS company_id,
                e.product_id AS product_id,
                e.main_speaker_id AS speaker_id,
                to_char(e.date_begin, 'YYYY') AS year,
                to_char(e.date_begin, 'MM') AS month,
                to_char(e.date_begin, 'YYYY-MM-DD') AS day,
                count(t.id) AS nbevent,
                t.id AS type,
                (SELECT SUM(c.nb_register) FROM event_registration  c  WHERE c.event_id=e.id AND t.id=e.type AND c.state IN ('draft')) AS draft_state,
                (SELECT SUM(c.nb_register) FROM event_registration  c  WHERE c.event_id=e.id AND t.id=e.type AND c.state IN ('open')) AS confirm_state,
                (SELECT SUM(c.price_subtotal) FROM event_registration  c  WHERE c.event_id=e.id AND t.id=e.type AND c.state IN ('done')) AS total,
                e.register_max AS register_max,
                e.state AS state
                FROM
                event_event e
                INNER JOIN
                    event_registration c ON (e.id=c.event_id)
                INNER JOIN
                    event_type t ON (e.type=t.id)
               GROUP BY
                    to_char(e.date_begin, 'YYYY'),
                    to_char(e.date_begin, 'MM'),
                    t.id, e.id, e.date_begin, e.main_speaker_id,
                    e.register_max, e.type, e.state, c.event_id, e.user_id,e.company_id,e.product_id,e.section_id,
                    to_char(e.date_begin, 'YYYY-MM-DD')
                )""")

report_event_registration()
