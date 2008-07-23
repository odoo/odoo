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

import time
from report import report_sxw

class ir_module_reference_print(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(ir_module_reference_print, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'findobj': self._object_find,
            'objdoc': self._object_doc,
            'findflds': self._fields_find,
        })
    def _object_doc(self, obj):
        modobj = self.pool.get(obj)
        return modobj.__doc__

    def _object_find(self, module):
        modobj = self.pool.get('ir.model')
        if module=='base':
            ids = modobj.search(self.cr, self.uid, [('model','=like','res%')])
            ids += modobj.search(self.cr, self.uid, [('model','=like','ir%')])
        else:
            ids = modobj.search(self.cr, self.uid, [('model','=like',module+'%')])
        return modobj.browse(self.cr, self.uid, ids)

    def _fields_find(self, obj):
        modobj = self.pool.get(obj)
        res = modobj.fields_get(self.cr, self.uid).items()
        return res

report_sxw.report_sxw('report.ir.module.reference', 'ir.module.module',
        'addons/base/module/report/ir_module_reference.rml',
        parser=ir_module_reference_print, header=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

