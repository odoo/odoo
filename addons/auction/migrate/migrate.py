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

def import_sql(cr, fname, query, fields=None, trigger=None):
    cr.execute(query)
    if not fields:
        fields = map(lambda x: x[0], cr.description)
    fp = file(fname,'wb')
    result = cr.fetchall()
    if trigger:
        result = map(lambda x: tuple(trigger(cr, list(x))), result)
    writer = csv.writer(fp,lineterminator='\n')
    writer.writerow(fields)
    writer.writerows(result)
    fp.close()


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

# cr.execute('select id,name from res_country')
# res= cr.fetchall()
# names=[]
# for r in res:
#   if r[1] in names:
#       cr.execute("update res_country set name= %s where id=%d",(str(r[1])+str(r[0]),r[0]))
#   else:
#       names.append(r[1])

# cr.execute('select id,code from res_country')
# res= cr.fetchall()
# names=[]
# for r in res:
#   if r[1] in names:
#       cr.execute("update res_country set code= %s where id=%d",(str(r[1])+str(r[0]),r[0]))
#   else:
#       names.append(r[1])



def _account_trigger(cr, x):
    x = list(x)
    if x[5] not in ('receivable','payable','view','income','expense','tax','cash','asset','equity','closed'):
        x[5] = {'stock_inventory':'asset','stock_income':'income','stock_expense':'expense'}.get(x[5], 'asset')
    return tuple(x)
# account.account
import_sql(cr,
    'account.account.csv',
    "select 'account' || id as id, code, name, 'EUR' as currency_id, True as active, type from account_account",
    trigger = _account_trigger
)

#account.tax
import_sql(cr,
    'account.tax.csv',
    """select
            'tax' || id as id,
            domain,
            name,
            'account'||account_collected_id as "account_collected_id:id",
            'account'||account_paid_id as "account_paid_id:id",
            amount,
            child_depend,
            type
        from
            account_tax
    """
)

#res.country
# import_sql(cr,
#   'res.country.csv',
#   """
#   select
#   'country'||id as id,
#   coalesce(name,id::char(10)) as "name",
#   coalesce(code,id::char(10)) as "code"
#   from
#   res_country
#   """
# )
#clients category
import_sql(cr,  
    'res.partner.category.csv',
    """
    select
    name,
    active
    from 
    res_partner_category
    """
)
##res.partner.category.rel
#import_sql(cr,
#   'res.partner.category.rel.csv',
#   """
#   select
#   'partner'||rel.partner_id as "partner_id:id",
#   'categ'||rel.category_id as "category_id:id"
#   from
#   res_partner_category_rel rel, res_partner r
#   where rel.partner_id=r.id
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
    res_partner r
    """
)

#   (select cat.name||'\N' from res_partner r1, res_partner_category cat,res_partner_category_rel rel where r1.id=rel.partner_id and rel.category_id=cat.id) as "category_id",
#   title,

#res.partner.address
import_sql(cr,
    'res.partner.address.csv',
    """
    select
    'address'||id as id,
    coalesce('partner'||partner_id,'partner_unknown') as "partner_id:id",
    name,
    street,
    zip,
    city,
    email,
    phone,
    type,
    mobile,
    fax
    from
    res_partner_address
    """
)
#   'country'||country as "country_id:id",


#auction.lot.category

import_sql(cr,
    'auction.lot.category.csv',
    """
    select
        'cat'||id as "id",
        name,
        active
    from
        auction_lot_category
    order by
        id
    """
)
#auction.dates.csv

import_sql(cr,
    'auction.dates.csv',
    """
    select
    
        'date'||id as "id",
        'Auction'||id as "name",
        expo1,
        expo2,
        'auction_db.account'||acc_expense as "acc_expense:id",
        'auction_db.account'||acc_income as "acc_income:id",
        coalesce(state,'draft') as "state",
        auction1,
        auction2,
        'account.expenses_journal' as "journal_seller_id:id",
        'account.sales_journal' as "journal_id:id",
        'auction_db.aaa_un' as "account_analytic_id:id"
        
    from
        auction_dates
    order by
        id
    """
)

# auction.artist.csv

import_sql(cr,
    'auction.artists.csv',
    """
    select
        'artist'||id as "id",
        name,
        biography,
        birth_death_dates
        
    from
        auction_artists
    order by
        id
    """
)


# auction.deposit.csv

import_sql(cr,
    'auction.deposit.csv',
    """
    select
        'deposit'||id as "id",
        name,
        date_dep,
        coalesce('auction_db.partner'||partner_id,'auction_db.partner_unknown') as "partner_id:id",
        method,
        'auction_db.tax'||tax_id as "tax_id:id",
        total_neg
        
    from
        auction_deposit
    order by
        id
    """
)


#lot 
import_sql(cr,
    'auction.lots.csv',
    """
    select
        'lot'||l.id as id,      
        'auction_db2.date'||l.auction_id as "auction_id:id",
        'auction_db2.deposit'||l.bord_vnd_id as "bord_vnd_id:id",
        l.name,
        l.name2,
        l.author_right,
        l.lot_est1,
        l.lot_est1,
        l.lot_local,
        l.artist_id,
        l.artist2_id,
        l.important,
        l.obj_desc,
        l.obj_num,
        l.obj_ret,
        l.obj_comm,
        l.obj_price,
        l.ach_avance,
        l.ach_login,
        'auction_db.partner'||l.ach_uid as "ach_uid:id",
        l.ach_emp,
        l.vnd_lim,
        l.vnd_lim_net,
        coalesce(l.state,'draft') as "state",
        'auction_db.product_product_unknown' as "product_id:id" 
    from
        auction_lots l join auction_dates d on (l.auction_id=d.id) join auction_deposit o on (l.bord_vnd_id=o.id) where d.expo2 like '2007%' 
    order by
        l.id
    """
)


#       'auction_db.invoice'||ach_inv_id as "ach_inv_id:id",
#       'auction_db.invoice'||ach_inv_id as "sel_inv_id:id",

def _deposit(cr, rec):
    if not rec[3]:
        rec[3] = '6025'
    return rec




# 'invoice'||invoice_id as "invoice_id:id",
import_sql(cr,
    'account.invoice.csv',
    """
    select
        'invoice'||id as "id",
        comment,
        date_due,
        number,
        'base.main_company' as "company_id:id",
        'auction_db.address'||address_invoice_id as "address_invoice_id:id",
        'auction_db.partner'||partner_id as "partner_id:id",
        state,
        type,
        'auction_db.account'||account_id as "account_id:id",
        date_invoice,
        name,
        'auction_db.address'||address_contact_id as "address_contact_id:id"
    from
        account_invoice
    order by
        id
    """
)

import_sql(cr,
    'account.invoice.line.csv',
    """
    select
        name,
        'invoice'||invoice_id as "invoice_id:id",
        price_unit,
        'auction_db.account'||account_id as "account_id:id",
        quantity
    from
        account_invoice_line
    order by
        id
    """
)

#auction.bid.csv

import_sql(cr,
    'auction.bid.csv',
    """
    select
        'bid'||b.id as "id",
        'date'||b.auction_id as "auction_id:id",
        coalesce('auction_db.partner'||b.partner_id,'auction_db.partner_unknown') as "partner_id:id",
        b.name,
        b.contact_tel 
    from
        auction_bid b join auction_dates d on (b.auction_id=d.id) where d.expo2 like '2007%'
    order by
        b.id
    """
)


#auction.bid_line.csv
import_sql(cr,
    'auction.bid_line.csv',
    """
    select 
        line.name,
        'auction_db2.bid'||line.bid_id as "bid_id:id",
        'auction_db3.lot'||line.lot_id as "lot_id:id",
        line.price,
        line.call
        
    from
        auction_bid_line line join auction_bid b on (b.id=line.bid_id) join auction_lots lot on (lot.id=line.lot_id) join auction_deposit o on (lot.bord_vnd_id=o.id)  join auction_dates d on (lot.auction_id=d.id) where d.expo2 like '2007%' and o.date_dep like '2007%'
    order by
        line.id
    """
)






cr.close()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

