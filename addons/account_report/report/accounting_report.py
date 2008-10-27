# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

import pooler
import time
from report import report_sxw


class accounting_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(accounting_report, self).__init__(cr, uid, name, context)
        self.ret_list = []
        self.localcontext.update({
            'time': time,
            'childs':self.process
        })

    def process(self,id,level=0):
        res = pooler.get_pool(self.cr.dbname).get('account.report.report').read(self.cr,self.uid,[id])
        ret_dict={
            'name':res[0]['name'],
            'code':res[0]['code'],
            'amount':res[0]['amount'],
            'note':res[0]['note'],
            'level': level,
#            'color_font':res[0]['color_font'],
#            'color_back':res[0]['color_back'],
        }

        self.ret_list.append(ret_dict)
        for child_id in res[0]['child_ids']:
                self.process(child_id,level+1)
        return self.ret_list


report_sxw.report_sxw('report.accounting.report', 'account.report.report',
        'addons/account_report/report/accounting_report.rml',
        parser=accounting_report, header=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

