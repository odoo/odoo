#!/usr/bin/env python
# -*- encoding: utf-8 -*-

class expression( object ):
    """
    parse a domain expression
    examples:

    >>> e = [('foo', '=', 'bar')]
    >>> expression(e).parse().to_sql()
    'foo = bar'
    >>> e = [('id', 'in', [1,2,3])]
    >>> expression(e).parse().to_sql()
    'id in (1, 2, 3)'
    >>> e = [('field', '=', 'value'), ('field', '<>', 'value')]
    >>> expression(e).parse().to_sql()
    '( field = value AND field <> value )'
    >>> e = [('&', ('field', '<', 'value'), ('field', '>', 'value'))]
    >>> expression(e).parse().to_sql()
    '( field < value AND field > value )'
    >>> e = [('|', ('field', '=', 'value'), ('field', '=', 'value'))]
    >>> expression(e).parse().to_sql()
    '( field = value OR field = value )'
    >>> e = [('&', ('field1', '=', 'value'), ('field2', '=', 'value'), ('|', ('field3', '<>', 'value'), ('field4', '=', 'value')))]
    >>> expression(e).parse().to_sql()
    '( field1 = value AND field2 = value AND ( field3 <> value OR field4 = value ) )'
    >>> e = [('&', ('|', ('a', '=', '1'), ('b', '=', '2')), ('|', ('c', '=', '3'), ('d', '=', '4')))]
    >>> expression(e).parse().to_sql()
    '( ( a = 1 OR b = 2 ) AND ( c = 3 OR d = 4 ) )'
    >>> e = [('|', (('a', '=', '1'), ('b', '=', '2')), (('c', '=', '3'), ('d', '=', '4')))]
    >>> expression(e).parse().to_sql()
    '( ( a = 1 AND b = 2 ) OR ( c = 3 AND d = 4 ) )'
    >>> expression('fail').parse().to_sql()
    Traceback (most recent call last):
    ...
    ValueError: Bad expression: 'fail'
    >>> e = [('fail', 'is', 'True')]
    >>> expression(e).parse().to_sql()
    Traceback (most recent call last):
    ...
    ValueError: Bad expression: ('&', ('fail', 'is', 'True'))
    """

    def _is_operator( self, element ):
        return isinstance( element, str ) \
           and element in ['&','|']

    def _is_leaf( self, element ):
        return isinstance( element, tuple ) \
           and len( element ) == 3 \
           and element[1] in ('=', '<>', '<=', '<', '>', '>=', 'like', 'not like', 'ilike', 'not ilike', 'in', 'not in', 'child_of') 

    def _is_expression( self, element ):
        return isinstance( element, tuple ) \
           and len( element ) > 2 \
           and self._is_operator( element[0] )

    def __init__( self, exp ):
        if isinstance( exp, tuple ):
            if not self._is_leaf( exp ) and not self._is_operator( exp[0] ):
                exp = list( exp )
        if isinstance( exp, list ):
            if len( exp ) == 1 and self._is_leaf( exp[0] ):
                exp = exp[0]
            else:
                if not self._is_operator( exp[0][0] ):
                    exp.insert( 0, '&' )
                    exp = tuple( exp )
                else:
                    exp = exp[0]

        self.exp = exp
        self.operator = '&'
        self.children = []

        self.left, self.right = None, None
        if self._is_leaf(self.exp):
            self.left, self.operator, self.right = self.exp
            if isinstance(self.right, list):
                self.right = tuple(self.right)
        elif not self._is_expression( self.exp ):
            raise ValueError, 'Bad expression: %r' % (self.exp,)

    def parse( self ):
       if not self._is_leaf( self.exp ) and self._is_expression( self.exp ):
            self.operator = self.exp[0]

            for element in self.exp[1:]:
                if not self._is_operator( element ):
                    self.children.append( expression(element).parse() )
       return self

    def to_sql( self ):
        if self._is_leaf( self.exp ):
            return "%s %s %s" % ( self.left, self.operator, self.right )
        else:
            return "( %s )" % (" %s " % {'&' : 'AND', '|' : 'OR' }[self.operator]).join([child.to_sql() for child in self.children])


if __name__ == '__main__':
    import doctest
    doctest.testmod()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

