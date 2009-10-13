# -*- coding: utf-8 -*-
#
#  wizzard_bvr.py
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

import wizard
import pooler
import re
from tools.translate import _

def _check(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    invoice_obj = pool.get('account.invoice')
    for invoice in invoice_obj.browse(cr, uid, data['ids'], context):
        if not invoice.partner_bank:
            raise wizard.except_wizard(_('UserError'),
                    _('No bank specified on invoice:\n%s') % \
                            invoice_obj.name_get(cr, uid, [invoice.id], context=context)[0][1])

        if not re.compile('[0-9][0-9]-[0-9]{3,6}-[0-9]').match(
                invoice.partner_bank.bvr_number or ''):
            raise wizard.except_wizard(_('UserError'),
                    _('Your bank BVR number should be of the form 0X-XXX-X!\n' \
                            'Please check your company ' \
                            'information for the invoice:\n%s') % \
                            invoice_obj.name_get(cr, uid, [invoice.id], context=context)[0][1])

        if invoice.partner_bank.bvr_adherent_num \
                and not re.compile('[0-9]*$').match(
                        invoice.partner_bank.bvr_adherent_num):
            raise wizard.except_wizard(_('UserError'),
                    _('Your bank BVR adherent number must contain exactly seven' \
                            'digits!\nPlease check your company ' \
                            'information for the invoice:\n%s') % \
                            invoice_obj.name_get(cr, uid, [invoice.id], context=context)[0][1])
    return {}

class wizard_report(wizard.interface):
    states = {
        'init': {
            'actions': [_check], 
            'result': {'type':'print', 'report':'l10n_ch.bvr', 'state':'end'}
        }
    }
wizard_report('l10n_ch.bvr.check')

class ReportInvoiceBVRCheck(wizard.interface):
    states = {
        'init': {
            'actions': [_check],
            'result': {'type':'print', 'report':'l10n_ch.invoice.bvr', 'state':'end'}
        }
    }
ReportInvoiceBVRCheck('l10n_ch.invoice.bvr.check')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
