#!/bin/env python

"""
The dotparser parses graphviz files in dot and dot files and transforms them
into a class representation defined by pydot.

The module needs pyparsing (tested with version 1.2) and pydot (tested with 0.9.9)

Author: Michael Krause <michael@krause-software.de>
"""

import sys
import glob
import pydot

from pyparsing import __version__ as pyparsing_version
from pyparsing import Literal, CaselessLiteral, Word,   \
    Upcase, OneOrMore, ZeroOrMore, Forward, NotAny,     \
    delimitedList, oneOf, Group, Optional, Combine,     \
    alphas, nums, restOfLine, cStyleComment, nums,      \
    alphanums, printables, empty, quotedString,         \
    ParseException, ParseResults, CharsNotIn, _noncomma


class P_AttrList:
    def __init__(self, toks):
        self.attrs = {}
        i = 0
        while i < len(toks):
            attrname = toks[i]
            attrvalue = toks[i+1]
            self.attrs[attrname] = attrvalue
            i += 2

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.attrs)


class DefaultStatement(P_AttrList):
    def __init__(self, default_type, attrs):
        self.default_type = default_type
        self.attrs = attrs

    def __repr__(self):
        return "%s(%s, %r)" %   \
            (self.__class__.__name__, self.default_type, self.attrs)


def push_top_graph_stmt(str, loc, toks):
    attrs = {}
    g = None
    
    for element in toks:
        if  isinstance(element, ParseResults) or    \
            isinstance(element, tuple) or           \
            isinstance(element, list):
            
            element = element[0]

        if element == 'strict':
            attrs['strict'] = True
        elif element in ['graph', 'digraph']:
            attrs['graph_type'] = element
        elif type(element) == type(''):
            attrs['graph_name'] = element
        elif isinstance(element, pydot.Graph):
            g = pydot.Graph(**attrs)
            g.__dict__.update(element.__dict__)
            for e in g.get_edge_list():
                e.parent_graph = g
            for e in g.get_node_list():
                e.parent_graph = g
            for e in g.get_subgraph_list():
                e.set_graph_parent(g)

        elif isinstance(element, P_AttrList):
            attrs.update(element.attrs)
        else:
            raise ValueError, "Unknown element statement: %r " % element
    
    if g is not None:
        g.__dict__.update(attrs)
        return g


def add_defaults(element, defaults):
    d = element.__dict__
    for key, value in defaults.items():
        if not d.get(key):
            d[key] = value


def add_elements(g, toks, defaults_graph=None, defaults_node=None, defaults_edge=None):
    
    if defaults_graph is None:
        defaults_graph = {}
    if defaults_node is None:
        defaults_node = {}
    if defaults_edge is None:
        defaults_edge = {}
        
    for element in toks:
        if isinstance(element, pydot.Graph):
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
                add_elements(g, [e], defaults_graph, defaults_node, defaults_edge)
        elif isinstance(element, DefaultStatement):
            if element.default_type == 'graph':
                default_graph_attrs = pydot.Node('graph')
                default_graph_attrs.__dict__.update(element.attrs)
                g.add_node(default_graph_attrs)
#               defaults_graph.update(element.attrs)
#               g.__dict__.update(element.attrs)
            elif element.default_type == 'node':
                default_node_attrs = pydot.Node('node')
                default_node_attrs.__dict__.update(element.attrs)
                g.add_node(default_node_attrs)
                #defaults_node.update(element.attrs)
            elif element.default_type == 'edge':
                default_edge_attrs = pydot.Node('edge')
                default_edge_attrs.__dict__.update(element.attrs)
                g.add_node(default_edge_attrs)
                #defaults_edge.update(element.attrs)
            else:
                raise ValueError, "Unknown DefaultStatement: %s " % element.default_type
        elif isinstance(element, P_AttrList):
            g.__dict__.update(element.attrs)
        else:
            raise ValueError, "Unknown element statement: %r " % element


def push_graph_stmt(str, loc, toks):
    g = pydot.Subgraph()
    add_elements(g, toks)
    return g


def push_subgraph_stmt(str, loc, toks): 
    for e in toks:
        if len(e)==3:
            g = e[2]
            g.set_name(e[1])

    return g


def push_default_stmt(str, loc, toks):
    # The pydot class instances should be marked as
    # default statements to be inherited by actual
    # graphs, nodes and edges.
    # print "push_default_stmt", toks
    default_type = toks[0][0]
    if len(toks) > 1:
        attrs = toks[1].attrs
    else:
        attrs = {}

    if default_type in ['graph', 'node', 'edge']:
        return DefaultStatement(default_type, attrs)
    else:
        raise ValueError, "Unknown default statement: %r " % toks


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


def push_edge_stmt(str, loc, toks):
    
    tok_attrs = [a for a in toks if isinstance(a, P_AttrList)]
    attrs = {}
    for a in tok_attrs:
        attrs.update(a.attrs)
    
    n_prev = toks[0]
    e = []
    for n_next in tuple(toks)[2::2]:
        port = get_port(n_prev)
        if port is not None:
            n_prev_port = ':'+port
        else:
            n_prev_port = ''
            
        port = get_port(n_next)
        if port is not None:
            n_next_port = ':'+port
        else:
            n_next_port = ''
            
        e.append(pydot.Edge(n_prev[0]+n_prev_port, n_next[0]+n_next_port, **attrs))
        n_prev = n_next
    return e


def push_node_stmt(str, loc, toks):

    if len(toks) == 2:
        attrs = toks[1].attrs
    else:
        attrs = {}
        
    node_name = toks[0]
    if isinstance(node_name, list) or isinstance(node_name, tuple):
        if len(node_name)>0:
            node_name = node_name[0]
    
    n = pydot.Node(node_name, **attrs)
    return n


def strip_quotes( s, l, t ):
    return [ t[0].strip('"') ]


graphparser = None
def GRAPH_DEF():
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
        strict_    = Literal("strict")
        graph_     = Literal("graph")
        digraph_   = Literal("digraph")
        subgraph_  = Literal("subgraph")
        node_      = Literal("node")
        edge_      = Literal("edge")
        
        identifier = Word(alphanums + "_" ).setName("identifier")
        
        double_quote = Literal('"')
        double_quoted_string =  \
            Combine( double_quote + ZeroOrMore(CharsNotIn('"')) + double_quote )

        alphastring_ = OneOrMore(CharsNotIn(_noncomma))

        ID = (identifier | double_quoted_string.setParseAction(strip_quotes) |\
            alphastring_).setName("ID")
            
        html_text = Combine(Literal("<<") + OneOrMore(CharsNotIn(",]")))
        
        float_number = Combine(Optional(minus) +    \
            OneOrMore(Word(nums + "."))).setName("float_number")
            
        righthand_id =  (float_number | ID | html_text).setName("righthand_id")

        port_angle = (at + ID).setName("port_angle")
        
        port_location = (Group(colon + ID) |    \
            Group(colon + lparen + ID + comma + ID + rparen)).setName("port_location")
            
        port = (Group(port_location + Optional(port_angle)) |   \
            Group(port_angle + Optional(port_location))).setName("port")
            
        node_id = (ID + Optional(port))
        a_list = OneOrMore(ID + Optional(equals.suppress() + righthand_id) +    \
            Optional(comma.suppress())).setName("a_list")
            
        attr_list = OneOrMore(lbrack.suppress() + Optional(a_list) +    \
            rbrack.suppress()).setName("attr_list")
            
        attr_stmt = (Group(graph_ | node_ | edge_) + attr_list).setName("attr_stmt")

        edgeop = (Literal("--") | Literal("->")).setName("edgeop")

        stmt_list = Forward()
        graph_stmt = Group(lbrace.suppress() + Optional(stmt_list) +    \
            rbrace.suppress()).setName("graph_stmt")
            
        subgraph = (Group(Optional(subgraph_ + Optional(ID)) + graph_stmt) |    \
            Group(subgraph_ + ID)).setName("subgraph")
            
        edgeRHS = OneOrMore(edgeop + Group(node_id | subgraph))
        
        edge_stmt = Group(node_id | subgraph) + edgeRHS + Optional(attr_list)

        node_stmt = (node_id + Optional(attr_list) + semi.suppress()).setName("node_stmt")
        
        assignment = (ID + equals.suppress() + righthand_id).setName("assignment")
        stmt =  (assignment | edge_stmt | attr_stmt | node_stmt | subgraph).setName("stmt")
        stmt_list << OneOrMore(stmt + Optional(semi.suppress()))

        graphparser = (Optional(strict_) + Group((graph_ | digraph_)) + \
            Optional(ID) + graph_stmt).setResultsName("graph")

        singleLineComment = "//" + restOfLine
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


def parse_dot_data(data):
    try:
        graphparser = GRAPH_DEF()
        if pyparsing_version >= '1.2':
            graphparser.parseWithTabs()
        tokens = graphparser.parseString(data)
        graph = tokens.graph
        return graph
    except ParseException, err:
        print err.line
        print " "*(err.column-1) + "^"
        print err
        return None
