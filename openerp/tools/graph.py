#!/usr/bin/env python
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

import operator
import math

class graph(object):
    def __init__(self, nodes, transitions, no_ancester=None):
        """Initialize graph's object

        @param nodes list of ids of nodes in the graph
        @param transitions list of edges in the graph in the form (source_node, destination_node)
        @param no_ancester list of nodes with no incoming edges
        """

        self.nodes = nodes or []
        self.edges = transitions or []
        self.no_ancester = no_ancester or {}
        trans = {}

        for t in transitions:
            trans.setdefault(t[0], [])
            trans[t[0]].append(t[1])
        self.transitions = trans
        self.result = {}


    def init_rank(self):
        """Computes rank of the nodes of the graph by finding initial feasible tree
        """
        self.edge_wt = {}
        for link in self.links:
            self.edge_wt[link] = self.result[link[1]]['x'] - self.result[link[0]]['x']

        tot_node = self.partial_order.__len__()
        #do until all the nodes in the component are searched
        while self.tight_tree()<tot_node:
            list_node = []
            list_edge = []

            for node in self.nodes:
                if node not in self.reachable_nodes:
                    list_node.append(node)

            for edge in self.edge_wt:
                 if edge not in self.tree_edges:
                    list_edge.append(edge)

            slack = 100

            for edge in list_edge:
                if ((self.reachable_nodes.__contains__(edge[0]) and edge[1] not in self.reachable_nodes) or
                    (self.reachable_nodes.__contains__(edge[1]) and  edge[0] not in self.reachable_nodes)):
                    if(slack>self.edge_wt[edge]-1):
                        slack = self.edge_wt[edge]-1
                        new_edge = edge

            if new_edge[0] not in self.reachable_nodes:
                delta = -(self.edge_wt[new_edge]-1)
            else:
                delta = self.edge_wt[new_edge]-1

            for node in self.result:
                if node in self.reachable_nodes:
                    self.result[node]['x'] += delta

            for edge in self.edge_wt:
                self.edge_wt[edge] = self.result[edge[1]]['x'] - self.result[edge[0]]['x']

        self.init_cutvalues()


    def tight_tree(self):
        self.reachable_nodes = []
        self.tree_edges = []
        self.reachable_node(self.start)
        return self.reachable_nodes.__len__()


    def reachable_node(self, node):
        """Find the nodes of the graph which are only 1 rank apart from each other
        """

        if node not in self.reachable_nodes:
            self.reachable_nodes.append(node)
        for edge in self.edge_wt:
            if edge[0]==node:
                if self.edge_wt[edge]==1:
                    self.tree_edges.append(edge)
                    if edge[1] not in self.reachable_nodes:
                        self.reachable_nodes.append(edge[1])
                    self.reachable_node(edge[1])


    def init_cutvalues(self):
        """Initailize cut values of edges of the feasible tree.
        Edges with negative cut-values are removed from the tree to optimize rank assignment
        """
        self.cut_edges = {}
        self.head_nodes = []
        i=0;

        for edge in self.tree_edges:
            self.head_nodes = []
            rest_edges = []
            rest_edges += self.tree_edges
            rest_edges.__delitem__(i)
            self.head_component(self.start, rest_edges)
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
        """Find nodes which are reachable from the starting node, after removing an edge
        """
        if node not in self.head_nodes:
            self.head_nodes.append(node)

            for edge in rest_edges:
                if edge[0]==node:
                    self.head_component(edge[1],rest_edges)


    def process_ranking(self, node, level=0):
        """Computes initial feasible ranking after making graph acyclic with depth-first search
        """

        if node not in self.result:
            self.result[node] = {'y': None, 'x':level, 'mark':0}
        else:
            if level > self.result[node]['x']:
                self.result[node]['x'] = level

        if self.result[node]['mark']==0:
            self.result[node]['mark'] = 1
            for sec_end in self.transitions.get(node, []):
                self.process_ranking(sec_end, level+1)


    def make_acyclic(self, parent, node, level, tree):
        """Computes Partial-order of the nodes with depth-first search
        """

        if node not in self.partial_order:
            self.partial_order[node] = {'level':level, 'mark':0}
            if parent:
                tree.append((parent, node))

        if self.partial_order[node]['mark']==0:
            self.partial_order[node]['mark'] = 1
            for sec_end in self.transitions.get(node, []):
                self.links.append((node, sec_end))
                self.make_acyclic(node, sec_end, level+1, tree)

        return tree


    def rev_edges(self, tree):
        """reverse the direction of the edges whose source-node-partail_order> destination-node-partail_order
        to make the graph acyclic
        """
        Is_Cyclic = False
        i=0
        for link in self.links:
            src = link[0]
            des = link[1]
            edge_len = self.partial_order[des]['level'] - self.partial_order[src]['level']
            if edge_len < 0:
                self.links.__delitem__(i)
                self.links.insert(i, (des, src))
                self.transitions[src].remove(des)
                self.transitions.setdefault(des, []).append(src)
                Is_Cyclic = True
            elif math.fabs(edge_len) > 1:
                Is_Cyclic = True
            i += 1

        return Is_Cyclic

    def exchange(self, e, f):
        """Exchange edges to make feasible-tree optimized
        @param edge edge with negative cut-value
        @param edge new edge with minimum slack-value
        """
        self.tree_edges.__delitem__(self.tree_edges.index(e))
        self.tree_edges.append(f)
        self.init_cutvalues()


    def enter_edge(self, edge):
        """Finds a new_edge with minimum slack value to replace an edge with negative cut-value

        @param edge edge with negative cut-value
        """

        self.head_nodes = []
        rest_edges = []
        rest_edges += self.tree_edges
        rest_edges.__delitem__(rest_edges.index(edge))
        self.head_component(self.start, rest_edges)

        if self.head_nodes.__contains__(edge[1]):
            l = []
            for node in self.result:
                if not self.head_nodes.__contains__(node):
                    l.append(node)
            self.head_nodes = l

        slack = 100
        new_edge = edge
        for source_node in self.transitions:
            if source_node in self.head_nodes:
                for dest_node in self.transitions[source_node]:
                    if dest_node not in self.head_nodes:
                        if(slack>(self.edge_wt[edge]-1)):
                            slack = self.edge_wt[edge]-1
                            new_edge = (source_node, dest_node)

        return new_edge


    def leave_edge(self):
        """Returns the edge with negative cut_value(if exists)
        """
        if self.critical_edges:
            for edge in self.critical_edges:
                self.cut_edges[edge] = 0

        for edge in self.cut_edges:
            if self.cut_edges[edge]<0:
                return edge

        return None


    def finalize_rank(self, node, level):
        self.result[node]['x'] = level
        for destination in self.optimal_edges.get(node, []):
            self.finalize_rank(destination, level+1)


    def normalize(self):
        """The ranks are normalized by setting the least rank to zero.
        """

        least_rank = min(map(lambda x: x['x'], self.result.values()))

        if(least_rank!=0):
            for node in self.result:
                self.result[node]['x']-=least_rank


    def make_chain(self):
        """Edges between nodes more than one rank apart are replaced by chains of unit
           length edges between temporary nodes.
        """

        for edge in self.edge_wt:
            if self.edge_wt[edge]>1:
                self.transitions[edge[0]].remove(edge[1])
                start = self.result[edge[0]]['x']
                end = self.result[edge[1]]['x']

                for rank in range(start+1, end):
                    if not self.result.get((rank, 'temp'), False):
                        self.result[(rank, 'temp')] = {'y': None, 'x': rank, 'mark': 0}

                for rank in range(start, end):
                    if start==rank:
                        self.transitions[edge[0]].append((rank+1, 'temp'))
                    elif rank==end-1:
                        self.transitions.setdefault((rank, 'temp'), []).append(edge[1])
                    else:
                        self.transitions.setdefault((rank, 'temp'), []).append((rank+1, 'temp'))


    def init_order(self, node, level):
        """Initialize orders the nodes in each rank with depth-first search
        """
        if not self.result[node]['y']:
            self.result[node]['y'] = self.order[level]
            self.order[level] = self.order[level]+1

        for sec_end in self.transitions.get(node, []):
            if node!=sec_end:
                self.init_order(sec_end, self.result[sec_end]['x'])


    def order_heuristic(self):
        for i in range(12):
            self.wmedian()


    def wmedian(self):
        """Applies median heuristic to find optimzed order of the nodes with in their ranks
        """
        for level in self.levels:

            node_median = []
            nodes = self.levels[level]
            for node in nodes:
                node_median.append((node, self.median_value(node, level-1)))

            sort_list = sorted(node_median, key=operator.itemgetter(1))

            new_list = [tuple[0] for tuple in sort_list]

            self.levels[level] = new_list
            order = 0
            for node in nodes:
                self.result[node]['y'] = order
                order +=1


    def median_value(self, node, adj_rank):
        """Returns median value of a vertex , defined as the median position of the adjacent vertices

        @param node node to process
        @param adj_rank rank 1 less than the node's rank
        """
        adj_nodes = self.adj_position(node, adj_rank)
        l = len(adj_nodes)
        m = l/2

        if l==0:
            return -1.0
        elif l%2 == 1:
            return adj_nodes[m]#median of the middle element
        elif l==2:
            return (adj_nodes[0]+adj_nodes[1])/2
        else:
            left = adj_nodes[m-1] - adj_nodes[0]
            right = adj_nodes[l-1] - adj_nodes[m]
            return ((adj_nodes[m-1]*right) + (adj_nodes[m]*left))/(left+right)


    def adj_position(self, node, adj_rank):
        """Returns list of the present positions of the nodes adjacent to node in the given adjacent rank.

        @param node node to process
        @param adj_rank rank 1 less than the node's rank
        """

        pre_level_nodes = self.levels.get(adj_rank, [])
        adj_nodes = []

        if pre_level_nodes:
            for src in pre_level_nodes:
                if (self.transitions.get(src) and self.transitions[src].__contains__(node)):
                    adj_nodes.append(self.result[src]['y'])

        return adj_nodes


    def preprocess_order(self):
        levels = {}

        for r in self.partial_order:
            l = self.result[r]['x']
            levels.setdefault(l,[])
            levels[l].append(r)

        self.levels = levels


    def graph_order(self):
        """Finds actual-order of the nodes with respect to maximum number of nodes in a rank in component
        """
        mid_pos = 0.0
        max_level = max(map(lambda x: len(x), self.levels.values()))

        for level in self.levels:
            if level:
                no = len(self.levels[level])
                factor = (max_level - no) * 0.10
                list = self.levels[level]
                list.reverse()

                if no%2==0:
                    first_half = list[no/2:]
                    factor = -factor
                else:
                    first_half = list[no/2+1:]
                    if max_level==1:#for the case when horizontal graph is there
                        self.result[list[no/2]]['y'] = mid_pos + (self.result[list[no/2]]['x']%2 * 0.5)
                    else:
                        self.result[list[no/2]]['y'] = mid_pos + factor

                last_half = list[:no/2]

                i=1
                for node in first_half:
                    self.result[node]['y'] = mid_pos - (i + factor)
                    i += 1

                i=1
                for node in last_half:
                    self.result[node]['y'] = mid_pos + (i + factor)
                    i += 1
            else:
                self.max_order += max_level+1
                mid_pos = self.result[self.start]['y']


    def tree_order(self, node, last=0):
        mid_pos = self.result[node]['y']
        l = self.transitions.get(node, [])
        l.reverse()
        no = len(l)

        rest = no%2
        first_half = l[no/2+rest:]
        last_half = l[:no/2]

        for i, child in enumerate(first_half):
            self.result[child]['y'] = mid_pos - (i+1 - (0 if rest else 0.5))

            if self.transitions.get(child, False):
                if last:
                    self.result[child]['y'] = last + len(self.transitions[child])/2 + 1
                last = self.tree_order(child, last)

        if rest:
            mid_node = l[no/2]
            self.result[mid_node]['y'] = mid_pos

            if self.transitions.get((mid_node), False):
                if last:
                    self.result[mid_node]['y'] = last + len(self.transitions[mid_node])/2 + 1
                if node!=mid_node:
                    last = self.tree_order(mid_node)
            else:
                if last:
                    self.result[mid_node]['y'] = last + 1
            self.result[node]['y'] = self.result[mid_node]['y']
            mid_pos = self.result[node]['y']

        i=1
        last_child = None
        for child in last_half:
            self.result[child]['y'] = mid_pos + (i - (0 if rest else 0.5))
            last_child = child
            i += 1
            if self.transitions.get(child, False):
                if last:
                    self.result[child]['y'] = last + len(self.transitions[child])/2 + 1
                if node!=child:
                    last = self.tree_order(child, last)

        if last_child:
            last = self.result[last_child]['y']

        return last


    def process_order(self):
        """Finds actual-order of the nodes with respect to maximum number of nodes in a rank in component
        """

        if self.Is_Cyclic:
            max_level = max(map(lambda x: len(x), self.levels.values()))

            if max_level%2:
                self.result[self.start]['y'] = (max_level+1)/2 + self.max_order + (self.max_order and 1)
            else:
                self.result[self.start]['y'] = (max_level)/2 + self.max_order + (self.max_order and 1)

            self.graph_order()

        else:
            self.result[self.start]['y'] = 0
            self.tree_order(self.start, 0)
            min_order = math.fabs(min(map(lambda x: x['y'], self.result.values())))

            index = self.start_nodes.index(self.start)
            same = False

            roots  = []
            if index>0:
                for start in self.start_nodes[:index]:
                    same = True
                    for edge in self.tree_list[start][1:]:
                        if self.tree_list[self.start].__contains__(edge):
                            continue
                        else:
                            same = False
                            break
                    if same:
                        roots.append(start)

            if roots:
                min_order += self.max_order
            else:
                min_order += self.max_order + 1

            for level in self.levels:
                for node in self.levels[level]:
                    self.result[node]['y'] += min_order

            if roots:
                roots.append(self.start)
                one_level_el = self.tree_list[self.start][0][1]
                base = self.result[one_level_el]['y']# * 2 / (index + 2)


                no = len(roots)
                first_half = roots[:no/2]

                if no%2==0:
                    last_half = roots[no/2:]
                else:
                    last_half = roots[no/2+1:]

                factor = -math.floor(no/2)
                for start in first_half:
                    self.result[start]['y'] = base + factor
                    factor += 1

                if no%2:
                    self.result[roots[no/2]]['y'] = base + factor
                factor +=1

                for start in last_half:
                    self.result[start]['y'] = base + factor
                    factor += 1

            self.max_order = max(map(lambda x: x['y'], self.result.values()))

    def find_starts(self):
        """Finds other start nodes of the graph in the case when graph is disconneted
        """
        rem_nodes = []
        for node in self.nodes:
            if not self.partial_order.get(node):
                rem_nodes.append(node)
        cnt = 0
        while True:
            if len(rem_nodes)==1:
                self.start_nodes.append(rem_nodes[0])
                break
            else:
                count = 0
                new_start = rem_nodes[0]
                largest_tree = []

                for node in rem_nodes:
                    self.partial_order = {}
                    tree = self.make_acyclic(None, node, 0, [])
                    if len(tree)+1 > count:
                        count = len(tree) + 1
                        new_start = node
                        largest_tree = tree
                else:
                    if not largest_tree:
                        new_start = rem_nodes[0]
                        rem_nodes.remove(new_start)

                self.start_nodes.append(new_start)


                for edge in largest_tree:
                    if rem_nodes.__contains__(edge[0]):
                        rem_nodes.remove(edge[0])
                    if rem_nodes.__contains__(edge[1]):
                        rem_nodes.remove(edge[1])

                if not rem_nodes:
                    break


    def rank(self):
        """Finds the optimized rank of the nodes using Network-simplex algorithm

        @param start starting node of the component
        """
        self.levels = {}
        self.critical_edges = []
        self.partial_order = {}
        self.links = []
        self.Is_Cyclic = False

        self.tree_list[self.start] = self.make_acyclic(None, self.start, 0, [])
        self.Is_Cyclic = self.rev_edges(self.tree_list[self.start])
        self.process_ranking(self.start)
        self.init_rank()

        #make cut values of all tree edges to 0 to optimize feasible tree
        e = self.leave_edge()

        while e :
            f = self.enter_edge(e)
            if e==f:
                self.critical_edges.append(e)
            else:
                self.exchange(e,f)
            e = self.leave_edge()

        #finalize rank using optimum feasible tree
#        self.optimal_edges = {}
#        for edge in self.tree_edges:
#            source = self.optimal_edges.setdefault(edge[0], [])
#            source.append(edge[1])

#        self.finalize_rank(self.start, 0)

        #normalization
        self.normalize()
        for edge in self.edge_wt:
            self.edge_wt[edge] = self.result[edge[1]]['x'] - self.result[edge[0]]['x']

    def order_in_rank(self):
        """Finds optimized order of the nodes within their ranks using median heuristic

        @param start: starting node of the component
        """

        self.make_chain()
        self.preprocess_order()
        self.order = {}
        max_rank = max(map(lambda x: x, self.levels.keys()))

        for i in range(max_rank+1):
            self.order[i] = 0

        self.init_order(self.start, self.result[self.start]['x'])

        for level in self.levels:
            self.levels[level].sort(lambda x, y: cmp(self.result[x]['y'], self.result[y]['y']))

        self.order_heuristic()
        self.process_order()

    def process(self, starting_node):
        """Process the graph to find ranks and order of the nodes

        @param starting_node node from where to start the graph search
        """

        self.start_nodes = starting_node or []
        self.partial_order = {}
        self.links = []
        self.tree_list = {}

        if self.nodes:
            if self.start_nodes:
                #add dummy edges to the nodes which does not have any incoming edges
                tree = self.make_acyclic(None, self.start_nodes[0], 0, [])

                for node in self.no_ancester:
                    for sec_node in self.transitions.get(node, []):
                        if sec_node in self.partial_order.keys():
                            self.transitions[self.start_nodes[0]].append(node)
                            break

                self.partial_order = {}
                tree = self.make_acyclic(None, self.start_nodes[0], 0, [])


            # if graph is disconnected or no start-node is given
            #than to find starting_node for each component of the node
            if len(self.nodes) > len(self.partial_order):
                self.find_starts()

            self.max_order = 0
            #for each component of the graph find ranks and order of the nodes
            for s in self.start_nodes:
                self.start = s
                self.rank()   # First step:Netwoek simplex algorithm
                self.order_in_rank()    #Second step: ordering nodes within ranks


    def __str__(self):
        result = ''
        for l in self.levels:
            result += 'PosY: ' + str(l) + '\n'
            for node in self.levels[l]:
                result += '\tPosX: '+ str(self.result[node]['y']) + '  - Node:' + str(node) + "\n"
        return result


    def scale(self, maxx, maxy, nwidth=0, nheight=0, margin=20):
        """Computes actual co-ordiantes of the nodes
        """

            #for flat edges ie. source an destination nodes are on the same rank
        for src in self.transitions:
            for des in self.transitions[src]:
                if (self.result[des]['x'] - self.result[src]['x'] == 0):
                    self.result[src]['x'] += 0.08
                    self.result[des]['x'] -= 0.08

        factorX = maxx + nheight
        factorY = maxy + nwidth

        for node in self.result:
            self.result[node]['y'] = (self.result[node]['y']) * factorX + margin
            self.result[node]['x'] = (self.result[node]['x']) * factorY + margin


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

    from PIL import Image
    from PIL import ImageDraw
    img = Image.new("RGB", (800, 600), "#ffffff")
    draw = ImageDraw.Draw(img)

    result = g.result_get()
    node_res = {}
    for node in nodes:
        node_res[node] = result[node]

    for name,node in node_res.items():

        draw.arc( (int(node['y']-radius), int(node['x']-radius),int(node['y']+radius), int(node['x']+radius) ), 0, 360, (128,128,128))
        draw.text( (int(node['y']),  int(node['x'])), str(name),  (128,128,128))


    for t in transitions:
        draw.line( (int(node_res[t[0]]['y']), int(node_res[t[0]]['x']),int(node_res[t[1]]['y']),int(node_res[t[1]]['x'])),(128,128,128) )
    img.save("graph.png", "PNG")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

