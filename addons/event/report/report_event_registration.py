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
        'event_date': fields.date('Event Start Date', readonly=True),
        'price_subtotal':fields.integer('subtotal'),
        'year': fields.char('Year', size=4, readonly=True),
        'month': fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'event_id': fields.many2one('event.event', 'Event', required=True),
        'draft_state': fields.integer(' # No of Draft Registrations', size=20),
        'average_subtotal': fields.integer('average_subtotal', size=20),
        'confirm_state': fields.integer(' # No of Confirmed Registrations', size=20),
        'register_max': fields.integer('Maximum Registrations'),
        'nbevent': fields.integer('Number Of Events'),
        'event_type': fields.many2one('event.type', 'Event Type'),
        'registration_state': fields.selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', readonly=True, required=True),
        'event_state': fields.selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', readonly=True, required=True),
        'user_id': fields.many2one('res.users', 'Responsible', readonly=True),
        'name_registration': fields.char('Register',size=45, readonly=True),
        'speaker_id': fields.many2one('res.partner', 'Speaker', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'total': fields.float('Total'),
        'section_id': fields.related('event_id', 'section_id', type='many2one', relation='crm.case.section', string='Sale Team', store=True, readonly=True),
    }
    _order = 'event_date desc'
    def init(self, cr):
        """
        initialize the sql view for the event registration
        cr -- the cursor
        """
        tools.drop_view_if_exists(cr, 'report_event_registration')
        cr.execute("""
         CREATE OR REPLACE view report_event_registration AS (
                SELECT
                event_id,
                r.id,
                e.date_begin AS event_date,
                e.user_id AS user_id,
                r.user_id AS user_id_registration,
                r.name AS name_registration,
                e.section_id AS section_id,
                e.company_id AS company_id,
                e.main_speaker_id AS speaker_id,
                to_char(e.date_begin, 'YYYY') AS year,
                to_char(e.date_begin, 'MM') AS month,
                count(e.id) AS nbevent,
                CASE WHEN r.state IN ('draft') THEN r.nb_register ELSE 0 END AS draft_state,
                CASE WHEN r.state IN ('open','done') THEN r.nb_register ELSE 0 END AS confirm_state,
                CASE WHEN r.state IN ('done') THEN r.price_subtotal ELSE 0 END AS total,
                e.type AS event_type,
                r.price_subtotal,
                AVG(r.price_subtotal) AS average_subtotal,
                e.register_max AS register_max,
                e.state AS  event_state,
                r.state AS  registration_state
                FROM
                event_event e
                
                LEFT JOIN
                    event_registration r ON (e.id=r.event_id)

                WHERE r.active = 'true'
               
               GROUP BY
                event_id,
                user_id_registration,
                e.id,
                r.id,
                registration_state,
                r.nb_register,
                event_type, e.id, e.date_begin, e.main_speaker_id,
                e.register_max,event_id, e.user_id,e.company_id,e.product_id,e.section_id, r.price_subtotal,
                e.user_id,
                e.section_id,
                event_state,
                e.company_id,

                e.main_speaker_id,
                year,
                month,
                e.register_max,
                name_registration

              )
                """)

report_event_registration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
