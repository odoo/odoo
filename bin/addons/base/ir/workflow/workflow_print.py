import psycopg
import pydot

wkf_id = 193

db = psycopg.connect('dbname=terp', serialize=0)
cr=db.cursor()

def graph_get(cr, graph, wkf_id, nested=True):
	cr.execute('select * from wkf_activity where wkf_id=%d', (wkf_id,))
	nodes = cr.dictfetchall()
	activities = {}
	actfrom = {}
	actto = {}
	for n in nodes:
		activities[n['id']] = n
		if n['subflow_id'] and nested:
			cr.execute('select * from wkf where id=%d', (n['subflow_id'],))
			wkfinfo = cr.dictfetchone()
			graph2 = pydot.Cluster('subflow'+str(n['subflow_id']), fontsize=10, label = "Subflow: "+n['name']+'\\nOSV: '+wkfinfo['osv'])
			(s1,s2) = graph_get(cr, graph2, n['subflow_id'], nested)
			graph.add_subgraph(graph2)
			actfrom[n['id']] = s2
			actto[n['id']] = s1
		else:
			args = {}
			if n['flow_start'] or n['flow_stop']:
				args['style']='filled'
				args['color']='lightgrey'
			args['label']=n['name']
			if n['action']:
				args['label']+='\\n'+n['action']
			if n['subflow_id']:
				args['shape'] = 'box'
			graph.add_node(pydot.Node(n['id'], **args))
			actfrom[n['id']] = n['id']
			actto[n['id']] = n['id']
	cr.execute('select * from wkf_transition where act_from in ('+','.join(map(lambda x: str(x['id']),nodes))+')')
	transitions = cr.dictfetchall()
	for t in transitions:
		args = {}
		args['label'] = str(t['condition'])
		if t['signal']:
			args['label'] += '\\n'+str(t['signal'])
			args['style'] = 'bold'

		if activities[t['act_from']]['split_mode']=='AND':
			args['arrowtail']='box'
		elif str(activities[t['act_from']]['split_mode'])=='OR ':
			args['arrowtail']='inv'

		if activities[t['act_to']]['join_mode']=='AND':
			args['arrowhead']='crow'

		graph.add_edge(pydot.Edge(actfrom[t['act_from']],actto[t['act_to']], fontsize=8, **args))
	nodes = cr.dictfetchall()
	cr.execute('select id from wkf_activity where flow_start=True limit 1')
	start = cr.fetchone()[0]
	cr.execute('select id from wkf_activity where flow_stop=True limit 1')
	stop = cr.fetchone()[0]
	return (start,stop)

cr.execute('select * from wkf where id=%d', (wkf_id,))
wkfinfo = cr.dictfetchone()
graph = pydot.Dot(fontsize = 16, label = "\\n\\nWorkflow: %s\\n OSV: %s"% (wkfinfo['name'],wkfinfo['osv']))
graph_get(cr, graph, wkf_id, True)
graph.write_ps('/tmp/a.ps', prog='dot')

