# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: print_instance.py 8595 2008-06-16 13:00:21Z stw $
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


import time, os

import netsvc
import report,pooler,tools

import processus_print
import Image


class report_graph_instance(object):
    def __init__(self, cr, uid, ids, data):
        current_object = 'sale.order'
        pool = pooler.get_pool(cr.dbname)
        for processus in pool.get('processus.processus').browse(cr, uid, ids):
            nodes = {}
            start = []
            transitions = {}
            for node in processus.node_ids:
                nodes[node.id] = node
                if node.flow_start:
                    start.append(node.id)
                for tr in node.transition_out:
                    transitions[tr.id] = tr
            g = tools.graph(nodes.keys(), map(lambda x: (x.node_from_id.id,x.node_to_id.id), transitions.values()))
            g.process(start)
            g.scale(250,250, 100, 10)

            img = Image.new('RGB',(1024,768),'#ffffff')
            g2 = processus_print.graph(img)
            positions = g.result
            for name,node in positions.items():
                start_color = (nodes[name].model_id.model==current_object)
                g2.node(node['y'],node['x'], {
                    'title': nodes[name].name,
                    'menu': nodes[name].menu_id.complete_name
                }, start_color=start_color)
            for name,transition in transitions.items():
                if transition.transition_ids:
                    g2.arrow_role((positions[transition.node_from_id.id]['y'], positions[transition.node_from_id.id]['x']),
                        (positions[transition.node_to_id.id]['y'], positions[transition.node_to_id.id]['x']))
                g2.arrow((positions[transition.node_from_id.id]['y'], positions[transition.node_from_id.id]['x']),
                    (positions[transition.node_to_id.id]['y'], positions[transition.node_to_id.id]['x']))
        img.save('/tmp/a.pdf')
        self.result = file('/tmp/a.pdf').read()
        self.done = True

    def is_done(self):
        return self.done

    def get(self):
        if self.done:
            return self.result
        else:
            return None

class report_graph(report.interface.report_int):
    def __init__(self, name, table):
        report.interface.report_int.__init__(self, name)
        self.table = table

    def result(self):
        if self.obj.is_done():
            return (True, self.obj.get(), 'pdf')
        else:
            return (False, False, False)

    def create(self, cr, uid, ids, data, context={}):
        self.obj = report_graph_instance(cr, uid, ids, data)
        return (self.obj.get(), 'pdf')

report_graph('report.processus.processus.print', 'processus.processus')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

