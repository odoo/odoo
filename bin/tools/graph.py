#!/usr/bin/python
##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
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
###############################################################################

class graph(object):
    def __init__(self, nodes, transitions):
        self.nodes = nodes
        self.links = transitions
        trans = {}
        for t in transitions:
            trans.setdefault(t[0], [])
            trans[t[0]].append(t[1])
        self.transitions = trans
        self.result = {}
        self.levels = {}
        
    def get_parent(self,node):
        count = 0
        for item in self.transitions:
            if self.transitions[item].__contains__(node):
                count +=1
        return count
    
    def init_rank(self):
        self.temp = {}
        for link in self.links:
            self.temp[link] = self.result[link[1]]['y'] - self.result[link[0]]['y']
        
        cnt = 0
        list_node = []
        list_edge = []
            
        while self.tight_tree()<self.result.__len__():
            cnt+=1
            list_node = []
            
            for node in self.nodes:
                if node not in self.reachable_nodes:
                    list_node.append(node)
            list_edge = []
            
            for link in self.temp:
                 if link not in self.tree_edges:
                    list_edge.append(link)
            
            slack = 100
            
            for edge in list_edge:
                if (self.reachable_nodes.__contains__(edge[0]) and edge[1] not in self.reachable_nodes) or ( self.reachable_nodes.__contains__(edge[1]) and  edge[0] not in self.reachable_nodes):
                    if(slack>self.temp[edge]-1):
                        slack = self.temp[edge]-1
                        new_edge = edge
                        
            if new_edge[0] not in self.reachable_nodes:
                delta = -(self.temp[new_edge]-1)
            else:
                delta = self.temp[new_edge]-1
                
            for node in self.result:
                if node in self.reachable_nodes:
                    self.result[node]['y'] += delta
                    
            for link in self.temp:
                self.temp[link] = self.result[link[1]]['y'] - self.result[link[0]]['y']     
        
        self.init_cutvalues()           
        
        
        
        
    def tight_tree(self,):
        self.reachable_nodes = []
        self.tree_edges = []
        self.reachable_node(self.start) 
        return self.reachable_nodes.__len__()
    
    def reachable_node(self,node):
        if node not in self.reachable_nodes:
            self.reachable_nodes.append(node)
        for link in self.temp:
            if link[0]==node:
#               print link[0]
                if self.temp[link]==1:
                    self.tree_edges.append(link)
                    if link[1] not in self.reachable_nodes:
                        self.reachable_nodes.append(link[1])
                    self.reachable_node(link[1])
                    
                    
    def init_cutvalues(self):
        self.cut_edges = {}
        self.head_nodes = []
        i=0;
        for edge in self.tree_edges:
            self.head_nodes = []
            rest_edges = []
            rest_edges += self.tree_edges
            rest_edges.__delitem__(i)
            self.head_component(self.start,rest_edges)      
            i+=1
            positive = 0
            negative = 0
            for source_node in self.transitions:
                if source_node in self.head_nodes:                  
                    for dest_node in self.transitions[source_node]:
                        if dest_node not in self.head_nodes:
                            negative+=1
                else:
                    for dest_node in self.transitions[source_node]:
                        if dest_node in self.head_nodes:
                            positive+=1

            self.cut_edges[edge] = positive - negative
        
            

                
    def head_component(self, node, rest_edges):
        if node not in self.head_nodes:
            self.head_nodes.append(node)
        for link in rest_edges:
            if link[0]==node:       
                self.head_component(link[1],rest_edges)
        

    def process_ranking(self, node, level=0):
        if node not in self.result:
            self.result[node] = {'x': None, 'y':level, 'mark':0}
        else:
            if level > self.result[node]['y']:
                self.result[node]['y'] = level
        if self.result[node]['mark']==0:
            self.result[node]['mark'] = 1
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
                    
    def exchange(self,e,f):
        self.tree_edges.__delitem__(self.tree_edges.index(e))
        self.tree_edges.append(f)
        self.init_cutvalues()
        
                    
    def enter_edge(self,edge):
        self.head_nodes = []
        rest_edges = []
        rest_edges += self.tree_edges
        rest_edges.__delitem__(rest_edges.index(edge))
        self.head_component(self.start,rest_edges)
        slack = 100
        for source_node in self.transitions:
            if source_node in self.head_nodes:                  
                for dest_node in self.transitions[source_node]:
                    if dest_node not in self.head_nodes:
                        if(slack>(self.temp[edge]-1)):
                            slack = self.temp[edge]-1
                            new_edge = (source_node,dest_node)
        return new_edge 
        

    def leave_edge(self):
        for edge in self.cut_edges:
            if self.cut_edges[edge]<0:
                return edge
        return ()   

    def process(self, starting_node):
        pos = (len(starting_node) - 1.0)/2.0
        self.start = starting_node[0]
        for s in starting_node:
            self.process_ranking(s)
            self.result[s]['x'] = pos
            pos += 1.0
        self.init_rank()
        #normalize
        least_rank=100
        
        #normalization
        for node in self.result:
            if least_rank>self.result[node]['y']:
                least_rank = self.result[node]['y']
        
        if(least_rank!=0):
            diff = least_rank
            for node in self.result:
                self.result[node]['y']-=least_rank
                    
        e = self.leave_edge()
        #while e:
        f = self.enter_edge(e)
        self.exchange(e,f) 
        e = self.leave_edge()   
    
            
        
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
        diff = 1.0
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
    starting_node = ['profile']  # put here nodes with flow_start=True
    nodes = ['project','account','hr','base','product','mrp','test','profile']
    transitions = [
        ('profile','mrp'),
        ('mrp','project'),
        ('project','product'),
        ('mrp','hr'),
        ('mrp','test'),
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

