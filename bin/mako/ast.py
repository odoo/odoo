# ast.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""utilities for analyzing expressions and blocks of Python code, as well as generating Python from AST nodes"""

from mako import exceptions, pyparser, util
import re

class PythonCode(object):
    """represents information about a string containing Python code"""
    def __init__(self, code, **exception_kwargs):
        self.code = code
        
        # represents all identifiers which are assigned to at some point in the code
        self.declared_identifiers = util.Set()
        
        # represents all identifiers which are referenced before their assignment, if any
        self.undeclared_identifiers = util.Set()
        
        # note that an identifier can be in both the undeclared and declared lists.

        # using AST to parse instead of using code.co_varnames, code.co_names has several advantages:
        # - we can locate an identifier as "undeclared" even if its declared later in the same block of code
        # - AST is less likely to break with version changes (for example, the behavior of co_names changed a little bit
        # in python version 2.5)
        if isinstance(code, basestring):
            expr = pyparser.parse(code.lstrip(), "exec", **exception_kwargs)
        else:
            expr = code

        f = pyparser.FindIdentifiers(self, **exception_kwargs)
        f.visit(expr)

class ArgumentList(object):
    """parses a fragment of code as a comma-separated list of expressions"""
    def __init__(self, code, **exception_kwargs):
        self.codeargs = []
        self.args = []
        self.declared_identifiers = util.Set()
        self.undeclared_identifiers = util.Set()
        if isinstance(code, basestring):
            if re.match(r"\S", code) and not re.match(r",\s*$", code):
                # if theres text and no trailing comma, insure its parsed
                # as a tuple by adding a trailing comma
                code  += ","
            expr = pyparser.parse(code, "exec", **exception_kwargs)
        else:
            expr = code

        f = pyparser.FindTuple(self, PythonCode, **exception_kwargs)
        f.visit(expr)
        
class PythonFragment(PythonCode):
    """extends PythonCode to provide identifier lookups in partial control statements
    
    e.g. 
        for x in 5:
        elif y==9:
        except (MyException, e):
    etc.
    """
    def __init__(self, code, **exception_kwargs):
        m = re.match(r'^(\w+)(?:\s+(.*?))?:\s*(#|$)', code.strip(), re.S)
        if not m:
            raise exceptions.CompileException("Fragment '%s' is not a partial control statement" % code, **exception_kwargs)
        if m.group(3):
            code = code[:m.start(3)]
        (keyword, expr) = m.group(1,2)
        if keyword in ['for','if', 'while']:
            code = code + "pass"
        elif keyword == 'try':
            code = code + "pass\nexcept:pass"
        elif keyword == 'elif' or keyword == 'else':
            code = "if False:pass\n" + code + "pass"
        elif keyword == 'except':
            code = "try:pass\n" + code + "pass"
        else:
            raise exceptions.CompileException("Unsupported control keyword: '%s'" % keyword, **exception_kwargs)
        super(PythonFragment, self).__init__(code, **exception_kwargs)
        
        
class FunctionDecl(object):
    """function declaration"""
    def __init__(self, code, allow_kwargs=True, **exception_kwargs):
        self.code = code
        expr = pyparser.parse(code, "exec", **exception_kwargs)
                
        f = pyparser.ParseFunc(self, **exception_kwargs)
        f.visit(expr)
        if not hasattr(self, 'funcname'):
            raise exceptions.CompileException("Code '%s' is not a function declaration" % code, **exception_kwargs)
        if not allow_kwargs and self.kwargs:
            raise exceptions.CompileException("'**%s' keyword argument not allowed here" % self.argnames[-1], **exception_kwargs)
            
    def get_argument_expressions(self, include_defaults=True):
        """return the argument declarations of this FunctionDecl as a printable list."""
        namedecls = []
        defaults = [d for d in self.defaults]
        kwargs = self.kwargs
        varargs = self.varargs
        argnames = [f for f in self.argnames]
        argnames.reverse()
        for arg in argnames:
            default = None
            if kwargs:
                arg = "**" + arg
                kwargs = False
            elif varargs:
                arg = "*" + arg
                varargs = False
            else:
                default = len(defaults) and defaults.pop() or None
            if include_defaults and default:
                namedecls.insert(0, "%s=%s" % (arg, pyparser.ExpressionGenerator(default).value()))
            else:
                namedecls.insert(0, arg)
        return namedecls

class FunctionArgs(FunctionDecl):
    """the argument portion of a function declaration"""
    def __init__(self, code, **kwargs):
        super(FunctionArgs, self).__init__("def ANON(%s):pass" % code, **kwargs)
