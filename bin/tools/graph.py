#!/usr/bin/python

class graph(object):
	def __init__(self, nodes, transitions):
		self.nodes = nodes
		trans = {}
		for t in transitions:
			trans.setdefault(t[0], [])
			trans[t[0]].append(t[1])
		self.transitions = trans
		self.result = {}
		self.levels = {}

	def process_ranking(self, node, level=0):
		if node not in self.result:
			self.result[node] = {'x': None, 'y':level}
		else:
			if level > self.result[node]['y']:
				self.result[node]['y'] = level
		for t in self.transitions.get(node, []):
			self.process_ranking(t, level+1)

	def preprocess_order(self):
		levels = {}
		for r in self.result:
			l = self.result[r]['y']
			levels.setdefault(l,[])
			levels[l].append(r)
		self.levels = levels

	def process_order(self, level):
		self.levels[level].sort(lambda x,y: cmp(self.result[x]['x'], self.result[y]['x']))
		for nodepos in range(len(self.levels[level])):
			node = self.levels[level][nodepos]
			if nodepos == 0:
				left = self.result[node]['x']- 0.5
			else:
				left = (self.result[node]['x'] + self.result[self.levels[level][nodepos-1]]['x']) / 2.0

			if nodepos == (len(self.levels[level])-1):
				right = self.result[node]['x'] + 0.5
			else:
				right = (self.result[node]['x'] +  self.result[self.levels[level][nodepos+1]]['x']) / 2.0


			if self.transitions.get(node, False):
				if len(self.transitions[node])==1:
					pos = (left+right)/2.0
					step = 0
				else:
					pos = left
					step = (-left+right) / (len(self.transitions[node])-1)

				for n2 in self.transitions[node]:
					self.result[n2]['x'] = pos
					pos += step

	def process(self, starting_node):
		pos = (len(starting_node) - 1.0)/2.0
		for s in starting_node:
			g.process_ranking(s)
			self.result[s]['x'] = pos
			pos += 1.0

		self.preprocess_order()

		for n in self.levels:
			self.process_order(n)

	def __str__(self):
		result = ''
		for l in self.levels:
			result += 'PosY: ' + str(l) + '\n'
			for node in self.levels[l]:
				result += '\tPosX: '+ str(self.result[node]['x']) + '  - Node:' + node + "\n"
		return result

	def scale(self, maxx, maxy, plusx2=0, plusy2=0):
		plusx = - min(map(lambda x: x['x'],self.result.values()))
		plusy = - min(map(lambda x: x['y'],self.result.values()))

		maxcurrent = 1.0
		for l in self.levels:
			for n in range(1, len(self.levels[l])):
				n1 = self.levels[l][n]
				n2 = self.levels[l][n-1]
				diff = abs(self.result[n2]['x']-self.result[n1]['x'])
				if diff<maxcurrent:
					maxcurrent=diff
		factor = maxx / diff
		for r in self.result:
			self.result[r]['x'] = (self.result[r]['x']+plusx) * factor + plusx2
			self.result[r]['y'] = (self.result[r]['y']+plusy) * maxy + plusy2

	def result_get(self):
		return self.result

if __name__=='__main__':
	starting_node = ['mrp']  # put here nodes with flow_start=True
	nodes = ['project','account','hr','base','product','mrp','test']
	transitions = [
		('mrp','project'),
		('project','product'),
		('project','account'),
		('project','hr'),
		('product','base'),
		('account','product'),
		('account','test'),
		('account','base'),
		('hr','base'),
		('test','base')
	]

	radius = 20
	g = graph(nodes, transitions)
	g.process(starting_node)
	g.scale(radius*3,radius*3, radius, radius)

	print g

	import Image
	import ImageDraw
	img = Image.new("RGB", (800, 600), "#ffffff")
	draw = ImageDraw.Draw(img)

	for name,node in g.result.items():
		draw.arc( (int(node['x']-radius), int(node['y']-radius),int(node['x']+radius), int(node['y']+radius) ), 0, 360, (128,128,128))
		draw.text( (int(node['x']),  int(node['y'])), name,  (128,128,128))


	for nodefrom in g.transitions:
		for nodeto in g.transitions[nodefrom]:
			draw.line( (int(g.result[nodefrom]['x']), int(g.result[nodefrom]['y']),int(g.result[nodeto]['x']),int(g.result[nodeto]['y'])),(128,128,128) )

	img.save("graph.png", "PNG")

