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

from report.interface import report_int
import netsvc
import openerp.pooler

class report_artistlot(report_int):
    def __init__(self, name):
        report_int.__init__(self, name)

    def create(self, cr, uid, ids, datas, context):
        pool = pooler.get_pool(cr.dbname)
        lots = pool.get('auction.lots').read(cr, uid, ids, ['artist_id'])
        artists = []
        for lot in lots:
            if lot['artist_id'] and lot['artist_id'] not in artists:
                artists.append(lot['artist_id'][0])

        if not len(artists):
            raise 'UserError', 'Objects '

        datas['ids'] = artists

        self._obj_report = netsvc.LocalService('report.report.auction.artists')
        return self._obj_report.create(cr, uid, artists, datas, context)

    def result(self):
        return self._obj_report.result()

report_artistlot('report.auction.artists_lots')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

