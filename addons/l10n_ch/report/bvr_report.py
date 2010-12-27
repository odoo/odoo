# -*- coding: utf-8 -*-
#
#  bvr.py
#  l10n_ch
#
#  Created by Nicolas Bessi based on Credric Krier contribution
#
#  Copyright (c) 2009 CamptoCamp. All rights reserved.
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

import re
import time

from report import report_sxw
from tools import mod10r
import logging
log = logging.getLogger('init')

try:
    this_module = 'l10n_ch'
    from report.render.rml2pdf import customfonts
    from addons import get_module_resource
    ocrb_fname = get_module_resource(this_module, 'report', 'ocrbb.ttf')
    if not ocrb_fname:
        raise OSError("Cannot find ocrbb.ttf in %s resources", this_module)
    customfonts.CustomTTFonts.append( ('ocrb', 'ocrb', ocrb_fname , None ) )
    log.debug("module: %s registered custom OCR-B font at %s", this_module, ocrb_fname)
except ImportError:
    log.debug("Import error", exc_info=True)
    pass
except Exception, e:
    log.exception("Cannot register custom font")

class account_invoice_bvr(report_sxw.rml_parse):
    """Report class that Allows to print BVR payement vector"""
    def __init__(self, cr, uid, name, context):
        super(account_invoice_bvr, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'user':self.pool.get("res.users").browse(cr,uid,uid),
            'mod10r': mod10r,
            '_space': self._space,
            '_get_ref': self._get_ref,
            'comma_me': self.comma_me,
            'format_date': self._get_and_change_date_format_for_swiss,
            'bvr_format': self._bvr_format,
        })
    def _get_and_change_date_format_for_swiss (self,date_to_format):
        date_formatted=''
        if date_to_format and date_to_format != 'False':  # happens: str(False)
            date_formatted = time.strptime(date_to_format,'%Y-%m-%d').strftime('%d.%m.%Y')
        return date_formatted

    def comma_me(self,amount):
        if amount is False or amount is None :
            return ''
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

    def _space(self,nbr, nbrspc=5):
        res = ''
        for i in range(len(nbr)):
            res = res + nbr[i]
            if not (i-1) % nbrspc:
                res = res + ' '
        return res

    def _get_ref(self, o):
        res = ''
        if o.partner_bank_id.bvr_adherent_num:
            res = o.partner_bank_id.bvr_adherent_num
        invoice_number = ''
        if o.number:
            invoice_number = re.sub('[^0-9]', '0', o.number)
        return mod10r(res + invoice_number.rjust(26-len(res), '0'))

    def _bvr_format(self, o):
        bvr_number = o.partner_bank_id.bvr_number
        if (not bvr_number) or '-' not in bvr_number:
            return '**** *******' # FIXME, what is the official "n/a" string, 
                                  # should we raise exception instead?
        return bvr_number.split('-')[0] + \
            (str(bvr_number.split('-')[1])).rjust(6,'0') + \
            bvr_number.split('-')[2]

report_sxw.report_sxw(
    'report.l10n_ch.bvr',
    'account.invoice',
    'addons/l10n_ch/report/bvr_report.rml',
    parser=account_invoice_bvr,
    header=False)

report_sxw.report_sxw(
    'report.l10n_ch.invoice.bvr',
    'account.invoice',
    'addons/l10n_ch/report/bvr_invoice_report.rml',
    parser=account_invoice_bvr,
    header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
