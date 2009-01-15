# -*- encoding: utf-8 -*-
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

import wizard
from osv import osv
import pooler
from tools.translate import _

import base64

form_rep = '''<?xml version="1.0"?>
<form string="Standard entries">
    <field name="module_file"/>
</form>'''


fields_rep = {
    'module_file': {'string': 'Save report', 'type': 'binary', 'required': True},
}

def get_detail(self, cr, uid, datas, context={}):
    data = pooler.get_pool(cr.dbname).get('quality.check.detail').browse(cr, uid, datas['id'])
    data.detail = base64.encodestring(data.detail)
    return {'module_file':data.detail}

class save_report(wizard.interface):
    states = {
        'init': {
            'actions': [get_detail],
            'result': {'type': 'form', 'arch':form_rep, 'fields':fields_rep, 'state':[('end','Cancel')]}
        },
    }
save_report('quality_detail_save')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

