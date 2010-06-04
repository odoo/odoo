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
from lxml import etree
from tools import graph
from tools.safe_eval import safe_eval as eval
import tools
import netsvc
import os

def _check_xml(self, cr, uid, ids, context={}):
    for view in self.browse(cr, uid, ids, context):
        eview = etree.fromstring(view.arch.encode('utf8'))
        frng = tools.file_open(os.path.join('base','rng','view.rng'))
        relaxng_doc = etree.parse(frng)
        relaxng = etree.RelaxNG(relaxng_doc)
        if not relaxng.validate(eview):
            logger = netsvc.Logger()
            logger.notifyChannel('init', netsvc.LOG_ERROR, 'The view does not fit the required schema !')
            logger.notifyChannel('init', netsvc.LOG_ERROR, tools.ustr(relaxng.error_log.last_error))
            return False
    return True

class view_custom(osv.osv):
    _name = 'ir.ui.view.custom'
    _columns = {
        'ref_id': fields.many2one('ir.ui.view', 'Original View'),
        'user_id': fields.many2one('res.users', 'User'),
        'arch': fields.text('View Architecture', required=True),
    }
view_custom()

class view(osv.osv):
    _name = 'ir.ui.view'
    _columns = {
        'name': fields.char('View Name',size=64,  required=True),
        'model': fields.char('Object', size=64, required=True),
        'priority': fields.integer('Priority', required=True),
        'type': fields.selection((
            ('tree','Tree'),
            ('form','Form'),
            ('mdx','mdx'),
            ('graph', 'Graph'),
            ('calendar', 'Calendar'),
            ('diagram','Diagram'),
            ('gantt', 'Gantt'),
            ('search','Search')), 'View Type', required=True),
        'arch': fields.text('View Architecture', required=True),
        'inherit_id': fields.many2one('ir.ui.view', 'Inherited View', ondelete='cascade'),
        'field_parent': fields.char('Child Field',size=64),
        'xml_id': fields.function(osv.osv.get_xml_id, type='char', size=128, string="XML ID",
                                  method=True),
    }
    _defaults = {
        'arch': '<?xml version="1.0"?>\n<tree string="Unknwown">\n\t<field name="name"/>\n</tree>',
        'priority': 16
    }
    _order = "priority"
    _constraints = [
        (_check_xml, 'Invalid XML for View Architecture!', ['arch'])
    ]

    def read(self, cr, uid, ids, fields=None, context={}, load='_classic_read'):

        if not isinstance(ids, (list, tuple)):
            ids = [ids]

        result = super(view, self).read(cr, uid, ids, fields, context, load)

        for rs in result:
            if rs.get('model') == 'board.board':
                cr.execute("select id,arch,ref_id from ir_ui_view_custom where user_id=%s and ref_id=%s", (uid, rs['id']))
                oview = cr.dictfetchall()
                if oview:
                    rs['arch'] = oview[0]['arch']


        return result

    def write(self, cr, uid, ids, vals, context={}):

        if not isinstance(ids, (list, tuple)):
            ids = [ids]

        exist = self.pool.get('ir.ui.view').browse(cr, uid, ids[0])
        if exist.model == 'board.board' and 'arch' in vals:
            vids = self.pool.get('ir.ui.view.custom').search(cr, uid, [('user_id','=',uid), ('ref_id','=',ids[0])])
            vals2 = {'user_id': uid, 'ref_id': ids[0], 'arch': vals.pop('arch')}

            # write fields except arch to the `ir.ui.view`
            result = super(view, self).write(cr, uid, ids, vals, context)

            if not vids:
                self.pool.get('ir.ui.view.custom').create(cr, uid, vals2)
            else:
                self.pool.get('ir.ui.view.custom').write(cr, uid, vids, vals2)

            return result

        return super(view, self).write(cr, uid, ids, vals, context)

    def graph_get(self, cr, uid, id, model, node_obj, conn_obj, src_node, des_node,label,scale,context={}):
        if not label:
            label = []
        nodes=[]
        nodes_name=[]
        transitions=[]
        start=[]
        tres={}
        labels={}
        no_ancester=[]
        blank_nodes = []

        _Model_Obj=self.pool.get(model)
        _Node_Obj=self.pool.get(node_obj)
        _Arrow_Obj=self.pool.get(conn_obj)

        for model_key,model_value in _Model_Obj._columns.items():
                if model_value._type=='one2many':
                    if model_value._obj==node_obj:
                        _Node_Field=model_key
                        _Model_Field=model_value._fields_id
                    flag=False
                    for node_key,node_value in _Node_Obj._columns.items():
                        if node_value._type=='one2many':
                             if node_value._obj==conn_obj:
                                 if src_node in _Arrow_Obj._columns and flag:
                                    _Source_Field=node_key
                                 if des_node in _Arrow_Obj._columns and not flag:
                                    _Destination_Field=node_key
                                    flag = True

        datas = _Model_Obj.read(cr, uid, id, [],context)
        for a in _Node_Obj.read(cr,uid,datas[_Node_Field],[]):
            if a[_Source_Field] or a[_Destination_Field]:
                nodes_name.append((a['id'],a['name']))
                nodes.append(a['id'])
            else:
                blank_nodes.append({'id': a['id'],'name':a['name']})

            if a.has_key('flow_start') and a['flow_start']:
                start.append(a['id'])
            else:
                if not a[_Source_Field]:
                    no_ancester.append(a['id'])
            for t in _Arrow_Obj.read(cr,uid, a[_Destination_Field],[]):
                transitions.append((a['id'], t[des_node][0]))
                tres[str(t['id'])] = (a['id'],t[des_node][0])
                label_string = ""
                if label:
                    for lbl in eval(label):
                        if t.has_key(str(lbl)) and str(t[lbl])=='False':
                            label_string = label_string + ' '
                        else:
                            label_string = label_string + " " + t[lbl]
                labels[str(t['id'])] = (a['id'],label_string)
        g  = graph(nodes, transitions, no_ancester)
        g.process(start)
        g.scale(*scale)
        result = g.result_get()
        results = {}
        for node in nodes_name:
            results[str(node[0])] = result[node[0]]
            results[str(node[0])]['name'] = node[1]
        return {'nodes': results, 'transitions': tres, 'label' : labels, 'blank_nodes': blank_nodes}
view()

class view_sc(osv.osv):
    _name = 'ir.ui.view_sc'
    _columns = {
        'name': fields.char('Shortcut Name', size=64, required=True),
        'res_id': fields.many2one('ir.ui.menu','Resource Ref.', ondelete='cascade'),
        'sequence': fields.integer('Sequence'),
        'user_id': fields.many2one('res.users', 'User Ref.', required=True, ondelete='cascade'),
        'resource': fields.char('Resource Name', size=64, required=True)
    }

    def get_sc(self, cr, uid, user_id, model='ir.ui.menu', context={}):
        ids = self.search(cr, uid, [('user_id','=',user_id),('resource','=',model)], context=context)
        return self.read(cr, uid, ids, ['res_id','name'], context=context)

    _order = 'sequence'
    _defaults = {
        'resource': lambda *a: 'ir.ui.menu',
        'user_id': lambda obj, cr, uid, context: uid,
    }
    _sql_constraints = [
        ('shortcut_unique', 'unique(res_id, user_id)', 'Shortcut for this menu already exists!'),
    ]
        
view_sc()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

