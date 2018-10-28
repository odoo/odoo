# -*- coding: utf-8 -*-
import ast
import collections
import io
import token
from tokenize import generate_tokens

LITERAL_NAME = ('null', 'undefined', 'true', 'false')

__all__ = ['tokenize', 'parse', 'iterate', 'Alt', 'Type', 'Literal']

class _Marker(object):
    __slots__ = ['name']
    def __init__(self, name): self.name = name
    def __repr__(self): return '<%s>' % self.name

OP = _Marker('OP')
NAME = _Marker('NAME')
LITERAL = _Marker('LITERAL')
def tokenize(typespec):
    typespec = typespec.replace('$', 'jQuery')
    for toktype, string, _, _, _ in generate_tokens(io.StringIO(typespec).readline):
        if toktype == token.NAME:
            if string == 'or': # special case "A or B"
                # TODO: deprecation warning
                yield (OP, '|')
            else:
                yield (NAME, string)
        elif toktype == token.OP:
            if string in '|<>[].,':
                yield (OP, string)
            elif string == '>>':
                yield (OP, '>')
                yield (OP, '>')
            elif string == '*': # maybe?
                yield (NAME, 'any')
            elif string in '()':
                # TODO: deprecation warning
                # seems useless unless we add support for "..."
                continue
            else:
                raise ValueError("Unknown typespec operator %r" % string)
        elif toktype in (token.STRING, token.NUMBER): # enum-ish
            yield (LITERAL, ast.literal_eval(string))
        elif toktype == token.ENDMARKER:
            return
        elif toktype == token.NEWLINE:
            pass
        else:
            raise ValueError("Unknown typespec token %s" % token.tok_name[toktype])

Alt = collections.namedtuple('Alt', ['params'])
Literal = collections.namedtuple('Literal', ['value'])
Type = collections.namedtuple('Type', ['name', 'params'])

def iterate(t, fortype, forliteral):
    if isinstance(t, Alt):
        ps = Peekable(t.params)
        for param in ps:
            for it in iterate(param, fortype, forliteral):
                yield it
            if ps.peek(None):
                yield forliteral('|')
    elif isinstance(t, Type):
        yield fortype(t.name)
        if not t.params:
            return
        yield forliteral('<')
        ps = Peekable(t.params)
        for param in ps:
            for it in iterate(param, fortype, forliteral):
                yield it
            if ps.peek(None):
                yield forliteral(',')
        yield forliteral('>')
    elif isinstance(t, Literal):
        yield forliteral(t.value)
    else:
        raise ValueError('Unknown item %s' % t)

def parse(typespec):
    tokens = Peekable(tokenize(typespec))
    return parse_alt(tokens)

# alt = param
#     | param '|' alt
def parse_alt(tokens):
    alt = Alt([])
    while True:
        alt.params.append(parse_param(tokens))
        if not next_is(tokens, (OP, '|')):
            break
    return alt

# param = 'null' | 'undefined' | 'true' | 'false'
#       | number
#       | string
#       | typename '[]'
#       X '[' alt ']'
#       | typename '<' params '>'
# params = alt | alt ',' params
def parse_param(tokens):
    t, v = tokens.peek()
    if t == LITERAL or (t == NAME and v in LITERAL_NAME):
        next(tokens)
        return Literal(str(v))

    # # [typespec] # should this be Array<T> or an n-uple allowing multiple items?
    # if tok == (OP, '['):
    #     next(tokens)
    #     t = Type('Array', [parse_alt(tokens)])
    #     rest = next(tokens)
    #     expect(rest, (OP, ']'))
    #     return t

    t = Type(parse_typename(tokens), [])
    # type[]
    peek = tokens.peek(None)
    if peek == (OP, '['):
        next(tokens) # skip peeked
        expect(next(tokens), (OP, ']'))
        return Type('Array', [t])
    # type<typespec, ...>
    if peek == (OP, '<'):
        next(tokens) # skip peeked
        while True:
            t.params.append(parse_alt(tokens))
            n = next(tokens)
            if n == (OP, ','):
                continue
            if n == (OP, '>'):
                break
            raise ValueError("Expected OP ',' or OP ',', got %s '%s'" % n)
    return t

# typename = name | name '.' typename
def parse_typename(tokens):
    typename = []
    while True:
        (t, n) = next(tokens)
        if t != NAME:
            raise ValueError("Expected a name token, got %s '%s'" % (t, n))
        if n in LITERAL_NAME:
            raise ValueError("Expected a type name, got literal %s" % n)
        typename.append(n)
        if not next_is(tokens, (OP, '.')):
            break
    return '.'.join(typename)

def next_is(tokens, expected):
    """
    Consumes the next token if it's `expected` otherwise does not touch the
    tokens.

     Returns whether it consumed a token
    """
    if tokens.peek(None) == expected:
        next(tokens)
        return True
    return False

def expect(actual, expected):
    """ Raises ValueError if `actual` and `expected` are different

    :type actual: (object, str)
    :type expected: (object, str)
    """
    if actual != expected:
        raise ValueError("Expected %s '%s', got %s '%s'" % (expected + actual))


NONE = object()
class Peekable(object):
    __slots__ = ['_head', '_it']
    def __init__(self, iterable):
        self._head = NONE
        self._it = iter(iterable)

    def __iter__(self):
        return self
    def __next__(self):
        if self._head is not NONE:
            r, self._head = self._head, NONE
            return r
        return next(self._it)
    next = __next__

    def peek(self, default=NONE):
        if self._head is NONE:
            try:
                self._head = next(self._it)
            except StopIteration:
                if default is not NONE:
                    return default
                raise
        return self._head
