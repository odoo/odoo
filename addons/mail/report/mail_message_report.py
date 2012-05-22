# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from osv import fields, osv
import time
import tools

class mail_message_report(osv.osv):
     #CSV:: access_res_log_report all,res.log.report,model_res_log_report,,1,0,0,0
    """ Log Report """
    _name = "mail.message.report"
    _auto = False
    _description = "Mail Message Report"
    _columns = {
        'name': fields.char('Year', size=64, required=False, readonly=True),
        'month':fields.selection([('01', 'January'), ('02', 'February'), \
                                  ('03', 'March'), ('04', 'April'),\
                                  ('05', 'May'), ('06', 'June'), \
                                  ('07', 'July'), ('08', 'August'),\
                                  ('09', 'September'), ('10', 'October'),\
                                  ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'creation_date': fields.date('Creation Date', readonly=True),
        'res_model': fields.char('Object', size=128),
        'nbr': fields.integer('# of Entries', readonly=True)
     }

    def init(self, cr):
        """
            Log Report
            @param cr: the current row, from the database cursor
        """
        tools.drop_view_if_exists(cr,'mail_message_report')
        cr.execute("""
            CREATE OR REPLACE VIEW mail_message_report AS (
                SELECT
                    l.id as id,
                    1 as nbr,
                    to_char(l.create_date, 'YYYY') as name,
                    to_char(l.create_date, 'MM') as month,
                    to_char(l.create_date, 'YYYY-MM-DD') as day,
                    to_char(l.create_date, 'YYYY-MM-DD') as creation_date,
                    l.model as res_model,
                    date_trunc('day',l.create_date) as create_date
                FROM
                    mail_message l
            )""")

