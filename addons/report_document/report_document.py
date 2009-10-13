# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields,osv
import time


class report_document_user(osv.osv):
    _name = "report.document.user"
    _description = "Files details by Users"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'month': fields.char('Month', size=24,readonly=True),
        'user_id':fields.integer('Owner', readonly=True),
        'user':fields.char('User',size=64,readonly=True),
        'file_title': fields.char('File Name',size=64,readonly=True),
        'directory': fields.char('Directory',size=64,readonly=True),
        'create_date': fields.datetime('Date Created', readonly=True),
        'change_date': fields.datetime('Modified Date', readonly=True),
        'file_size': fields.integer('File Size', readonly=True),
        'nbr':fields.integer('# of Files', readonly=True),
        'type':fields.char('Directory Type',size=64,readonly=True),
        'partner':fields.char('Partner',size=64,readonly=True),
     }
    def init(self, cr):
         cr.execute("""
            create or replace view report_document_user as (
                 select
                     min(f.id) as id,
                     f.user_id as user_id,
                     u.name as user,
                     count(*) as nbr,
                     to_char(f.create_date,'YYYY-MM')||'-'||'01' as name,
                     d.name as directory,
                     f.create_date as create_date,
                     f.file_size as file_size,
                     min(f.title) as file_title,
                     min(d.type) as type,
                     min(EXTRACT(MONTH FROM f.create_date)||'-'||to_char(f.create_date,'Month')) as month,
                     f.write_date as change_date
                 from ir_attachment f
                     left join document_directory d on (f.parent_id=d.id and d.name<>'')
                     inner join res_users u on (f.user_id=u.id)
                 group by d.name,f.parent_id,d.type,f.create_date,f.user_id,f.file_size,u.name,d.type,f.write_date
             )
         """)
report_document_user()

class report_files_partner(osv.osv):
    _name = "report.files.partner"
    _description = "Files details by Partners"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'file_title': fields.char('File Name',size=64,readonly=True),
        'directory': fields.char('Directory',size=64,readonly=True),
        'create_date': fields.datetime('Date Created', readonly=True),
        'change_date': fields.datetime('Modified Date', readonly=True),
        'file_size': fields.integer('File Size', readonly=True),
        'nbr':fields.integer('# of Files', readonly=True),
        'type':fields.char('Directory Type',size=64,readonly=True),
        'partner':fields.char('Partner',size=64,readonly=True),
     }
    def init(self, cr):
         cr.execute("""
            create or replace view report_files_partner as (
                select min(f.id) as id,count(*) as nbr,
                       min(to_char(f.create_date,'YYYY-MM-01')) as name,
                       min(f.title) as file_title,
                       p.name as partner 
                from ir_attachment f 
                inner join res_partner p 
                on (f.partner_id=p.id)
                where f.datas_fname is not null
                group by p.name
             )
         """)
report_files_partner()

class report_document_file(osv.osv):
    _name = "report.document.file"
    _description = "Files details by Directory"
    _auto = False
    _columns = {
        'file_size': fields.integer('File Size', readonly=True),
        'nbr':fields.integer('# of Files', readonly=True),
        'month': fields.char('Month', size=24,readonly=True),
     }
    _order = "month"
    def init(self, cr):
         cr.execute("""
            create or replace view report_document_file as (
                select min(f.id) as id,
                       count(*) as nbr,
                       min(EXTRACT(MONTH FROM f.create_date)||'-'||to_char(f.create_date,'Month')) as month,
                       sum(f.file_size) as file_size  
                from ir_attachment f 
                group by EXTRACT(MONTH FROM f.create_date) 
             )
         """)
        
report_document_file()

class report_document_wall(osv.osv):
    _name = "report.document.wall"
    _description = "Users that did not inserted documents since one month"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'user_id':fields.many2one('res.users', 'Owner',readonly=True),
        'user':fields.char('User',size=64,readonly=True),
        'month': fields.char('Month', size=24,readonly=True),
        'file_name':fields.char('Last Posted File Name',size=64,readonly=True),
        'last':fields.datetime('Last Posted Time', readonly=True),
             }
       
    def init(self, cr):
         cr.execute("""
            create or replace view report_document_wall as (
               select max(f.id) as id,
               min(title) as file_name,
               to_char(min(f.create_date),'YYYY-MM-DD HH24:MI:SS') as last,
               f.user_id as user_id, f.user_id as user,
               to_char(f.create_date,'Month') as month 
               from ir_attachment f 
               where f.create_date in (
                   select max(i.create_date) 
                   from ir_attachment i 
                   inner join res_users u on (i.user_id=u.id) 
                   group by i.user_id) group by f.user_id,f.create_date 
                   having (CURRENT_DATE - to_date(to_char(f.create_date,'YYYY-MM-DD'),'YYYY-MM-DD')) > 30
             )
         """)
report_document_wall()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

