# -*- coding: utf-8 -*-
""" Backport of Python 2.6's ast.py for Python 2.5
"""
__all__ = ['literal_eval']
try:
    from ast import literal_eval
except ImportError:
    from _ast import *
    from _ast import __version__


    def parse(expr, filename='<unknown>', mode='exec'):
        """
        Parse an expression into an AST node.
        Equivalent to compile(expr, filename, mode, PyCF_ONLY_AST).
        """
        return compile(expr, filename, mode, PyCF_ONLY_AST)


    def literal_eval(node_or_string):
        """
        Safely evaluate an expression node or a string containing a Python
        expression.  The string or node provided may only consist of the
        following Python literal structures: strings, numbers, tuples, lists,
        dicts, booleans, and None.
        """
        _safe_names = {'None': None, 'True': True, 'False': False}
        if isinstance(node_or_string, basestring):
            node_or_string = parse(node_or_string, mode='eval')
        if isinstance(node_or_string, Expression):
            node_or_string = node_or_string.body
        def _convert(node):
            if isinstance(node, Str):
                return node.s
            elif isinstance(node, Num):
                return node.n
            elif isinstance(node, Tuple):
                return tuple(map(_convert, node.elts))
            elif isinstance(node, List):
                return list(map(_convert, node.elts))
            elif isinstance(node, Dict):
                return dict((_convert(k), _convert(v)) for k, v
                            in zip(node.keys, node.values))
            elif isinstance(node, Name):
                if node.id in _safe_names:
                    return _safe_names[node.id]
            raise ValueError('malformed string')
        return _convert(node_or_string)
