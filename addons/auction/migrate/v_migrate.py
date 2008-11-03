#!/usr/bin/python
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

import psycopg
import csv

db_old = "in"
print 'Extracting data from db '+db_old
#
#def import_sql(cr, fname, query, fields=None, trigger=None):
#   cr.execute(query)
#   fp = file(fname,'wb')
#   result = cr.fetchall()
#   if trigger:
#       result = map(lambda x: tuple(trigger(cr, list(x))), result)
#   writer = csv.writer(fp,lineterminator='\n')
#   writer.writerow(["id","lang","website","name","comment","active","category_id"])
#   for line in result:
#       cr.execute("SELECT c.name from res_partner_category_rel r join res_partner p on (p.id=r.partner_id)  join res_partner_category c on (r.category_id=c.id) where p.name=%s",(line[3],))
#       cats= ",".join([l[0] for l in cr.fetchall()])
#       print "cats",cats
#       line=line + (cats,)
#       writer.writerow(line)
#   fp.close()
#
#db = psycopg.connect("dbname="+db_old)
#cr = db.cursor()
def import_sql(cr, fname, query, fields=None, trigger=None):
    cr.execute(query)
    fp = file(fname,'wb')
    result = cr.fetchall()
    if trigger:
        result = map(lambda x: tuple(trigger(cr, list(x))), result)
    writer = csv.writer(fp,lineterminator='\n')
    writer.writerow(["id","lang","website","name","comment","active","category_id"])
    for line in result:
        cr.execute("SELECT c.name from res_partner_category_rel r join res_partner p on (p.id=r.partner_id)  join res_partner_category c on (r.category_id=c.id) where p.name=%s",(line[3],))
        l = ''
        for x in cr.fetchall():
            if not l:
                l = x[0]
            else:
                l += ',' + x[0]
        writer.writerow(line + (l,))


#       print l
#       head,tail= l[:1], l[1:]
#       if not head: head= [None]
#       writer.writerow(line+tuple(head))
#       for t in tail:
#           writer.writerow((None,None,None,None,None,None)+(t,))


#       for l in cr.fetchall():
#           a=0
#           lenght=len(l)
#           line=line + (l[a],)
#           print "l[0]",a,l[a]
#           print line
#           writer.writerow(line)
#           a=a+1
#           while a< lenght:
#               line2=(None,None,None,None,None,None,) +(l[a],)
#               writer.writerow(line2)
#               a=a+1
    fp.close()

    #       if l[0] != cats:
    #           line2=",,,,,"+(l[0][1:],)
    #           print "line2",line2
db = psycopg.connect("dbname="+db_old)
cr = db.cursor()

cr.execute("update auction_lots set state='draft' where state is null or state = '' ")
cr.execute("update auction_lots set state='sold' where state='invoiced'")


cr.execute('select id,name from res_partner')
res= cr.fetchall()
names=[]
for r in res:
    if r[1] in names:
        cr.execute("update res_partner set name= %s where id=%d",(r[1]+str(r[0]),r[0]))
    else:
        names.append(r[1])


##clients category
#import_sql(cr, 
#   'res.partner.category.csv',
#   """
#   select
#   name,
#   active
#   from 
#   res_partner_category
#   """
#)

#res.partner
import_sql(cr,
    'res.partner.csv',
    """
    select
    'partner'||r.id as id,
    r.lang,
    r.website,
    r.name,
    r.comment,
    r.active
    from
    res_partner r --limit 10
    """
)


#   (select cat.name||'\N' from res_partner r1, res_partner_category cat,res_partner_category_rel rel where r1.id=rel.partner_id and rel.category_id=cat.id) as "category_id",
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

