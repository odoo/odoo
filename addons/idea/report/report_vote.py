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

import tools
from osv import fields,osv

class report_vote(osv.osv):
    _name = "report.vote"
    _description = "Idea Vote Statistics"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Date Order', readonly=True, select=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'user_id': fields.many2one('res.users', 'User Name'),
        'score': fields.integer('Score',group_operator="avg"),
        'idea_id': fields.many2one('idea.idea', 'Idea'),
        'nbr':fields.integer('# of Lines', readonly=True),
        'idea_state': fields.selection([('draft', 'Draft'),('open', 'Opened'),
                            ('close', 'Accepted'),
                            ('cancel', 'Cancelled')],
                            'Status'),
        'category_id': fields.many2one('idea.category', 'Category'),
        'creater_id': fields.many2one('res.users', 'User Name'),

        }
    _order = 'date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_vote')
        cr.execute("""
            create or replace view report_vote as (
               select
                    min(iv.id) as id,
                    count(*) as nbr,
                    to_date(to_char(ii.open_date, 'dd-MM-YYYY'),'dd-MM-YYYY') as date,
                    to_char(ii.open_date, 'YYYY') as year,
                    to_char(ii.open_date, 'MM') as month,
                    to_char(ii.open_date, 'YYYY-MM-DD') as day,
                    iv.user_id as user_id,
                    iv.idea_id as idea_id,
                    ii.state as idea_state,
                    ii.user_id as creater_id,
                    ii.category_id,
                    (sum(CAST(iv.score as integer))/count(iv.*)) as score
                from
                    idea_vote as iv
                    left join idea_idea as ii on (ii.id = iv.idea_id)
                group by
                    iv.id ,to_char(ii.open_date, 'dd-MM-YYYY'),to_char(ii.open_date, 'YYYY'),
                    to_char(ii.open_date, 'MM'),to_char(ii.open_date, 'YYYY-MM-DD'),ii.state,
                    iv.user_id,ii.user_id,ii.category_id,iv.idea_id
            )
            """)
report_vote()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
