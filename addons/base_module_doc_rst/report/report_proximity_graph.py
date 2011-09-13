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
import time, os
import pydot

import report,pooler,tools

class report_graph(report.interface.report_int):
    def __init__(self, name, table):
        report.interface.report_int.__init__(self, name)
        self.table = table

    def get_proximity_graph(self, cr, uid, module_id, context=None):
        pool_obj = pooler.get_pool(cr.dbname)
        module_obj = pool_obj.get('ir.module.module')
        nodes = [('base','unknown')]
        edges = []
        def get_dpend_module(module_id):
            module_record = module_obj.browse(cr, uid, module_id, context=context)
            if module_record.name not in nodes:
                # Add new field ir.module.module object in server side. field name = module_type/
                nodes.append((module_record.name, "unknown"))
            if module_record.dependencies_id:
                for depen in module_record.dependencies_id:
                    if (module_record.name,depen.name) not in edges:
                        edges.append((module_record.name,depen.name))
                    if depen.name == "base":
                        continue
                    id = module_obj.browse(cr, uid, module_obj.search(cr, uid, [('name', '=' ,depen.name)]), context=context)
                    if id:
                        get_dpend_module(id[0].id)
        get_dpend_module(module_id)
        graph = pydot.Dot(graph_type='digraph',fontsize='10', label="\\nProximity Graph. \\n\\nGray Color-Official Modules, Red  Color-Extra Addons Modules, Blue Color-Community Modules, Purple Color-Unknow Modules"
                                     , center='1')
        for node in nodes:
            if node[1] == "official":
                graph.add_node(pydot.Node(node[0], style="filled", fillcolor="lightgray"))
            elif node[1] == "extra_addons":
                graph.add_node(pydot.Node(node[0], style="filled", fillcolor="red"))
            elif node[1] == "community":
                graph.add_node(pydot.Node(node[0], style="filled", fillcolor="#000FFF"))
            elif node[1] == "unknown":
                graph.add_node(pydot.Node(node[0], style="filled", fillcolor="purple"))
        for edge in edges:
            graph.add_edge(pydot.Edge(edge[0], edge[1]))

        ps_string = graph.create(prog='dot', format='ps')
        if os.name == "nt":
            prog = 'ps2pdf.bat'
        else:
            prog = 'ps2pdf'

        args = (prog, '-', '-')
        input, output = tools.exec_command_pipe(*args)
        input.write(ps_string)
        input.close()
        return output.read()

    def create(self, cr, uid, ids, data, context=None):
        pdf_string = self.get_proximity_graph(cr, uid, data['id'])
        return (pdf_string, 'pdf')

report_graph('report.proximity.graph', 'ir.module.module')