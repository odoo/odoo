"""Graphviz's dot language parser.

The dotparser parses GraphViz files in
dot and dot files and transforms them
into a class representation defined by `pydot`.

Author: Michael Krause <michael@krause-software.de>
Fixes by: Ero Carrera <ero.carrera@gmail.com>
"""
from __future__ import division
from __future__ import print_function
import sys

from pyparsing import (
    nestedExpr, Literal, CaselessLiteral,
    Word, OneOrMore,
    Forward,
    Group, Optional, Combine,
    restOfLine, cStyleComment, nums, alphanums,
    printables,
    ParseException, ParseResults, CharsNotIn,
    QuotedString)

import pydot

__author__ = ['Michael Krause', 'Ero Carrera']
__license__ = 'MIT'


PY3 = sys.version_info >= (3, 0, 0)
if PY3:
    str_type = str
else:
    str_type = basestring


class P_AttrList(object):

    def __init__(self, toks):

        self.attrs = {}
        i = 0

        while i < len(toks):
            attrname = toks[i]
            if i+2 < len(toks) and toks[i+1] == '=':
                attrvalue = toks[i+2]
                i += 3
            else:
                attrvalue = None
                i += 1

            self.attrs[attrname] = attrvalue


    def __repr__(self):

        return "%s(%r)" % (self.__class__.__name__, self.attrs)



class DefaultStatement(P_AttrList):

    def __init__(self, default_type, attrs):

        self.default_type = default_type
        self.attrs = attrs

    def __repr__(self):

        return "%s(%s, %r)" % (self.__class__.__name__,
            self.default_type, self.attrs)


top_graphs = list()

def push_top_graph_stmt(str, loc, toks):

    attrs = {}
    g = None

    for element in toks:

        if (isinstance(element, (ParseResults, tuple, list)) and
                len(element) == 1 and
                isinstance(element[0], str_type)):

            element = element[0]

        if element == 'strict':
            attrs['strict'] = True

        elif element in ['graph', 'digraph']:

            attrs = {}

            g = pydot.Dot(graph_type=element, **attrs)
            attrs['type'] = element

            top_graphs.append( g )

        elif isinstance( element, str_type):
            g.set_name( element )

        elif isinstance(element, pydot.Subgraph):

            g.obj_dict['attributes'].update( element.obj_dict['attributes'] )
            g.obj_dict['edges'].update( element.obj_dict['edges'] )
            g.obj_dict['nodes'].update( element.obj_dict['nodes'] )
            g.obj_dict['subgraphs'].update( element.obj_dict['subgraphs'] )

            g.set_parent_graph(g)

        elif isinstance(element, P_AttrList):
            attrs.update(element.attrs)

        elif isinstance(element, (ParseResults, list)):
            add_elements(g, element)

        else:
            raise ValueError(
                'Unknown element statement: {s}'.format(s=element))


    for g in top_graphs:
        update_parent_graph_hierarchy(g)

    if len( top_graphs ) == 1:
        return top_graphs[0]

    return top_graphs


def update_parent_graph_hierarchy(g, parent_graph=None, level=0):


    if parent_graph is None:
        parent_graph = g

    for key_name in ('edges',):

        if isinstance(g, pydot.frozendict):
            item_dict = g
        else:
            item_dict = g.obj_dict

        if key_name not in item_dict:
            continue

        for key, objs in item_dict[key_name].items():
            for obj in objs:
                if ('parent_graph' in obj and
                        obj['parent_graph'].get_parent_graph()==g):
                    if obj['parent_graph'] is g:
                        pass
                    else:
                        obj['parent_graph'].set_parent_graph(parent_graph)

                if key_name == 'edges' and len(key) == 2:
                    for idx, vertex in enumerate( obj['points'] ):
                        if isinstance( vertex,
                                      (pydot.Graph,
                                       pydot.Subgraph, pydot.Cluster)):
                            vertex.set_parent_graph(parent_graph)
                        if isinstance( vertex, pydot.frozendict):
                            if vertex['parent_graph'] is g:
                                pass
                            else:
                                vertex['parent_graph'].set_parent_graph(
                                    parent_graph)



def add_defaults(element, defaults):

    d = element.__dict__
    for key, value in defaults.items():
        if not d.get(key):
            d[key] = value



def add_elements(g, toks, defaults_graph=None,
                 defaults_node=None, defaults_edge=None):

    if defaults_graph is None:
        defaults_graph = {}
    if defaults_node is None:
        defaults_node = {}
    if defaults_edge is None:
        defaults_edge = {}

    for elm_idx, element in enumerate(toks):

        if isinstance(element, (pydot.Subgraph, pydot.Cluster)):

            add_defaults(element, defaults_graph)
            g.add_subgraph(element)

        elif isinstance(element, pydot.Node):

            add_defaults(element, defaults_node)
            g.add_node(element)

        elif isinstance(element, pydot.Edge):

            add_defaults(element, defaults_edge)
            g.add_edge(element)

        elif isinstance(element, ParseResults):

            for e in element:
                add_elements(g, [e], defaults_graph,
                             defaults_node, defaults_edge)

        elif isinstance(element, DefaultStatement):

            if element.default_type == 'graph':

                default_graph_attrs = pydot.Node('graph', **element.attrs)
                g.add_node(default_graph_attrs)

            elif element.default_type == 'node':

                default_node_attrs = pydot.Node('node', **element.attrs)
                g.add_node(default_node_attrs)

            elif element.default_type == 'edge':

                default_edge_attrs = pydot.Node('edge', **element.attrs)
                g.add_node(default_edge_attrs)
                defaults_edge.update(element.attrs)

            else:
                raise ValueError(
                    'Unknown DefaultStatement: {s}'.format(
                         s=element.default_type))

        elif isinstance(element, P_AttrList):

            g.obj_dict['attributes'].update(element.attrs)

        else:
            raise ValueError(
                'Unknown element statement: {s}'.format(s=element))


def push_graph_stmt(str, loc, toks):

    g = pydot.Subgraph('')
    add_elements(g, toks)
    return g


def push_subgraph_stmt(str, loc, toks):

    g = pydot.Subgraph('')
    for e in toks:
        if len(e)==3:
            e[2].set_name(e[1])
            if e[0] == 'subgraph':
                e[2].obj_dict['show_keyword'] = True
            return e[2]
        else:
            if e[0] == 'subgraph':
                e[1].obj_dict['show_keyword'] = True
            return e[1]

    return g


def push_default_stmt(str, loc, toks):

    # The pydot class instances should be marked as
    # default statements to be inherited by actual
    # graphs, nodes and edges.
    #
    default_type = toks[0][0]
    if len(toks) > 1:
        attrs = toks[1].attrs
    else:
        attrs = {}

    if default_type in ['graph', 'node', 'edge']:
        return DefaultStatement(default_type, attrs)
    else:
        raise ValueError(
            'Unknown default statement: {s}'.format(s=toks))


def push_attr_list(str, loc, toks):

    p = P_AttrList(toks)
    return p


def get_port(node):

    if len(node)>1:
        if isinstance(node[1], ParseResults):
            if len(node[1][0])==2:
                if node[1][0][0]==':':
                    return node[1][0][1]

    return None


def do_node_ports(node):

    node_port = ''
    if len(node) > 1:
        node_port = ''.join( [str(a)+str(b) for a,b in node[1] ] )

    return node_port


def push_edge_stmt(str, loc, toks):

    tok_attrs = [a for a in toks if isinstance(a, P_AttrList)]
    attrs = {}
    for a in tok_attrs:
        attrs.update(a.attrs)

    e = []

    if isinstance(toks[0][0], pydot.Graph):

        n_prev = pydot.frozendict(toks[0][0].obj_dict)
    else:
        n_prev = toks[0][0] + do_node_ports( toks[0] )

    if isinstance(toks[2][0], ParseResults):

        n_next_list = [[n.get_name(),] for n in toks[2][0] ]
        for n_next in [n for n in n_next_list]:
            n_next_port = do_node_ports(n_next)
            e.append(pydot.Edge(n_prev, n_next[0]+n_next_port, **attrs))

    elif isinstance(toks[2][0], pydot.Graph):

        e.append(pydot.Edge(n_prev,
                            pydot.frozendict(toks[2][0].obj_dict),
                            **attrs))

    elif isinstance(toks[2][0], pydot.Node):

        node = toks[2][0]

        if node.get_port() is not None:
            name_port = node.get_name() + ":" + node.get_port()
        else:
            name_port = node.get_name()

        e.append(pydot.Edge(n_prev, name_port, **attrs))

    # if the target of this edge is the name of a node
    elif isinstance(toks[2][0], str_type):

        for n_next in [n for n in tuple(toks)[2::2]]:

            if (isinstance(n_next, P_AttrList) or
                    not isinstance(n_next[0], str_type)):
                continue

            n_next_port = do_node_ports( n_next )
            e.append(pydot.Edge(n_prev, n_next[0]+n_next_port, **attrs))

            n_prev = n_next[0]+n_next_port
    else:
        raise Exception(
            'Edge target {r} with type {s} unsupported.'.format(
                r=toks[2][0], s=type(toks[2][0])))

    return e



def push_node_stmt(s, loc, toks):

    if len(toks) == 2:
        attrs = toks[1].attrs
    else:
        attrs = {}

    node_name = toks[0]
    if isinstance(node_name, list) or isinstance(node_name, tuple):
        if len(node_name)>0:
            node_name = node_name[0]

    n = pydot.Node(str(node_name), **attrs)
    return n






graphparser = None

def graph_definition():

    global graphparser

    if not graphparser:

        # punctuation
        colon  = Literal(":")
        lbrace = Literal("{")
        rbrace = Literal("}")
        lbrack = Literal("[")
        rbrack = Literal("]")
        lparen = Literal("(")
        rparen = Literal(")")
        equals = Literal("=")
        comma  = Literal(",")
        dot    = Literal(".")
        slash  = Literal("/")
        bslash = Literal("\\")
        star   = Literal("*")
        semi   = Literal(";")
        at     = Literal("@")
        minus  = Literal("-")

        # keywords
        strict_    = CaselessLiteral("strict")
        graph_     = CaselessLiteral("graph")
        digraph_   = CaselessLiteral("digraph")
        subgraph_  = CaselessLiteral("subgraph")
        node_      = CaselessLiteral("node")
        edge_      = CaselessLiteral("edge")


        # token definitions

        identifier = Word(alphanums + "_." ).setName("identifier")

        double_quoted_string = QuotedString(
            '"', multiline=True, unquoteResults=False, escChar='\\')  # dblQuotedString

        noncomma = "".join([c for c in printables if c != ","])
        alphastring_ = OneOrMore(CharsNotIn(noncomma + ' '))

        def parse_html(s, loc, toks):
            return '<%s>' % ''.join(toks[0])


        opener = '<'
        closer = '>'
        html_text = nestedExpr( opener, closer,
            ( CharsNotIn( opener + closer )  )
                ).setParseAction(parse_html).leaveWhitespace()

        ID = ( identifier | html_text |
            double_quoted_string | #.setParseAction(strip_quotes) |
            alphastring_ ).setName("ID")


        float_number = Combine(Optional(minus) +
            OneOrMore(Word(nums + "."))).setName("float_number")

        righthand_id =  (float_number | ID ).setName("righthand_id")

        port_angle = (at + ID).setName("port_angle")

        port_location = (OneOrMore(Group(colon + ID)) |
            Group(colon + lparen +
                  ID + comma + ID + rparen)).setName("port_location")

        port = (Group(port_location + Optional(port_angle)) |
            Group(port_angle + Optional(port_location))).setName("port")

        node_id = (ID + Optional(port))
        a_list = OneOrMore(ID + Optional(equals + righthand_id) +
            Optional(comma.suppress())).setName("a_list")

        attr_list = OneOrMore(lbrack.suppress() + Optional(a_list) +
            rbrack.suppress()).setName("attr_list")

        attr_stmt = (Group(graph_ | node_ | edge_) +
                     attr_list).setName("attr_stmt")

        edgeop = (Literal("--") | Literal("->")).setName("edgeop")

        stmt_list = Forward()
        graph_stmt = Group(lbrace.suppress() + Optional(stmt_list) +
            rbrace.suppress() +
            Optional(semi.suppress())).setName("graph_stmt")


        edge_point = Forward()

        edgeRHS = OneOrMore(edgeop + edge_point)
        edge_stmt = edge_point + edgeRHS + Optional(attr_list)

        subgraph = Group(
            subgraph_ + Optional(ID) + graph_stmt).setName("subgraph")

        edge_point << Group(
            subgraph | graph_stmt | node_id).setName('edge_point')

        node_stmt = (
            node_id + Optional(attr_list) +
            Optional(semi.suppress())).setName("node_stmt")

        assignment = (ID + equals + righthand_id).setName("assignment")
        stmt = (assignment | edge_stmt | attr_stmt |
                subgraph | graph_stmt | node_stmt).setName("stmt")
        stmt_list << OneOrMore(stmt + Optional(semi.suppress()))

        graphparser = OneOrMore(
            (Optional(strict_) + Group((graph_ | digraph_)) +
             Optional(ID) + graph_stmt).setResultsName("graph"))

        singleLineComment = Group(
            "//" + restOfLine) | Group("#" + restOfLine)


        # actions

        graphparser.ignore(singleLineComment)
        graphparser.ignore(cStyleComment)

        assignment.setParseAction(push_attr_list)
        a_list.setParseAction(push_attr_list)
        edge_stmt.setParseAction(push_edge_stmt)
        node_stmt.setParseAction(push_node_stmt)
        attr_stmt.setParseAction(push_default_stmt)

        subgraph.setParseAction(push_subgraph_stmt)
        graph_stmt.setParseAction(push_graph_stmt)
        graphparser.setParseAction(push_top_graph_stmt)


    return graphparser


def parse_dot_data(s):
    """Parse DOT description in (unicode) string `s`.

    @return: Graphs that result from parsing.
    @rtype: `list` of `pydot.Dot`
    """
    global top_graphs
    top_graphs = list()
    try:
        graphparser = graph_definition()
        graphparser.parseWithTabs()
        tokens = graphparser.parseString(s)
        return list(tokens)
    except ParseException as err:
        print(err.line)
        print(" " * (err.column - 1) + "^")
        print(err)
        return None
