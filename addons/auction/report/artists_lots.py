# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
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

from report.interface import report_int
import netsvc

class report_artistlot(report_int):
    def __init__(self, name):
        report_int.__init__(self, name)

    def create(self,cr, uid, ids, datas, context):
        service = netsvc.LocalService("object_proxy")
        lots = service.execute(cr.dbname,uid, 'auction.lots', 'read', ids, ['artist_id'])
        artists = []
        for lot in lots:
            if lot['artist_id'] and lot['artist_id'] not in artists:
                artists.append(lot['artist_id'][0])

        if not len(artists):
            raise 'UserError', 'Objects '

        datas['ids'] = artists

        self._obj_report = netsvc.LocalService('report.report.auction.artists')
        return self._obj_report.create(cr,uid, artists, datas, context)

    def result(self):
        return self._obj_report.result()

report_artistlot('report.auction.artists_lots')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

