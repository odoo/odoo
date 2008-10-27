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

import wizard
import pooler

form = '''<?xml version="1.0"?>
<form string="Print Central Journal">
    <field name="journal_id"/>
    <field name="period_id"/>
</form>'''

fields = {
  'journal_id': {'string': 'Journal', 'type': 'many2many', 'relation': 'account.journal', 'required': True},
  'period_id': {'string': 'Period', 'type': 'many2many', 'relation': 'account.period', 'required': True},
}


class wizard_print_journal(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': form, 'fields': fields, 'state': (('end', 'Cancel'), ('print', 'Print'))},
        },
        'print': {
            'actions': [],
            'result': {'type':'print', 'report':'account.central.journal.wiz', 'state':'end'},
        },
    }
wizard_print_journal('account.central.journal.report')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

