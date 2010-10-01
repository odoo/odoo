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

from osv import fields,osv
from osv.orm import browse_null
import ir
import report.custom
from tools.translate import _
from tools.safe_eval import safe_eval as eval
import netsvc

class report_custom_fields(osv.osv):
    _name = 'ir.report.custom.fields'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'field_child0': fields.many2one('ir.model.fields', 'Field child0', required=True),
        'fc0_operande': fields.many2one('ir.model.fields', 'Constraint'),
        'fc0_condition': fields.char('Condition', size=64),
        'fc0_op': fields.selection((('>','>'),('<','<'),('==','='),('in','in'),('gety,==','(year)=')), 'Relation'),
        'field_child1': fields.many2one('ir.model.fields', 'Field child1'),
        'fc1_operande': fields.many2one('ir.model.fields', 'Constraint'),
        'fc1_condition': fields.char('condition', size=64),
        'fc1_op': fields.selection((('>','>'),('<','<'),('==','='),('in','in'),('gety,==','(year)=')), 'Relation'),
        'field_child2': fields.many2one('ir.model.fields', 'Field child2'),
        'fc2_operande': fields.many2one('ir.model.fields', 'Constraint'),
        'fc2_condition': fields.char('condition', size=64),
        'fc2_op': fields.selection((('>','>'),('<','<'),('==','='),('in','in'),('gety,==','(year)=')), 'Relation'),
        'field_child3': fields.many2one('ir.model.fields', 'Field child3'),
        'fc3_operande': fields.many2one('ir.model.fields', 'Constraint'),
        'fc3_condition': fields.char('condition', size=64),
        'fc3_op': fields.selection((('>','>'),('<','<'),('==','='),('in','in'),('gety,==','(year)=')), 'Relation'),
        'alignment':  fields.selection((('left','left'),('right','right'),('center','center')), 'Alignment', required=True),
        'sequence': fields.integer('Sequence', required=True),
        'width': fields.integer('Fixed Width'),
        'operation': fields.selection((('none', 'None'),('calc_sum','Calculate Sum'),('calc_avg','Calculate Average'),('calc_count','Calculate Count'),('calc_max', 'Get Max'))),
        'groupby' : fields.boolean('Group By'),
        'bgcolor': fields.char('Background Color', size=64),
        'fontcolor': fields.char('Font color', size=64),
        'cumulate': fields.boolean('Accumulate')
    }
    _defaults = {
        'alignment': lambda *a: 'left',
        'bgcolor': lambda *a: 'white',
        'fontcolor': lambda *a: 'black',
        'operation': lambda *a: 'none',
    }
    _order = "sequence"

    def onchange_any_field_child(self, cr, uid, ids, field_id, level):
        if not(field_id):
            return {}
        next_level_field_name = 'field_child%d' % (level+1)
        next_level_operande = 'fc%d_operande' % (level+1)
        field = self.pool.get('ir.model.fields').browse(cr, uid, [field_id])[0]
        res = self.pool.get(field.model).fields_get(cr, uid, field.name)
        if res[field.name].has_key('relation'):
            cr.execute('select id from ir_model where model=%s', (res[field.name]['relation'],))
            (id,) = cr.fetchone() or (False,)
            if id:
                return {
                    'domain': {
                        next_level_field_name: [('model_id', '=', id)],
                        next_level_operande: [('model_id', '=', id)]
                    },
                    'required': {
                        next_level_field_name: True
                    }
                }
            else:
                netsvc.Logger().notifyChannel('web-services', netsvc.LOG_WARNING, _("Using a relation field which uses an unknown object"))
                return {'required': {next_level_field_name: True}}
        else:
            return {'domain': {next_level_field_name: []}}

    def get_field_child_onchange_method(level):
        return lambda self, cr, uid, ids, field_id: self.onchange_any_field_child(cr, uid, ids, field_id, level)

    onchange_field_child0 = get_field_child_onchange_method(0)
    onchange_field_child1 = get_field_child_onchange_method(1)
    onchange_field_child2 = get_field_child_onchange_method(2)
report_custom_fields()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

