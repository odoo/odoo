# -*- encoding: utf-8 -*-
#
#  bvr.py
#  l10n_ch
#
#  Created by Nicolas Bessi based on Credric Krier contribution
#
#  Copyright (c) 2010 CamptoCamp. All rights reserved.
##############################################################################
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
"""Report class that Allows to print BVR payement vector"""

import time
from report import report_sxw
from tools import mod10r
import re
import os 
import sys
import shutil
# from mx.DateTime import *

class AccountInvoiceBvr(report_sxw.rml_parse):
    """Report class that Allows to print BVR payement vector"""
    def __init__(self, cursor, uid, name, context):
        super(AccountInvoiceBvr, self).__init__(cursor, uid, name, context)
        self.copyocrbfile('addons/l10n_ch/report/ocrbb.ttf')
        self.localcontext.update({
            'time': time,
            'user':self.pool.get("res.users").browse(cursor, uid, uid),
            'mod10r': mod10r,
            '_space': self._space,
            '_get_ref': self._get_ref,
            'comma_me': self.comma_me,
            'police_absolute_path' : self.police_absolute_path,
            'copyocrbfile': self.copyocrbfile
        })
        
    #will be fixed in 5.0.10    
    def police_absolute_path(self, inner_path) :
        """Will get the ocrb police absolute path"""
        path = os.path.join(os.path.dirname(sys.argv[0]), inner_path)
        return  path
    # will be fix in 5.0.10   
    def copyocrbfile(self, ttffile):
        """Copy ocrb file"""
        src = self.police_absolute_path(ttffile)
        basefile = os.path.basename(src)
        dest = os.path.join('/tmp/', basefile)
        if not os.path.isfile(dest):
            try:
                shutil.copyfile(src, dest)
            except:
                """print ocrbfile was not copy in /tmp/ please 
                copy it manually from l10_ch/report"""
        
            

    def comma_me(self, amount):
        """Fast swiss number formatting"""
        if  type(amount) is float :
            amount = str('%.2f'%amount)
        else :
            amount = str(amount)
        orig = amount
        new = re.sub("^(-?\d+)(\d{3})", "\g<1>'\g<2>", amount)
        if orig == new:
            return new
        else:
            return self.comma_me(new)

    def _space(self, nbr, nbrspc=5):
        """Spaces * 5"""
        res = ''
        for i in range(len(nbr)):
            res = res + nbr[i]
            if not (i-1) % nbrspc:
                res = res + ' '
        return res

    def _get_ref(self, inv):
        """Retrieve ESR/BVR reference form invoice in order to print it"""
        res = ''
        if inv.partner_bank.bvr_adherent_num:
            res = inv.partner_bank.bvr_adherent_num
        invoice_number = ''
        if inv.number:
            invoice_number = re.sub('[^0-9]', '', inv.number)
        return mod10r(res + invoice_number.rjust(26-len(res), '0'))

report_sxw.report_sxw(
    'report.l10n_ch.bvr',
    'account.invoice',
    'addons/l10n_ch/report/bvr_report.rml',
    parser=AccountInvoiceBvr,
    header=False)

report_sxw.report_sxw(
    'report.l10n_ch.invoice.bvr',
    'account.invoice',
    'addons/l10n_ch/report/invoice_report.rml',
    parser=AccountInvoiceBvr,
    header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
