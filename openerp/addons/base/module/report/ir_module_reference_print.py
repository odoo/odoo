# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import time

from openerp.report import report_sxw

class ir_module_reference_print(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(ir_module_reference_print, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'findobj': self._object_find,
            'objdoc': self._object_doc,
            'objdoc2': self._object_doc2,
            'findflds': self._fields_find,
        })
    def _object_doc(self, obj):
        modobj = self.pool.get(obj)
        strdocs= modobj.__doc__
        if not strdocs:
            return None
        else:
            strdocs=strdocs.strip().splitlines(True)
        res = ''
        for stre in strdocs:
            if not stre or stre.isspace():
                break
            res += stre
        return res

    def _object_doc2(self, obj):
        modobj = self.pool.get(obj)
        strdocs= modobj.__doc__
        if not strdocs:
            return None
        else:
            strdocs=strdocs.strip().splitlines(True)
        res = []
        fou = False
        for stre in strdocs:
            if fou:
                res.append(stre.strip())
            elif not stre or stre.isspace():
                fou = True
        return res

    def _object_find(self, module):
        ids2 = self.pool.get('ir.model.data').search(self.cr, self.uid, [('module','=',module), ('model','=','ir.model')])
        ids = []
        for mod in self.pool.get('ir.model.data').browse(self.cr, self.uid, ids2):
            ids.append(mod.res_id)
        modobj = self.pool.get('ir.model')
        return modobj.browse(self.cr, self.uid, ids)

    def _fields_find(self, obj):
        modobj = self.pool.get(obj)
        res = modobj.fields_get(self.cr, self.uid).items()
        res.sort()
        return res

report_sxw.report_sxw('report.ir.module.reference', 'ir.module.module',
        'addons/base/module/report/ir_module_reference.rml',
        parser=ir_module_reference_print, header=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

