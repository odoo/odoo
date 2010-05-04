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

import time, os

import netsvc
import report,pooler,tools


def graph_get(cr, graph, wkf_id, nested=False, workitem={}):
    import pydot
    cr.execute('select * from wkf_activity where wkf_id=%s', (wkf_id,))
    nodes = cr.dictfetchall()
    activities = {}
    actfrom = {}
    actto = {}
    for n in nodes:
        activities[n['id']] = n
        if n['subflow_id'] and nested:
            cr.execute('select * from wkf where id=%s', (n['subflow_id'],))
            wkfinfo = cr.dictfetchone()
            graph2 = pydot.Cluster('subflow'+str(n['subflow_id']), fontsize='12', label = """\"Subflow: %s\\nOSV: %s\"""" % ( n['name'], wkfinfo['osv']) )
            (s1,s2) = graph_get(cr, graph2, n['subflow_id'], nested,workitem)
            graph.add_subgraph(graph2)
            actfrom[n['id']] = s2
            actto[n['id']] = s1
        else:
            args = {}
            if n['flow_start'] or n['flow_stop']:
                args['style']='filled'
                args['color']='lightgrey'
            args['label']=n['name']
            if n['subflow_id']:
                args['shape'] = 'box'
            if n['id'] in workitem:
                args['label']+='\\nx '+str(workitem[n['id']])
                args['color'] = "red"
            graph.add_node(pydot.Node(n['id'], **args))
            actfrom[n['id']] = (n['id'],{})
            actto[n['id']] = (n['id'],{})
    cr.execute('select * from wkf_transition where act_from in ('+','.join(map(lambda x: str(x['id']),nodes))+')')
    transitions = cr.dictfetchall()
    for t in transitions:
        args = {}
        args['label'] = str(t['condition']).replace(' or ', '\\nor ').replace(' and ', '\\nand ')
        if t['signal']:
            args['label'] += '\\n'+str(t['signal'])
            args['style'] = 'bold'

        if activities[t['act_from']]['split_mode']=='AND':
            args['arrowtail']='box'
        elif str(activities[t['act_from']]['split_mode'])=='OR ':
            args['arrowtail']='inv'

        if activities[t['act_to']]['join_mode']=='AND':
            args['arrowhead']='crow'

        activity_from = actfrom[t['act_from']][1].get(t['signal'], actfrom[t['act_from']][0])
        activity_to = actto[t['act_to']][1].get(t['signal'], actto[t['act_to']][0])
        graph.add_edge(pydot.Edge( str(activity_from) ,str(activity_to), fontsize='10', **args))
    nodes = cr.dictfetchall()
    cr.execute('select id from wkf_activity where flow_start=True and wkf_id=%s limit 1', (wkf_id,))
    start = cr.fetchone()[0]
    cr.execute("select 'subflow.'||name,id from wkf_activity where flow_stop=True and wkf_id=%s", (wkf_id,))
    stop = cr.fetchall()
    if stop:
        stop = (stop[0][1], dict(stop))
    return ((start,{}),stop)


def graph_instance_get(cr, graph, inst_id, nested=False):
    workitems = {}
    cr.execute('select * from wkf_instance where id=%s', (inst_id,))
    inst = cr.dictfetchone()

    def workitem_get(instance):
        cr.execute('select act_id,count(*) from wkf_workitem where inst_id=%s group by act_id', (instance,))
        workitems = dict(cr.fetchall())

        cr.execute('select subflow_id from wkf_workitem where inst_id=%s', (instance,))
        for (subflow_id,) in cr.fetchall():
            workitems.update(workitem_get(subflow_id))
        return workitems
    graph_get(cr, graph, inst['wkf_id'], nested, workitem_get(inst_id))

#
# TODO: pas clean: concurrent !!!
#

class report_graph_instance(object):
    def __init__(self, cr, uid, ids, data):
        logger = netsvc.Logger()
        try:
            import pydot
        except Exception,e:
            logger.notifyChannel('workflow', netsvc.LOG_WARNING,
                    'Import Error for pydot, you will not be able to render workflows\n'
                    'Consider Installing PyDot or dependencies: http://dkbza.org/pydot.html')
            raise e
        self.done = False

        try:
            cr.execute('select * from wkf where osv=%s limit 1',
                    (data['model'],))
            wkfinfo = cr.dictfetchone()
            if not wkfinfo:
                ps_string = '''%PS-Adobe-3.0
/inch {72 mul} def
/Times-Roman findfont 50 scalefont setfont
1.5 inch 15 inch moveto
(No workflow defined) show
showpage'''
            else:
                cr.execute('SELECT id FROM wkf_instance \
                        WHERE res_id=%s AND wkf_id=%s \
                        ORDER BY state LIMIT 1',
                        (data['id'], wkfinfo['id']))
                inst_id = cr.fetchone()
                if not inst_id:
                    ps_string = '''%PS-Adobe-3.0
/inch {72 mul} def
/Times-Roman findfont 50 scalefont setfont
1.5 inch 15 inch moveto
(No workflow instance defined) show
showpage'''
                else:
                    inst_id = inst_id[0]
                    graph = pydot.Dot(fontsize='16', label="""\\\n\\nWorkflow: %s\\n OSV: %s""" % (wkfinfo['name'],wkfinfo['osv']),
                                      size='10.7, 7.3', center='1', ratio='auto', rotate='90', rankdir='LR'
                                     )
                    graph_instance_get(cr, graph, inst_id, data.get('nested', False))
                    ps_string = graph.create(prog='dot', format='ps')
        except Exception, e:
            import traceback, sys
            tb_s = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            logger.notifyChannel('workflow', netsvc.LOG_ERROR, 'Exception in call: ' + tb_s)
            # string is in PS, like the success message would have been
            ps_string = '''%PS-Adobe-3.0
/inch {72 mul} def
/Times-Roman findfont 50 scalefont setfont
1.5 inch 15 inch moveto
(No workflow available) show
showpage'''
        if os.name == "nt":
            prog = 'ps2pdf.bat'
        else:
            prog = 'ps2pdf'
        args = (prog, '-', '-')
        input, output = tools.exec_command_pipe(*args)
        input.write(ps_string)
        input.close()
        self.result = output.read()
        output.close()
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

report_graph('report.workflow.instance.graph', 'ir.workflow')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

