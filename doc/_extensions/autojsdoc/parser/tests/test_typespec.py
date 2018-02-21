# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from autojsdoc.parser import types

def test_parser():
    assert types.parse("MouseEvent|TouchEvent") == types.Alt([
        types.Type('MouseEvent', []),
        types.Type('TouchEvent', []),
    ])

    assert types.parse('Deferred<Object>') == types.Alt([
        types.Type('Deferred', [
            types.Alt([types.Type('Object', [])])
        ])
    ])

    assert types.parse('Object|undefined') == types.Alt([
        types.Type('Object', []),
        types.Literal('undefined'),
    ])
    assert types.parse('any[]') == types.Alt([
        types.Type('Array', [types.Type('any', [])])
    ])
    assert types.parse("'xml' | 'less'") == types.Alt([
        types.Literal('xml'),
        types.Literal('less'),
    ])
    assert types.parse('Foo<Bar | Bar[] | null>') == types.Alt([
        types.Type('Foo', [types.Alt([
            types.Type('Bar', []),
            types.Type('Array', [types.Type('Bar', [])]),
            types.Literal('null'),
        ])])
    ])
    assert types.parse('Function<Array<Object[]>>') == types.Alt([
        types.Type('Function', [types.Alt([
            types.Type('Array', [types.Alt([
                types.Type('Array', [
                    types.Type('Object', [])
                ])
            ])])
        ])])
    ])


def test_tokens():
    toks = list(types.tokenize('A'))
    assert toks == [(types.NAME, 'A')]

    toks = list(types.tokenize('"foo" | "bar"'))
    assert toks == [(types.LITERAL, 'foo'), (types.OP, '|'), (types.LITERAL, 'bar')]

    toks = list(types.tokenize('1 or 2'))
    assert toks == [(types.LITERAL, 1), (types.OP, '|'), (types.LITERAL, 2)]

    toks = list(types.tokenize('a.b.c.d'))
    assert toks == [
        (types.NAME, 'a'), (types.OP, '.'),
        (types.NAME, 'b'), (types.OP, '.'),
        (types.NAME, 'c'), (types.OP, '.'),
        (types.NAME, 'd'),
    ]

    toks = list(types.tokenize('Function<String, Object>'))
    assert toks == [
        (types.NAME, 'Function'),
        (types.OP, '<'),
        (types.NAME, 'String'),
        (types.OP, ','),
        (types.NAME, 'Object'),
        (types.OP, '>')
    ]

    toks = list(types.tokenize('Function<Array<Object[]>>'))
    assert toks == [
        (types.NAME, 'Function'),
        (types.OP, '<'),
        (types.NAME, 'Array'),
        (types.OP, '<'),
        (types.NAME, 'Object'),
        (types.OP, '['),
        (types.OP, ']'),
        (types.OP, '>'),
        (types.OP, '>')
    ]

def test_peekable():
    p = types.Peekable(range(5))

    assert p.peek() == 0
    assert next(p) == 0, "consuming should yield previously peeked value"
    next(p)
    next(p)
    assert next(p) == 3
    assert p.peek() == 4
    next(p)
    assert p.peek(None) is None
    with pytest.raises(StopIteration):
        p.peek()
    with pytest.raises(StopIteration):
        next(p)
