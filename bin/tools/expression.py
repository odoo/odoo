#!/usr/bin/env python

def _is_operator( element ):
    return isinstance( element, str ) and element in ['&','|']

def _is_leaf( element ):
    return isinstance( element, tuple ) and len( element ) == 3 and element[1] in ['=', '<>', '!=', '<=', '<', '>', '>=', 'like', 'not like', 'ilike', 'not ilike'] 

def _is_expression( element ):
    return isinstance( element, tuple ) and len( element ) > 2 and _is_operator( element[0] )

class expression_leaf( object ):
    def __init__(self, operator, left, right ):
        self.operator = operator
        self.left = left
        self.right = right

    def parse( self ):
        return self

    def to_sql( self ):
        return "%s %s %s" % ( self.left, self.operator, self.right )

class expression( object ):
    def __init__( self, exp ):
        if isinstance( exp, tuple ):
            if not _is_leaf( exp ) and not _is_operator( exp[0] ):
                exp = list( exp )
        if isinstance( exp, list ):
            if len( exp ) == 1 and _is_leaf( exp[0] ):
                exp = exp[0]
            else:
                if not _is_operator( exp[0][0] ):
                    exp.insert( 0, '&' )
                    exp = tuple( exp )
                else:
                    exp = exp[0]

        self.exp = exp
        self.operator = '&'
        self.children = []

    def parse( self ):
        if _is_leaf( self.exp ):
            self.children.append( expression_leaf( self.exp[1], self.exp[0], self.exp[2] ).parse() )
        elif _is_expression( self.exp ):
            self.operator = self.exp[0]

            for element in self.exp[1:]:
                if not _is_operator( element ) and not _is_leaf(element):
                    self.children.append( expression(element).parse() )
                else:
                    if _is_leaf(element):
                        self.children.append( expression_leaf( element[1], element[0], element[2] ).parse() )
        return self

    def to_sql( self ):
        return "( %s )" % ((" %s " % {'&' : 'AND', '|' : 'OR' }[self.operator]).join([child.to_sql() for child in self.children]))
