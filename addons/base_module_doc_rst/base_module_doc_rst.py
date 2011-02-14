# -*- encoding: utf-8 -*-
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
import os
import pydot
import base64

import report
from osv import fields, osv
import addons

class module(osv.osv):
    _inherit = 'ir.module.module'
    _description = 'Module With Relationship Graph'
    _columns = {
        'file_graph': fields.binary('Relationship Graph'),
            }

    def _get_graphical_representation(self, cr, uid, model_ids, level=1, context=None):
        obj_model = self.pool.get('ir.model')
        if level == 0:
            return tuple()
        relation = []
        for id in model_ids:
            model_data = obj_model.browse(cr, uid, id, context=context)
            for field in (f for f in model_data.field_id if f.ttype in ('many2many', 'many2one', 'one2many')):
                relation.append((model_data.model, field.name, field.ttype, field.relation, field.field_description))
                new_model_ids = obj_model.search(cr, uid, [('model', '=', field.relation)], context=context)
                if new_model_ids:
                    model = obj_model.read(cr, uid, new_model_ids, ['id', 'name'], context=context)[0]
                    relation.extend(self._get_graphical_representation(cr, uid, model['id'], level - 1))
        return tuple(relation)

    def _get_structure(self, relations, main_element):
        res = {}
        for rel in relations:
            # if we have to display the string along with field name then uncomment the first line n comment the second line
            res.setdefault(rel[0], set()).add(rel[1])
            res.setdefault(rel[3], set())
        val = []
        for obj, fields in res.items():
            val.append('"%s" [%s label="{<id>%s|%s}"];' % (obj,
                                                       obj in main_element and 'fillcolor=yellow, style="filled,rounded"' or "",
                                                       obj,
                                                       "|".join(["<%s> %s" % (fn, fn) for fn in fields])))
        return "\n".join(val)

    def _get_arrow(self, field_type='many2one'):
        return {
            'many2one': 'arrowtail="none" arrowhead="normal" color="red" label="m2o"',
            'many2many': 'arrowtail="crow" arrowhead="crow" color="green" label="m2m"',
            'one2many': 'arrowtail="none" arrowhead="crow" color="blue" label="o2m"',
        }[field_type]

    def get_graphical_representation(self, cr, uid, model_ids, context=None):
        obj_model = self.pool.get('ir.model')
        if context is None:
            context = {}
        res = {}
        models = []
        for obj in obj_model.browse(cr, uid, model_ids, context=context):
            models.append(obj.model)
        relations = set(self._get_graphical_representation(cr, uid, model_ids, context.get('level', 1)))
        res[obj.model] = "digraph G {\nnode [style=rounded, shape=record];\n%s\n%s }" % (
                self._get_structure(relations, models),
                ''.join('"%s":%s -> "%s":id:n [%s]; // %s\n' % (m, fn, fr, self._get_arrow(ft),ft) for m, fn, ft, fr, fl in relations),
            )
        return res

    def _get_module_objects(self, cr, uid, module, context=None):
        obj_model = self.pool.get('ir.model')
        obj_mod_data = self.pool.get('ir.model.data')
        obj_ids = []
        model_data_ids = obj_mod_data.search(cr, uid, [('module', '=', module), ('model', '=', 'ir.model')], context=context)
        model_ids = []
        for mod in obj_mod_data.browse(cr, uid, model_data_ids, context=context):
            model_ids.append(mod.res_id)
        models = obj_model.browse(cr, uid, model_ids, context=context)
        map(lambda x: obj_ids.append(x.id),models)
        return obj_ids

    def get_relation_graph(self, cr, uid, module_name, context=None):
        if context is None: context = {}
        object_ids = self._get_module_objects(cr, uid, module_name, context=context)
        if not object_ids:
            return {'module_file': False}
        context.update({'level': 1})
        dots = self.get_graphical_representation(cr, uid, object_ids, context=context)
        # todo: use os.realpath
        file_path = addons.get_module_resource('base_module_doc_rst')
        path_png = file_path + "/module.png"
        for key, val in dots.items():
           path_dotfile = file_path + "/%s.dot" % (key,)
           fp = file(path_dotfile, "w")
           fp.write(val)
           fp.close()
        os.popen('dot -Tpng' +' '+ path_dotfile + ' '+ '-o' +' ' + path_png)
        fp = file(path_png, "r")
        x = fp.read()
        fp.close()
        os.popen('rm ' + path_dotfile + ' ' + path_png)
        return {'module_file': base64.encodestring(x)}

module()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

