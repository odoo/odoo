#@+leo-ver=4
#@+node:@file task.py
#@@language python
#@<< Copyright >>
#@+node:<< Copyright >>
############################################################################
#   Copyright (C) 2005, 2006, 2007, 2008 by Reithinger GmbH
#   mreithinger@web.de
#
#   This file is part of faces.
#
#   faces is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   faces is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
############################################################################

#@-node:<< Copyright >>
#@nl
"""
This module contains all classes for project plan objects
"""
#@<< Imports >>
#@+node:<< Imports >>
import pcalendar
import resource
import types
import sys
import datetime
import operator as op
import warnings
import locale
import weakref
import opcode
import new
try:
    set
except NameError:
    from sets import Set as set
#@-node:<< Imports >>
#@nl

_is_source = True

STRICT = 3
SLOPPY = 2
SMART = 1

#@+others
#@+node:Exceptions
#@+node:class AttributeError
class AttributeError(AttributeError):
    #@	<< class AttributeError declarations >>
    #@+node:<< class AttributeError declarations >>
    is_frozen = False


    #@-node:<< class AttributeError declarations >>
    #@nl
#@-node:class AttributeError
#@+node:class RecursionError
class RecursionError(Exception):
    """This exception is raised in cas of cirular dependencies
    within an project"""
    #@	<< class RecursionError declarations >>
    #@+node:<< class RecursionError declarations >>
    pass


    #@-node:<< class RecursionError declarations >>
    #@nl
#@-node:class RecursionError
#@+node:class _IncompleteError
class _IncompleteError(Exception):
    """This exception is raised, when there is not enough
    data specified to calculate as task"""
    #@	@+others
    #@+node:__init__
    def __init__(self, *args):
        if isinstance(args[0], (basestring)):
            Exception.__init__(self, *args)
        else:
            Exception.__init__(self,
                               "Not enough data for calculating task, "\
                               "maybe you have a recursive reference.",
                               *args)
    #@-node:__init__
    #@-others
#@-node:class _IncompleteError
#@-node:Exceptions
#@+node:Proxies for self referencing
#@+node:class _MeProxy
class _MeProxy(object):
    """
    A Proxy class for the me attribute of tasks in the compile case
    """
    #@	<< declarations >>
    #@+node:<< declarations >>
    __slots__ = "task"

    #@-node:<< declarations >>
    #@nl
    #@	@+others
    #@+node:__init__
    def __init__(self, task):
        object.__setattr__(self, "task", task)
    #@-node:__init__
    #@+node:__getattr__
    def __getattr__(self, name):
        if self.task._is_frozen:
            return getattr(self.task, name)

        if name in ("name", "up", "root", "path",
                    "depth", "index", "calendar",
                    "children", "resource", "balance"):
            return getattr(self.task, name)

        value = self.task.__dict__.get(name, _NEVER_USED_)
        def make_val(default):
            if value is _NEVER_USED_: return default
            return value

        if name in ("start", "end"):
            return self.task._to_start(make_val("1.1.2006"))

        if name in ("length", "effort", "duration", "todo", "done",
                    "buffer", "performed", "performed_effort",
                    "performed_end", "performed_start",
                    "performed_work_time" ):
            return self.task._to_delta(make_val("0d"))

        if name in ("complete", "priority", "efficiency"):
            return make_val(0)

        if value is _NEVER_USED_:
            raise AttributeError("'%s' is not a valid attribute." % (name))

        return value
    #@-node:__getattr__
    #@+node:__setattr__
    def __setattr__(self, name, value):
        self.task._set_attrib(name, value)
    #@-node:__setattr__
    #@+node:__iter__
    def __iter__(self):
        return iter(self.task)
    #@nonl
    #@-node:__iter__
    #@+node:add_attrib
    def add_attrib(self, name_or_iter, val=None):
        if not isinstance(name_or_iter, str):
            for n, v in name_or_iter:
                setattr(self, n, v)
        else:
            setattr(self, name_or_iter, val)
    #@-node:add_attrib
    #@-others
#@nonl
#@-node:class _MeProxy
#@+node:class _MeProxyRecalc
class _MeProxyRecalc(_MeProxy):
    """
    A Proxy class for the me attribute of tasks in the recalc case
    """
    #@	@+others
    #@+node:__setattr__
    def __setattr__(self, name, value):
        if self.task._properties.has_key(name):
            self.task._set_attrib(name, value)
    #@-node:__setattr__
    #@-others
#@-node:class _MeProxyRecalc
#@+node:class _MeProxyError
class _MeProxyError(_MeProxy):
    #@	<< declarations >>
    #@+node:<< declarations >>
    __slots__ = ("task", "attrib", "exc")

    #@-node:<< declarations >>
    #@nl
    #@	@+others
    #@+node:__init__
    def __init__(self, task, attrib, exc):
        _MeProxy.__init__(self, task)
        object.__setattr__(self, "attrib", attrib)
        object.__setattr__(self, "exc", exc)
    #@-node:__init__
    #@+node:__setattr__
    def __setattr__(self, name, value):
        if name == self.attrib or not self.attrib:
            raise self.exc
    #@-node:__setattr__
    #@-others
#@-node:class _MeProxyError
#@+node:class _MeProxyWarn
class _MeProxyWarn(_MeProxy):
    #@	<< declarations >>
    #@+node:<< declarations >>
    __slots__ = ("task", "attrib", "message")

    #@-node:<< declarations >>
    #@nl
    #@	@+others
    #@+node:__init__
    def __init__(self, task, attrib, message):
        _MeProxy.__init__(self, task)
        object.__setattr__(self, "attrib", attrib)
        object.__setattr__(self, "message", message)
    #@-node:__init__
    #@+node:__setattr__
    def __setattr__(self, name, value):
        if name == self.attrib or not self.attrib:
            warnings.warn(self.message, RuntimeWarning, 2)
            if not self.attrib:
                #warn only one time!
                object.__setattr__(self, "attrib", 1)
    #@-node:__setattr__
    #@-others
#@-node:class _MeProxyWarn
#@-node:Proxies for self referencing
#@+node:Task instrumentation
#@+doc
# This section contains code for byte code instrumenting
# the task functions
#@-doc
#@nonl
#@+node:_int_to_arg
def _int_to_arg(value):
    return value % 256, value / 256
#@-node:_int_to_arg
#@+node:_correct_labels
def _correct_labels(old_code, new_code):
    #@    << localize dot variables >>
    #@+node:<< localize dot variables >>
    hasjrel = opcode.hasjrel
    hasjabs = opcode.hasjabs
    HAVE_ARGUMENT = opcode.HAVE_ARGUMENT
    #@nonl
    #@-node:<< localize dot variables >>
    #@nl
    #@    << loop initialization >>
    #@+node:<< loop initialization >>
    labels = {}
    old_new_map = {} # map old code offset to new code offset
    n = len(old_code)
    i = 0
    j = 0
    #@nonl
    #@-node:<< loop initialization >>
    #@nl
    while i < n:
        op = old_code[i]
        nop = new_code[j]
        old_new_map[i] = j
        i = i + 1
        j = j + 1
        if op >= HAVE_ARGUMENT:
            oparg = old_code[i] + old_code[i + 1] * 256
            i = i + 2
            j = j + 2
            if nop != op:
                j += 3 # skip the 3 addition opcodes for attrib access
            else:
                #@                << add label if necessary >>
                #@+node:<< add label if necessary >>
                label = -1
                if op in hasjrel:
                    label = i + oparg
                elif op in hasjabs:
                    label = oparg
                if label >= 0:
                    labels[i] = label
                #@nonl
                #@-node:<< add label if necessary >>
                #@nl

    for offset, label in labels.iteritems():
        new_offset = old_new_map[offset]
        new_label = old_new_map[label]
        op = new_code[new_offset - 3]
        #change jump arguments
        if op in hasjrel:
            jump = _int_to_arg(new_label - new_offset)
            new_code[new_offset - 2:new_offset] = jump
        elif op in hasjabs:
            new_code[new_offset - 2:new_offset] = _int_to_arg(new_label)
#@nonl
#@-node:_correct_labels
#@+node:_instrument
def _instrument(func):
    #@    << localize dot variables >>
    #@+node:<< localize dot variables >>
    opname = opcode.opname
    opmap = opcode.opmap
    jumps = opcode.hasjrel + opcode.hasjabs
    HAVE_ARGUMENT = opcode.HAVE_ARGUMENT
    co = func.func_code
    local_names = co.co_varnames
    all_names = list(co.co_names)
    global_names = set()
    #@-node:<< localize dot variables >>
    #@nl
    #@    << define local functions list_to_dict and is_local >>
    #@+node:<< define local functions list_to_dict and is_local >>
    def list_to_dict(l):
        return dict([(t[1], t[0]) for t in enumerate(l)])

    def is_local(name):
        return name[0] == "_" and name != "__constraint__"
    #@nonl
    #@-node:<< define local functions list_to_dict and is_local >>
    #@nl

    #convert code
    #@    << loop initialization >>
    #@+node:<< loop initialization >>
    # all_name_map maps names to the all_names index
    # (same like all_names.index())
    all_name_map = list_to_dict(all_names)
    if not all_name_map.has_key("me"):
        all_name_map["me"] = len(all_names)
        all_names.append("me")

    #<python 2.5>
    for ln in local_names:
        if not all_name_map.has_key(ln):
            all_name_map[ln] = len(all_names)
            all_names.append(ln)
    #</python 2.5>

    new_local_names = filter(is_local, local_names)
    new_local_name_map = list_to_dict(new_local_names)

    me_arg = _int_to_arg(all_name_map["me"])
    old_lnotab = map(ord, co.co_lnotab)
    new_lnotab = []
    tab_pos = 0
    try:
        next_tab_point = old_lnotab[0]
    except IndexError:
        next_tab_point = None

    last_tab_point = 0
    code = map(ord, co.co_code)
    new_code = []
    has_labels = False
    n = len(code)
    i = 0
    #@nonl
    #@-node:<< loop initialization >>
    #@nl
    while i < n:
        if i == next_tab_point:
            #@            << calculate new tab point >>
            #@+node:<< calculate new tab point >>
            increment = len(new_code) - last_tab_point
            new_lnotab.extend((increment, old_lnotab[tab_pos + 1]))
            tab_pos += 2
            try:
                next_tab_point = i + old_lnotab[tab_pos]
                last_tab_point = len(new_code)
            except IndexError:
                next_tab_point = -1
            #@nonl
            #@-node:<< calculate new tab point >>
            #@nl

        op = code[i]
        i += 1
        if op >= HAVE_ARGUMENT:
            #@            << calculate argument >>
            #@+node:<< calculate argument >>
            arg0 = code[i]
            arg1 = code[i+1]
            oparg = arg0 + arg1 * 256
            #@nonl
            #@-node:<< calculate argument >>
            #@nl
            i += 2

            if opname[op] == "LOAD_GLOBAL":
                global_names.add(oparg)

            elif opname[op] == "STORE_FAST":
                #@                << change "store fast" to "store attribute" >>
                #@+node:<< change "store fast" to "store attribute" >>
                name = local_names[oparg]
                if not is_local(name):
                    new_code.append(opmap["LOAD_GLOBAL"])
                    new_code.extend(me_arg)
                    op = opmap["STORE_ATTR"]
                    arg0, arg1 = _int_to_arg(all_name_map[name])
                else:
                    arg0, arg1 = _int_to_arg(new_local_name_map[name])
                #@nonl
                #@-node:<< change "store fast" to "store attribute" >>
                #@nl

            elif opname[op] == "LOAD_FAST":
                #@                << change "load fast" to "load attribute" >>
                #@+node:<< change "load fast" to "load attribute" >>
                name = local_names[oparg]
                if not is_local(name):
                    new_code.append(opmap["LOAD_GLOBAL"])
                    new_code.extend(me_arg)
                    op = opmap["LOAD_ATTR"]
                    arg0, arg1 = _int_to_arg(all_name_map[name])
                else:
                    arg0, arg1 = _int_to_arg(new_local_name_map[name])
                #@nonl
                #@-node:<< change "load fast" to "load attribute" >>
                #@nl

            elif op in jumps:
                has_labels = True

            new_code.extend((op, arg0, arg1))
        else:
            new_code.append(op)

    if has_labels:
        _correct_labels(code, new_code)

    #@    << create new code and function objects and return >>
    #@+node:<< create new code and function objects and return >>
    new_code = "".join(map(chr, new_code))
    new_lnotab = "".join(map(chr, new_lnotab))
    new_co = new.code(co.co_argcount,
                      len(new_local_names),
                      max(co.co_stacksize, 2),
                      co.co_flags,
                      new_code,
                      co.co_consts,
                      tuple(all_names),
                      tuple(new_local_names),
                      co.co_filename,
                      co.co_name,
                      co.co_firstlineno,
                      new_lnotab,
                      co.co_freevars,
                      co.co_cellvars)


    func =  new.function(new_co,
                         func.func_globals,
                         func.func_name,
                         func.func_defaults,
                         func.func_closure)
    func.global_names = tuple([all_names[index] for index in global_names])
    return func
    #@nonl
    #@-node:<< create new code and function objects and return >>
    #@nl
#@nonl
#@-node:_instrument
#@-node:Task instrumentation
#@+node:Wrappers
#@+node:class _Path
class _Path(object):
    """
    This class represents an instrumented path, to
    a task. If it points to an attribute of a task, it
    not only returns the value of the attribute. You can also
    find out the source attribute (task and attribute name)
    of the value.
    """
    #@	@+others
    #@+node:__init__
    def __init__(self, task, path_str):
        self._task = task
        self._path_str = path_str
    #@-node:__init__
    #@+node:__getattr__
    def __getattr__(self, name):
        new = getattr(self._task, name)
        if isinstance(new, Task):
            return _Path(new, self._path_str + "." + name)

        return _ValueWrapper(new, [(self._task, name)])
    #@-node:__getattr__
    #@+node:__str__
    def __str__(self):
        return self._path_str
    #@-node:__str__
    #@+node:__iter__
    def __iter__(self):
        return iter(self._task)
    #@nonl
    #@-node:__iter__
    #@-others

#@-node:class _Path
#@+node:_val
#helper functions for _ValueWrapper
#----------------------------------

def _val(val):
    if isinstance(val, _ValueWrapper):
        return val._value

    return val
#@-node:_val
#@+node:_ref
def _ref(val):
    if isinstance(val, _ValueWrapper):
        return val._ref

    return []
#@-node:_ref
#@+node:_sref
def _sref(val, ref):
    if isinstance(val, _ValueWrapper):
        val._ref = ref
#@nonl
#@-node:_sref
#@+node:_refsum
def _refsum(refs):
    return reduce(lambda a, b: a + b, refs, [])
#@nonl
#@-node:_refsum
#@+node:class _ValueWrapper


class _ValueWrapper(object):
    """
    This class represents a value, of a task attribute or
    a return value of a task method. It contains the value,
    and the supplier of that value
    """
    #@	@+others
    #@+node:__init__
    def __init__(self, value, ref):
        self._value = value
        self._ref = ref
    #@-node:__init__
    #@+node:unicode
    def unicode(self, *args):
        if isinstance(self._value, str):
            return unicode(self._value, *args)

        return unicode(self._value)
    #@nonl
    #@-node:unicode
    #@+node:_vw
    def _vw(self, operand, *args):
        refs = _refsum(map(_ref, args))
        vals = map(_val, args)
        result = operand(*vals)
        return self.__class__(result, refs)
    #@-node:_vw
    #@+node:_cmp
    def _cmp(self, operand, *args):
        refs = _refsum(map(_ref, args))
        vals = map(_val, args)
        result = operand(*vals)
        map(lambda a: _sref(a, refs), args)
        return result
    #@-node:_cmp
    #@+node:__getattr__
    def __getattr__(self, name):
        return getattr(self._value, name)
    #@-node:__getattr__
    #@+node:__getitem__
    def __getitem__(self, slice):
        return self.__class__(self._value[slice], self._ref)
    #@nonl
    #@-node:__getitem__
    #@+node:__str__
    def __str__(self): return str(self._value)
    #@-node:__str__
    #@+node:__unicode__
    def __unicode__(self): return unicode(self._value)
    #@nonl
    #@-node:__unicode__
    #@+node:__repr__
    def __repr__(self): return repr(self._value)
    #@-node:__repr__
    #@+node:__nonzero__
    def __nonzero__(self): return bool(self._value)
    #@-node:__nonzero__
    #@+node:__lt__
    def __lt__(self, other): return self._cmp(op.lt, self, other)
    #@-node:__lt__
    #@+node:__le__
    def __le__(self, other): return self._cmp(op.le, self, other)
    #@-node:__le__
    #@+node:__eq__
    def __eq__(self, other): return self._cmp(op.eq, self, other)
    #@-node:__eq__
    #@+node:__ne__
    def __ne__(self, other): return self._cmp(op.ne, self, other)
    #@-node:__ne__
    #@+node:__gt__
    def __gt__(self, other): return self._cmp(op.gt, self, other)
    #@-node:__gt__
    #@+node:__ge__
    def __ge__(self, other): return self._cmp(op.ge, self, other)
    #@-node:__ge__
    #@+node:__add__
    def __add__(self, other): return self._vw(op.add, self, other)
    #@nonl
    #@-node:__add__
    #@+node:__sub__
    def __sub__(self, other): return self._vw(op.sub, self, other)
    #@-node:__sub__
    #@+node:__mul__
    def __mul__(self, other): return self._vw(op.mul, self, other)
    #@-node:__mul__
    #@+node:__floordiv__
    def __floordiv__(self, other): return self._vw(op.floordiv, self, other)
    #@-node:__floordiv__
    #@+node:__mod__
    def __mod__(self, other): return self._vw(op.mod, self, other)
    #@-node:__mod__
    #@+node:__divmod__
    def __divmod__(self, other): return self._vw(op.divmod, self, other)
    #@-node:__divmod__
    #@+node:__pow__
    def __pow__(self, other): return self._vw(op.pow, self, other)
    #@-node:__pow__
    #@+node:__lshift__
    def __lshift__(self, other): return self._vw(op.lshift, self, other)
    #@-node:__lshift__
    #@+node:__rshift__
    def __rshift__(self, other): return self._vw(op.rshift, self, other)
    #@-node:__rshift__
    #@+node:__and__
    def __and__(self, other): return self._vw(op.and_, self, other)
    #@-node:__and__
    #@+node:__xor__
    def __xor__(self, other): return self._vw(op.xor, self, other)
    #@-node:__xor__
    #@+node:__or__
    def __or__(self, other): return self._vw(op.or_, self, other)
    #@-node:__or__
    #@+node:__div__
    def __div__(self, other): return self._vw(op.div, self, other)
    #@-node:__div__
    #@+node:__radd__
    def __radd__(self, other): return self._vw(op.add, other, self)
    #@-node:__radd__
    #@+node:__rsub__
    def __rsub__(self, other): return self._vw(op.sub, other, self)
    #@-node:__rsub__
    #@+node:__rmul__
    def __rmul__(self, other): return self._vw(op.mul, other, self)
    #@-node:__rmul__
    #@+node:__rdiv__
    def __rdiv__(self, other): return self._vw(op.div, other, self)
    #@-node:__rdiv__
    #@+node:__rtruediv__
    def __rtruediv__(self, other): return self._vw(op.truediv, other, self)
    #@-node:__rtruediv__
    #@+node:__rfloordiv__
    def __rfloordiv__(self, other): return self._vw(op.floordiv, other, self)
    #@-node:__rfloordiv__
    #@+node:__rmod__
    def __rmod__(self, other): return self._vw(op.mod, other, self)
    #@-node:__rmod__
    #@+node:__rdivmod__
    def __rdivmod__(self, other): return self._vw(op.divmod, other, self)
    #@-node:__rdivmod__
    #@+node:__rpow__
    def __rpow__(self, other): return self._vw(op.pow, other, self)
    #@-node:__rpow__
    #@+node:__rlshift__
    def __rlshift__(self, other): return self._vw(op.lshift, other, self)
    #@-node:__rlshift__
    #@+node:__rrshift__
    def __rrshift__(self, other): return self._vw(op.rshift, other, self)
    #@-node:__rrshift__
    #@+node:__rand__
    def __rand__(self, other): return self._vw(op.and_, other, self)
    #@-node:__rand__
    #@+node:__rxor__
    def __rxor__(self, other): return self._vw(op.xor, other, self)
    #@-node:__rxor__
    #@+node:__ror__
    def __ror__(self, other): return self._vw(op.or_, other, self)
    #@-node:__ror__
    #@+node:__int__
    def __int__(self): return int(self._value)
    #@-node:__int__
    #@+node:__long__
    def __long__(self): return long(self._value)
    #@-node:__long__
    #@+node:__float__
    def __float__(self): return float(self._value)
    #@-node:__float__
    #@+node:__len__
    def __len__(self): return len(self._value)
    #@-node:__len__
    #@+node:__iter__
    def __iter__(self): return iter(self._value)
    #@-node:__iter__
    #@+node:__hash__
    def __hash__(self): return hash(self._value)
    #@-node:__hash__
    #@-others
#@-node:class _ValueWrapper
#@-node:Wrappers
#@+node:Utilities
#@+node:class _NEVER_USED_
class _NEVER_USED_:
    pass

#@-node:class _NEVER_USED_
#@+node:class _StringConverter
class _StringConverter(object):
    """This class is a helper for the to_string mechanism
    of tasks"""
    #@	@+others
    #@+node:__init__
    def __init__(self, source, format=None):
        self.source = source
        self.format = format
    #@-node:__init__
    #@+node:__getitem__
    def __getitem__(self, format):
        return _StringConverter(self.source, format)
    #@-node:__getitem__
    #@+node:__getattr__
    def __getattr__(self, name):
        class StrWrapper(object):
            def __init__(self, value, name, source, format):
                self._value = value
                self.name = name
                self.source = source
                self.format = format

            def __call__(self, arg):
                formatter = self.source.formatter(self.name,
                                                  arg,
                                                  self.format)
                return formatter(self._value(arg))

        value = getattr(self.source, name)
        if callable(value):
            #for methods the wrapper has to
            return StrWrapper(value, name, self.source, self.format)

        formatter = self.source.formatter(name, format=self.format)
        return formatter(value)
    #@-node:__getattr__
    #@-others
#@-node:class _StringConverter
#@+node:Multi
def Multi(val, **kwargs):
    """returns a directory for mutlivalued attributes"""
    return dict(_default=val, **kwargs)
#@nonl
#@-node:Multi
#@+node:create_relative_path
def create_relative_path(from_, to_):
    """
    creates a relative path from absolute path
    from_ to absolute path to_
    """
    from_ = from_.split(".")
    to_ = to_.split(".")

    for i, parts in enumerate(zip(from_, to_)):
        from_part, to_part = parts
        if from_part != to_part:
            break

    from_ = from_[i:]
    to_ = to_[i:]
    return "up." * len(from_) + ".".join(to_)
#@nonl
#@-node:create_relative_path
#@+node:create_absolute_path
def create_absolute_path(from_, to_):
    """
    creates a absolute path from absolute path
    from_ to relative path to_
    """
    from_ = from_.split(".")
    to_ = to_.split(".")

    for i, part in enumerate(to_):
        if part != "up":
            break

    from_ = from_[:-i]
    to_ = to_[i:]
    return "%s.%s" % (".".join(from_), ".".join(to_))


#@-node:create_absolute_path
#@+node:_split_path
def _split_path(path):
    try:
        index = path.rindex(".")
        return path[:index], path[index + 1:]
    except:
        return path
#@-node:_split_path
#@+node:_to_datetime
_to_datetime = pcalendar.to_datetime
#@nonl
#@-node:_to_datetime
#@+node:_get_tasks_of_sources
def _get_tasks_of_sources(task, attrib_filter="end,start,effort,length,duration"):
    #return all source tasks, this task is dependend on

    dep_tasks = {}

    while task:
        for dep in task._sources.values():
            for d in dep:
                path, attrib = _split_path(d)
                if attrib and attrib_filter.find(attrib) >= 0:
                    dep_tasks[path] = True

        task = task.up

    return dep_tasks.keys()
#@-node:_get_tasks_of_sources
#@+node:_build_balancing_list
def _build_balancing_list(tasks):
    """
    Returns a specialy sorted list of tasks.
    If the tasks will allocate resources in the sorting order of that list
    correct balancing is ensured
    """

    # first sort the list for attributes
    index = 0
    balancing_list = [(-t.priority, t.balance, index, t) for index, t in enumerate(tasks)]
    balancing_list.sort()

    #print
    #for p, b, i, t  in balancing_list:
    #    print p, b, i, t.path

    balancing_list = [ t for p, b, i, t  in balancing_list ]

    #now correct the presorted list:
    #if task a is dependent on task b, b will be moved before a

    done_map = { }
    count = len(balancing_list)
    while len(done_map) < count:
        for i in range(count):
            to_inspect = balancing_list[i]
            if done_map.has_key(to_inspect):
                continue

            done_map[to_inspect] = True
            break
        else:
            break

        #@        << define inspect_depends_on >>
        #@+node:<< define inspect_depends_on >>
        inspect_path = to_inspect.path + "."
        sources = _get_tasks_of_sources(to_inspect)
        sources = [ s + "." for s in sources
                    if not inspect_path.startswith(s) ]

        # the if in the later line ignores assignments like
        # like start = up.start (i.e. references to parents)
        # this will be handled in the second if of inspect_depends_on
        # and can cause errors otherwise

        def inspect_depends_on(task):
            cmp_path = task.path + "."
            for src in sources:
                if cmp_path.startswith(src):
                    #task is a source of to_inspect
                    return True

            if inspect_path.startswith(cmp_path):
                #to_inspect is a child of task
                return True

            return False
        #@nonl
        #@-node:<< define inspect_depends_on >>
        #@nl
        for j in range(i + 1, count):
            check_task = balancing_list[j]
            if done_map.has_key(check_task):
                continue

            if inspect_depends_on(check_task):
                del balancing_list[j]
                balancing_list.insert(i, check_task)
                i += 1 # to_inspect is now at i + 1


    return balancing_list
#@-node:_build_balancing_list
#@+node:_as_string
def _as_string(val):
    if isinstance(val, basestring):
        return '"""%s"""' % val.replace("\n", "\\n")

    if isinstance(val, pcalendar._WorkingDateBase):
        return '"%s"' % val.strftime("%Y-%m-%d %H:%M")

    if isinstance(val, datetime.datetime):
        return '"%s"' % val.strftime("%Y-%m-%d %H:%M")

    if isinstance(val, datetime.timedelta):
        return '"%id %iM"' % (val.days, val.seconds / 60)

    if isinstance(val, tuple):
        result = map(_as_string, val)
        return "(%s)" % ", ".join(result)

    if isinstance(val, list):
        result = map(_as_string, val)
        return "[%s]" % ", ".join(result)

    if isinstance(val, resource.Resource):
        return val._as_string()

    if isinstance(val, Task):
        return val.path

    return str(val)
#@-node:_as_string
#@+node:_step_tasks
def _step_tasks(task):
    if isinstance(task, Task):
        yield task

    stack = [iter(task.children)]
    while stack:
        for task in stack[-1]:
            yield task

            if task.children:
                stack.append(iter(task.children))
                break
        else:
            stack.pop()
#@-node:_step_tasks
#@-node:Utilities
#@+node:Cache
instrumentation_cache = {}
balancing_cache = {}

def clear_cache():
    instrumentation_cache.clear()
    balancing_cache.clear()
#@nonl
#@-node:Cache
#@+node:Resource Allocators
#@+others
#@+node:VariableLoad
def VariableLoad(limit=0):
    """
    Allocates the resource with maximal possible load.
    If limit is given, a the load is at least limit or more.
    """
    try:
        balance = me.balance
    except NameError:
        balance = SLOPPY

    if balance != SLOPPY:
        raise RuntimeError("You may specify variable_load only with balance=SLOPPY")

    return -limit
#@-node:VariableLoad
#@+node:_calc_load
def _calc_load(task, resource):
    #changed at the resource instance
    load = resource.__dict__.get("load")
    if load is not None: return load

    load = task.__dict__.get("load")
    if load is not None: return load

    #inherited by the task
    return min(task.load, task.max_load, resource.max_load or 100.0)
#@-node:_calc_load
#@+node:_calc_maxload
def _calc_maxload(task, resource):
    #changed at the resource instance
    max_load = resource.__dict__.get("max_load")
    if max_load: return max_load

    #an explicit load can overwrite max_load
    load = max(resource.__dict__.get("load", 0),
               task.__dict__.get("load"), 0)

    #change at the task
    max_load = task.__dict__.get("max_load")
    if max_load: return max(max_load, load)

    #inherited by the resource
    max_load = resource.max_load
    if max_load: return max(max_load, load)

    #inherited by the task
    return max(task.max_load, load)
#@-node:_calc_maxload
#@+node:class AllocationAlgorithm
class AllocationAlgorithm(object):
    """This class is a base for resource allocation algorithms"""
    #@	@+others
    #@+node:test_allocation
    def test_allocation(self, task, resource):
        """This method simulates the allocation of a specific resource.
        It returns a list of values representing the state of the allocation.
        The task allocator calls test_allocation for every alternative resource.
        It compares the first items of all return lists, and allocates the
        resource with the minum first item value"""
        return (task.end, )
    #@-node:test_allocation
    #@+node:allocate
    def allocate(self, task, state):
        """This method eventually allocates a specific resource.
        State is the return list of test_allocation"""
        pass
    #@-node:allocate
    #@-others
#@-node:class AllocationAlgorithm
#@+node:class StrictAllocator
class StrictAllocator(AllocationAlgorithm):
    """This class implements the STRICT resource allocation"""
    #@	@+others
    #@+node:_distribute_len_loads
    def _distribute_len_loads(self, task, resource, effort, length):
        # A special load calculation, if effort and length are given.
        # and the resources have a defined maxload, the load must be
        # individually calculated for each resource.

        # Formulars: r=resources, t=task
        #   effort = length * efficiency(t) * sum[load(r) * effiency(r)]
        #   ==> sum_load = sum[load(r) * effiency(r)]
        #                = effort / (length * efficiency(t))
        #

        sum_load = float(effort) / (task.efficiency * length)

        # algorithm:
        # The goal is to distribute the load (norm_load) equally
        # to all resources. If a resource has a max_load(r) < norm_load
        # the load of this resource will be max_load(r), and the other
        # resources will have another (higher) norm_load

        max_loads = map(lambda r: (_calc_maxload(task, r), r), resource)
        max_loads.sort()

        efficiency_sum = sum(map(lambda r: r.efficiency, resource))
        norm_load = sum_load / efficiency_sum

        loads = {}
        for max_load, r in max_loads[:-1]:
            if max_load < norm_load:
                loads[r] = max_load
                efficiency_sum -= r.efficiency
                sum_load -= max_load * r.efficiency
                norm_load = sum_load / efficiency_sum
            else:
                loads[r] = norm_load

        max_load, r = max_loads[-1]
        loads[r] = norm_load
        return loads
    #@-node:_distribute_len_loads
    #@+node:test_allocation
    def test_allocation(self, task, resource):
        effort = task.__dict__.get("effort")
        to_start = task._to_start
        to_end = task._to_end
        to_delta = task._to_delta

        if task.performed_end:
            start = to_start(max(task.performed_end,
                                 task.root.calendar.now,
                                 task.start))
        else:
            start = task.start
            if task.root.has_actual_data and task.complete == 0:
                start = max(start, to_start(task.root.calendar.now))

        base_start = to_start(task.performed_start or task.start)
        calc_load = lambda r: _calc_load(task, r)
        loads = map(lambda r: (r, calc_load(r)), resource)

        length = task.__dict__.get("length")
        duration = task.__dict__.get("duration")
        end = task.__dict__.get("end")

        #@    << correct length >>
        #@+node:<< correct length >>
        if length is not None:
            length = to_delta(max(length - (task.start - base_start), 0))
        #@nonl
        #@-node:<< correct length >>
        #@nl
        #@    << correct duration >>
        #@+node:<< correct duration >>
        if duration is not None:
            delta = task.start.to_datetime() - base_start.to_datetime()
            delta = to_delta(delta, True)
            duration = to_delta(max(duration - delta, 0), True)
        #@nonl
        #@-node:<< correct duration >>
        #@nl
        #@    << check end >>
        #@+node:<< check end >>
        if end is not None:
            length = end - start
            if length <= 0: return False
        #@nonl
        #@-node:<< check end >>
        #@nl
        #@    << correct effort and (re)calculate length >>
        #@+node:<< correct effort and (re)calculate length >>
        if effort is not None:
            effort -= task.performed_effort
            effort = to_delta(max(effort, 0))
            if effort <= 0: return False

            if length is not None:
                #if length and effort is set, the load will be calculated
                length = length or task.calendar.minimum_time_unit
                loads = self._distribute_len_loads(task, resource,
                                                   effort, length)
                def calc_load(res):
                    return loads[res]
            else:
                #the length depends on the count of resources
                factor = sum(map(lambda a: a[0].efficiency * a[1],
                                 loads)) * task.efficiency
                length = effort / factor
        #@nonl
        #@-node:<< correct effort and (re)calculate length >>
        #@nl
        #@    << set adjust_date and delta >>
        #@+node:<< set adjust_date and delta >>
        if length is not None:
            adjust_date = lambda date: date
            delta = to_delta(length).round()
        else:
            assert(duration is not None)
            adjust_date = _to_datetime
            delta = datetime.timedelta(minutes=duration)
        #@nonl
        #@-node:<< set adjust_date and delta >>
        #@nl

        # find the earliest start date
        start, book_load\
               = self.balance(task, start, delta, adjust_date,
                              calc_load, resource)

        end = to_end(start + delta)
        start = to_start(start)

        if effort is None:
            #length is frozen ==> a new effort will be calculated
            factor = sum(map(lambda a: a[1], loads))
            length = end - start

            effort = to_delta(length * factor\
                              + task.performed_effort).round()

        return (end, book_load), resource, calc_load, start, effort
    #@-node:test_allocation
    #@+node:allocate
    def allocate(self, task, state):
        # now really book the resource
        end_bl, resource, calc_load, start, effort = state
        end = end_bl[0]
        cal = task.root.calendar
        to_start = task._to_start
        to_end = task._to_end
        to_delta = task._to_delta

        task.start = task.performed_start \
                     and to_start(task.performed_start) \
                     or to_start(start)

        task.end = end
        task._unfreeze("length")
        task._unfreeze("duration")
        length = end - start

        for r in resource:
            book_load = calc_load(r)
            work_time = to_delta(length * book_load).round()
            r.book_task(task, start, end, book_load, work_time, False)

        #the following lines are important to be exactly at this
        #positions in that order:
        # done and todo are dependend on:
        #    - the existence of effort (if effort was set or not set)
        #    - book_task (they can only be calculated, if the task is booked)
        #    - booked_resource (to get the booked tasks)
        task.booked_resource = resource
        task.done = task.done
        task.todo = task.todo
        task.length = end - task.start
        task.effort = to_delta(effort + task.performed_effort)
    #@-node:allocate
    #@+node:balance
        #now effort exists always


    def balance(self, task, start, delta, adjust_date,
                calc_load, resource):
        book_load = max(map(lambda r: r.get_load(task.start, task.scenario), resource))
        return start, book_load
    #@-node:balance
    #@-others
#@-node:class StrictAllocator
#@+node:class SmartAllocator


class SmartAllocator(StrictAllocator):
    #@	@+others
    #@+node:balance
    def balance(self, task, start, delta, adjust_date,
                calc_load, resource):
        #find the earliest start date, at which all
        #resources in the team are free

        cal = task.root.calendar
        to_start = task._to_start
        start = adjust_date(start)
        scenario = task.scenario

        while True:
            #we have finished, when all resources have the
            #same next free start date
            for r in resource:
                max_load = _calc_maxload(task, r)
                load = calc_load(r)

                #find the next free time of the resource
                s = r.find_free_time(start, delta, load, max_load, scenario)
                if s != start:
                    s = to_start(s)
                    start = adjust_date(s)
                    break
            else:
                #only one resource
                break

        return start, 1.0
    #@-node:balance
    #@-others
#@-node:class SmartAllocator
#@+node:class SloppyAllocator


class SloppyAllocator(AllocationAlgorithm):
    #@	@+others
    #@+node:test_allocation
    def test_allocation(self, task, resource):
        if task.__dict__.has_key("effort"):
            return self.test_allocation_effort(task, resource)

        return self.test_allocation_length(task, resource)
    #@-node:test_allocation
    #@+node:test_allocation_length
    def test_allocation_length(self, task, resource):
        #length is frozen ==> effort will be calculated
        to_start = task._to_start
        to_end = task._to_end
        to_delta = task._to_delta

        end = task.end
        if task.performed_end:
            start = to_start(max(task.performed_end,
                                 task.root.calendar.now,
                                 start))
        else:
            start = task.start

        base_start = to_start(task.performed_start or task.start)
        length = to_delta(max(task.length - (start - base_start), 0))
        sum_effort = 0
        intervals = []
        scenario = task.scenario
        for r in resource:
            date = start
            max_load = _calc_maxload(task, r)
            book_load = _calc_load(task, r)

            while date < end:
                #find free time intervals and add them for booking
                endi, load = r.end_of_booking_interval(date, task)
                endi = min(endi, end)
                endi = to_end(endi)

                if book_load <= 0:
                    #variable book_load ==> calc the maxmimal possible book_load >= (the given book_load)
                    used_book_load = - book_load
                    diff_load = max_load - load
                    if diff_load and diff_load >= book_load:
                        used_book_load = diff_load
                    else:
                        used_book_load = max_load
                else:
                    used_book_load = book_load

                if max_load - load >= used_book_load:
                    intervals.append((r, used_book_load, date, endi))
                    sum_effort = (endi - date) * used_book_load

                date = to_start(endi)

        return -sum_effort, end, resource, intervals
    #@-node:test_allocation_length
    #@+node:test_allocation_effort
    def test_allocation_effort(self, task, resource):
        #effort is frozen ==> length will be calculated

        to_start = task._to_start
        to_end = task._to_end
        to_delta = task._to_delta

        intervals = []
        effort = task.__dict__.get("effort")

        if task.performed_end:
            next_date = to_start(max(task.performed_end,
                                     task.root.calendar.now,
                                     task.start))
        else:
            next_date = task.start
            if task.root.has_actual_data and task.complete == 0:
                next_date = max(next_date, to_start(task.root.calendar.now))

        #walks chronologicly through the booking
        #intervals of each resource, and reduces
        #the effort for each free interval
        #until it becomes 0

        alloc_effort = effort
        effort -= task.performed_effort
        while effort > 0:
            date = next_date

            interval_resource = []
            interval_end = to_start(sys.maxint)
            factor = 0

            for r in resource:
                max_load = _calc_maxload(task, r)
                book_load = _calc_load(task, r)
                end, load = r.end_of_booking_interval(date, task)
                interval_end = to_start(min(end, interval_end))

                if book_load <= 0:
                    #variable book_load ==> calc the maxmimal possible book_load >= (the given book_load)
                    book_load = - book_load
                    diff_load = max_load - load
                    if diff_load and diff_load >= book_load:
                        book_load = diff_load
                    else:
                        book_load = max_load

                if book_load + load <= max_load:
                    resource_factor = book_load * r.efficiency
                    interval_resource.append((r, book_load, resource_factor))
                    factor += resource_factor



            next_date = interval_end
            if factor:
                factor *= task.efficiency
                length = to_delta(effort / factor).round()
                end = date + length

                if interval_end >= end:
                    next_date = interval_end = end
                    effort = 0
                    book_end = end
                else:
                    book_end = interval_end
                    length = book_end - date
                    minus_effort = length * factor
                    effort -= minus_effort

                book_end = to_end(book_end)
                intervals.append((date, book_end, length, interval_resource))

        return next_date, alloc_effort, resource, intervals
    #@-node:test_allocation_effort
    #@+node:allocate
    def allocate(self, task, state):
        if task.__dict__.has_key("effort"): self.allocate_effort(task, state)
        else: self.allocate_length(task, state)
    #@-node:allocate
    #@+node:allocate_length
    def allocate_length(self, task, state):
        # now really book the resource
        neg_sum_effort, end, resource, intervals = state

        cal = task.root.calendar
        to_start = task._to_start
        to_end = task._to_end
        to_delta = task._to_delta

        task.start = to_start(task.performed_start or task.start)
        task.end = to_end(end)
        task._unfreeze("length")
        task._unfreeze("duration")

        effort = 0
        for r, load, s, e in intervals:
            work_time = to_delta((e - s) * load).round()
            effort += work_time
            r.book_task(task, s, e, load, work_time, False)

        #see comment at StrictAllocator.allocate
        task.booked_resource = resource
        task.done = task.done
        task.todo = task.todo
        task.effort = to_delta(effort + task.performed_effort).round()
    #@-node:allocate_length
    #@+node:allocate_effort
    def allocate_effort(self, task, state):
        # now really book the resource
        end, effort, resource, intervals = state
        to_start = task._to_start
        to_end = task._to_end
        to_delta = task._to_delta

        task.start = task.performed_start \
                     and to_start(task.performed_start) \
                     or to_start(intervals[0][0])
        task.end = to_end(end)
        task._unfreeze("length")
        task._unfreeze("duration")

        for start, end, length, resources in intervals:
            for r, load, factor in resources:
                work_time = to_delta(length * load)
                r.book_task(task, start, end, load, work_time, False)

        task.booked_resource = resource
        task.done = task.done
        task.todo = task.todo
        task.effort = to_delta(effort)
        task.length = task.end - task.start
    #@-node:allocate_effort
    #@-others
#@-node:class SloppyAllocator
#@-others

_smart_allocator = SmartAllocator()
_sloppy_allocator = SloppyAllocator()
_strict_allocator = StrictAllocator()
_allocators = { SMART: _smart_allocator,
                SLOPPY: _sloppy_allocator,
                STRICT: _strict_allocator }

_allocator_strings = { SMART: "SMART",
                       SLOPPY: "SLOPPY",
                       STRICT: "STRICT" }
#@-node:Resource Allocators
#@+node:Load Calculators
#@+node:YearlyMax
def YearlyMax(value):
    """
    Calculates a load parameter with a maximal yearly workload
    """
    #@    << calculate calendar and time_diff >>
    #@+node:<< calculate calendar and time_diff >>
    try:
        cal = me.calendar
    except NameError:
        cal = pcalendar._default_calendar

    time_diff = cal.Minutes(value)
    #@nonl
    #@-node:<< calculate calendar and time_diff >>
    #@nl
    return float(time_diff) / \
            (cal.working_days_per_year \
             * cal.working_hours_per_day \
             * 60)
#@nonl
#@-node:YearlyMax
#@+node:WeeklyMax
def WeeklyMax(value):
    """
    Calculates a load parameter with a maximal weekly workload
    """
    #@    << calculate calendar and time_diff >>
    #@+node:<< calculate calendar and time_diff >>
    try:
        cal = me.calendar
    except NameError:
        cal = pcalendar._default_calendar

    time_diff = cal.Minutes(value)
    #@nonl
    #@-node:<< calculate calendar and time_diff >>
    #@nl
    return float(time_diff) / \
            (cal.working_days_per_week \
             * cal.working_hours_per_day \
             * 60)

#@-node:WeeklyMax
#@+node:MonthlyMax
def MonthlyMax(value):
    """
    Calculates a load parameter with a maximal monthly workload
    """
    #@    << calculate calendar and time_diff >>
    #@+node:<< calculate calendar and time_diff >>
    try:
        cal = me.calendar
    except NameError:
        cal = pcalendar._default_calendar

    time_diff = cal.Minutes(value)
    #@nonl
    #@-node:<< calculate calendar and time_diff >>
    #@nl
    return float(time_diff) / \
            (cal.working_days_per_month \
             * cal.working_hours_per_day \
             * 60)

#@-node:MonthlyMax
#@+node:DailyMax
def DailyMax(value):
    """
    Calculates a load parameter with a maximal daily workload
    """
    #@    << calculate calendar and time_diff >>
    #@+node:<< calculate calendar and time_diff >>
    try:
        cal = me.calendar
    except NameError:
        cal = pcalendar._default_calendar

    time_diff = cal.Minutes(value)
    #@nonl
    #@-node:<< calculate calendar and time_diff >>
    #@nl
    return float(time_diff) / (cal.working_hours_per_day * 60)
#@-node:DailyMax
#@-node:Load Calculators
#@+node:Task
#@+node:class _TaskProperty
class _TaskProperty(object):
    #@	@+others
    #@+node:__init__
    def __init__(self, method):
        self.method = method
    #@-node:__init__
    #@+node:__get__
    def __get__(self, instance, owner):
        if not instance:
            return None

        return instance._wrap_attrib(self.method)
    #@-node:__get__
    #@-others
#@-node:class _TaskProperty
#@+node:class _RoundingTaskProperty
class _RoundingTaskProperty(object):
    #@	@+others
    #@+node:__init__
    def __init__(self, method, name):
        self.method = method
        self.name = name
    #@-node:__init__
    #@+node:__get__
    def __get__(self, instance, owner):
        if not instance:
            return None

        result = instance._wrap_attrib(self.method).round()
        if instance._is_frozen:
            #correct the attrib to the rounded value
            setattr(instance, self.name, result)

        return result
    #@-node:__get__
    #@-others
#@-node:class _RoundingTaskProperty
#@+node:class Task
class Task(object):
    #@    << description >>
    #@+node:<< description >>
    """
    This class represents a single task in the project tree. A task
    can have other child tasks, or is a leaf of the tree. Resources
    will be allocated only to leafes. You will never create task
    objects by your self, they are created indirectly by Projects.

    @var root:
    Returns the root project task.

    @var up:
    Returns the parent task.

    @var title:
    Specifies an alternative more descriptive name for the task.

    @var start:
    The start date of the task. Valid values are expressions and
    strings specifing a datatime

    @var end:
    The end date of the task. Valid values are expressions and
    strings.

    @var effort:
    Specifies the effort needed to complete the task. Valid values
    are expressions and strings. (Todo: What happens, in case of
    specified performance data...)


    @var length:
    Specifies the time the task occupies the resources.  This is
    working time, not calendar time. 7d means 7 working days, not one
    week. Whether a day is considered a working day or not depends on
    the defined working hours and global vacations.

    @var duration:
    Specifies the time the task occupies the resources. This is
    calendar time, not working time. 7d means one week.

    @var buffer:
    Specifies the time a task can be delayed, without moving dependend
    milestones. A Task with a buffer S{<=} 0d is part of the critical
    chain.  This attribute is readonly.

    @var complete:
    Specifies what percentage of the task is already completed.

    @var todo:
    Specifies the effort, which needs to be done to complete a
    task. This is another (indirect) way to specify the ME{complete}
    attribute.

    @var done:
    Specifies the work effort, which has been already done. This
    attribute is readonly.

    @var estimated_effort:
    Specifies the estimated_effort given by setting the effort property.

    @var performed:
    Specifies a list of actual working times performed on the task.
    The format is: C{[ (resource, from, to, time), ... ]}

    @var performed_work_time:
    Specifies the sum of all working times. This attribute is
    readonly.

    @var performed_effort:
    Specifies the complete effort of all working times. This attribute is
    readonly.

    @var performed_start:
    The start date of the performed data.

    @var performed_end:
    The end date of the performed data.

    @var performed_resource:
    The resources who have already performed on the task. This attribute is readonly.


    @var balance:
    Specifies the resource allocation type. Possible values are
    CO{STRICT}, CO{SLOPPY}, CO{SMART}.

    @var resource:
    Specifies the possible resources, that may be allocated for the
    task.

    @var booked_resource:
    Specifies the allocated resources of a task. This attribute is
    readonly.

    @var load:
    Specifies the daily load of a resource for an allocation of the
    specified task. A load of 1.0 (default) means the resource is
    allocated for as many hours as specified by
    ME{working_hours_per_day}. A load of 0.5 means half that many
    hours.

    @var max_load:
    Specify the maximal allowed load sum of all simultaneously
    allocated tasks of a resource. A ME{max_load} of 1.0 (default)
    means the resource may be fully allocated. A ME{max_load} of 1.3
    means the resource may be allocated with 30% overtime.

    @var efficiency:
    The efficiency of a resource can be used for two purposes. First
    you can use it as a crude way to model a team. A team of 5 people
    should have an efficiency of 5.0. Keep in mind that you cannot
    track the member of the team individually if you use this
    feature. The other use is to model performance variations between
    your resources.

    @var milestone:
    Specified if the task is a milestone. The possible values are
    C{True} or "later". If the start date of the milestone is not
    a valid working date, the milestone will appear at the previous
    working date before the given start date. If "later" is specified
    the milestone will appear at the next valid working date.
    A milestone has always an effort of 0d.

    @var priority:
    Specifies a priority between 1 and 1000. A task with higher
    priority is more likely to get the requested resources.  The
    default priority is 500.

    @var children:
    Specifies a list of all subtasks. A task without children is
    called a leaf task index{leaf task} otherwise it is called a
    parent task index{parent task}. This attribute is readonly.

    @var depth:
    Specifies the depth of the task within the hierachy. This
    attribute is readonly.

    @var index:
    Specifies a structural index number. This attribute is readonly.

    @var path:
    Specifies the path.

    @var copy_src:
    Specifies the path to an other task.  When you set this attribute,
    all attributes (except of ME{start} and ME{end}) of copy_src will
    be copied to the current task. This is usefull if you want to
    define the same task, in diffent project definitions. It acts like
    a task link.

    @var scenario:
    The scenario which is currently evaluated. This attribute is readonly.

    @var dont_inherit:
    A list of attribute names, which will be not inherited by
    subtasks.

    @var calendar:
    Specifies the task calendar.

    @var working_days_per_week:
    Specifies the days within a working week. This value is used
    internally to convert time differences from weeks to days. The
    default value is 5 days.

    @var working_days_per_month:
    Specifies the days within a working month. This value is used
    internally to convert time differences from months to days. The
    default value is 20 days.

    @var working_days_per_year:
    Specifies the days within a working year. This value is used
    internally to convert time differences from years to days The
    default value is 200 days.

    @var working_hours_per_day:
    Specifies the hours within a working day. This value is used
    internally to convert time differences from are entered in days to
    hours.  The default value is 8 hours.

    @var minimum_time_unit:
    Specifies the minimum resolution in minutes for the task
    scheduling. The default value is 15 minutes.

    @var vacation:
    Specifies a public vacation for the calendar. This attribute is
    specified as a list of date literals or date literal intervals. Be
    aware that the end of an interval is excluded, i.e. it is the
    first working date.

    @var extra_work:
    Specifies additional worktime. This attribute is specified as a
    list of date literals or date literal intervals. Be aware that the
    end of an interval is excluded, i.e. it is the first working date.

    @var working_days:
    Specifies the weekly working time within calendar. The format of
    this attribute is: [ (day_range, time_range, ...), (day_range, time_range, ...), ... ].
    day_range is a comma sperated string of week days. Valid values
    are mon, tue, wed, thu, fri, sat, sun.
    time_range is string specifing a time interval like
    8:00-10:00. You can specified any number of time_ranges, following
    the first.

    @var now:
    Specifies the current daytime and is a date literal. ME{now} is
    used to calculate several task attributes.

    """
    #@nonl
    #@-node:<< description >>
    #@nl
    #@	<< declarations >>
    #@+node:<< declarations >>
    # Variables for the gui interface
    _date_completion = { "Date": 'Date("|")',
                         "max": "max(|)",
                         "min": "min(|)",
                         "Multi" : "Multi(|)" }


    _delta_completion = { "Delta" : 'Delta("|")',
                          "Multi" : "Multi(|)" }


    __attrib_completions__ = { \
        "def NewTask():" : "def |NewTask():\n",
        "milestone": 'milestone = True',
        "start": 'start = ',
        "end": 'end = ',
        "effort": 'effort = "|"',
        "duration": 'duration = "|"',
        "length": 'length = "|"',
        "todo": 'todo = "|"',
        "done": 'done = "|"',
        "title": 'title = "|"',
        "load": 'load = ',
        "max_load": 'max_load = ',
        "efficiency": 'efficiency = ',
        "complete": 'complete = ',
        "copy_src": 'copy_src =',
        "__constraint__": '__constraint__():\n|"',
        "priority": 'priority = ',
        "balance" : 'balance = ',
        "resource": 'resource = ',
        "performed"  : 'performed = [(|resource, "2002-02-01", "2002-02-05", "2H"),]',
        "add_attrib": "add_attrib(|'name', None)",
        "working_days_per_week": 'working_days_per_week = ',
        "working_days_per_month": 'working_days_per_month = ',
        "working_days_per_year": 'working_days_per_year = ',
        "working_hours_per_day": 'working_hours_per_day = ',
        "minimum_time_unit": 'minimum_time_unit = ',
        "vacation": 'vacation = [("|2002-02-01", "2002-02-05")]',
        "extra_work": 'extra_work = [("|2002-02-01", "2002-02-05")]',
        "working_days" : 'working_days = ["|mon,tue,wed,thu,fri", "8:00-12:00", "13:00-17:00"]',
        "now": 'now = "|"',
        "calendar" : 'calendar = ',
        "#load": { "YearlyMax": 'YearlyMax("|")',
                   "WeeklyMax": 'WeeklyMax("|")',
                   "MonthlyMax": 'MonthlyMax("|")',
                   "DailyMax": 'DailyMax("|")',
                   "VariableLoad" : "VariableLoad(|)"},
        "#max_load": { "YearlyMax": 'YearlyMax("|")',
                       "WeeklyMax": 'WeeklyMax("|")',
                       "MonthlyMax": 'MonthlyMax("|")',
                       "DailyMax": 'DailyMax("|")' },
        "#start": _date_completion,
        "#end": _date_completion,
        "#effort": _delta_completion,
        "#duration": _delta_completion,
        "#length": _delta_completion,
        "#todo": _delta_completion,
        "#done": _delta_completion,
        "#resource" : "get_resource_completions",
        "#calendar" : "get_calendar_completions",
        "#balance": { "STRICT": "STRICT",
                      "SMART": "SMART",
                      "SLOPPY": "SLOPPY" } }


    formats = { "start" : "%x %H:%M",
                "end"  : "%x %H:%M",
                "performed_start" : "%x %H:%M",
                "performed_end" : "%x %H:%M",
                "load" : "%.2f",
                "length" : "%dd{ %HH}{ %MM}",
                "effort" : "%dd{ %HH}{ %MM}",
                "estimated_effort" : "%dd{ %HH}{ %MM}",
                "performed_effort" : "%dd{ %HH}{ %MM}",
                "duration" : "%dd{ %HH}{ %MM}",
                "complete" : "%i",
                "priority" : "%i",
                "todo" : "%dd{ %HH}{ %MM}",
                "done" : "%dd{ %HH}{ %MM}",
                "efficiency" : "%.2f",
                "buffer" : "%dd{ %HH}{ %MM}",
                "costs" : "%.2f",
                "sum" : "%.2f",
                "max" : "%.2f",
                "min" : "%.2f",
                "milestone" : "%s",
                "resource" : "%s",
                "booked_resource" : "%s",
                "performed_resource" : "%s" }

    _constraint = None
    _is_frozen = False
    _is_compiled = False
    _is_parent_referer = False

    scenario = None # only for autocompletion
    milestone = False
    performed = ()
    performed_resource = ()
    booked_resource = ()
    _performed_resource_length = ()
    _resource_length = ()
    dont_inherit = ()
    performed_start = None
    performed_end = None
    performed_work_time = pcalendar.Minutes(0)

    _setting_hooks = {}
    #@nonl
    #@-node:<< declarations >>
    #@nl
    #@	@+others
    #@+node:__init__
    def __init__(self, func, name, parent=None, index=1):

        assert(type(func) == types.FunctionType)

        func_key = (func.func_code, func.func_closure and id(func.func_closure))

        try:
            instrumented = instrumentation_cache[func_key]
        except KeyError:
            instrumented = _instrument(func)
            instrumented.org_code = func_key
            instrumentation_cache[func_key] = instrumented

        func.task_func = instrumented # will be used in the gui
        self._function = instrumented
        self.name = name
        self.up = parent
        self.children = []
        self._sources = {} # all tasks, I am linked to
        self._dependencies = {} # all tasks that link to me
        self._original_values = {}
        self._properties = {} # a registry of all non standard attributes
        self.title = self.name
        self.root = parent and parent.root or self
        self.scenario = self.root.scenario
        self.path = parent and parent.path + "." + name or name
        self.depth = len(self.path.split(".")) - 1
        self.index = parent and ("%s.%i" % (parent.index, index)) \
                     or str(index)
        if self.formats.has_key(name):
            raise AttributeError("Task name '%s' hides attribute of parent." \
                                 % name)

        cal = self.calendar
        self._to_delta = cal.Minutes
        self._to_start = cal.StartDate
        self._to_end = cal.EndDate

    #@-node:__init__
    #@+node:__iter__
    def __iter__(self):
        return _step_tasks(self)
    #@-node:__iter__
    #@+node:__repr__
    def __repr__(self):
        return "<Task %s>" % self.name
    #@-node:__repr__
    #@+node:__cmp__
    def __cmp__(self, other):
        try:
            return cmp(self.path, other.path)
        except Exception:
            return cmp(self.path, other)
    #@-node:__cmp__
    #@+node:__getattr__
    def __getattr__(self, name):
        try:
            if name[0] != "_":
                parent = self.up
                while parent:
                    if name not in parent.dont_inherit:
                        result = getattr(parent, name)
                        if not (isinstance(result, Task) and result.up == parent):
                            return result

                    parent = parent.up
        except AttributeError:
            pass
        except IndexError:
            raise AttributeError()

        exception = AttributeError("'%s' is not a valid attribute of '%s'."
                                   % (name, self.path))
        exception.is_frozen = self._is_frozen
        raise exception
    #@-node:__getattr__
    #@+node:_idendity_
    def _idendity_(self): return self.root.id + self.path[4:]
    #@-node:_idendity_
    #@+node:_set_hook
    def _set_hook(cls, attrib_name, function=None):
        if function:
            cls._setting_hooks[attrib_name] = function
        else:
            try:
                del cls._setting_hooks[attrib_name]
            except KeyError: pass


    _set_hook = classmethod(_set_hook)
    #@nonl
    #@-node:_set_hook
    #@+node:Public methods
    #@+node:to_string
    def to_string(self): return _StringConverter(self)
    to_string = property(to_string)
    #@nonl
    #@-node:to_string
    #@+node:indent_name
    def indent_name(self, ident="    "):
        """
        returns a indented name, according to its depth in the hierachy.
        """

        return ident * self.depth + self.name

    indent_name.attrib_method = True
    indent_name.__call_completion__ = "indent_name()"
    #@-node:indent_name
    #@+node:costs
    def costs(self, cost_name, mode="ep"):
        """
        calculates the resource costs for the task.
        cost_name is the name of a rate attribute of the reosurce
        mode is character combination:
                  e calculates the estimated costs
                  p calculates the performed costs
                  ==> pe calculates all costs
        """

        if self.children:
            return sum([ c.costs(cost_name, mode) for c in self.children])

        costs = 0
        if 'e' in mode:
            costs += sum(map(lambda rl: getattr(rl[0], cost_name) * rl[1],
                             self._resource_length))

        if 'p' in mode:
            costs += sum(map(lambda rl: getattr(rl[0], cost_name) * rl[1],
                             self._performed_resource_length))

        costs /= (60.0 * self.root.calendar.working_hours_per_day)
        return round(costs, 2)

    costs.attrib_method = True
    costs.__call_completion__ = 'costs("|")'
    #@-node:costs
    #@+node:sum
    def sum(self, attrib_name):
        val = 0

        if self.children:
            val += sum(map(lambda c: c.sum(attrib_name), self.children))
            if self.is_inherited(attrib_name):
                return val

            if attrib_name not in self.dont_inherit:
                return val

        return val + getattr(self, attrib_name)

    sum.attrib_method = True
    sum.__call_completion__ = 'sum("|")'

    #@-node:sum
    #@+node:min
    def min(self, attrib_name):
        if self.children:
            return min(map(lambda c: c.min(attrib_name), self.children))

        return getattr(self, attrib_name)

    min.attrib_method = True
    min.__call_completion__ = 'min("|")'

    #@-node:min
    #@+node:max
    def max(self, attrib_name):
        if self.children:
            return max(map(lambda c: c.max(attrib_name), self.children))

        return getattr(self, attrib_name)

    max.attrib_method = True
    max.__call_completion__ = 'max("|")'

    #@-node:max
    #@+node:all_resources
    def all_resources(self):
        result = self._all_resources_as_dict()
        result = result.keys()
        result.sort()
        return result
    #@-node:all_resources
    #@+node:get_task
    def get_task(self, path=None):
        """
        Returns a task with the given path.
        """

        if not path:
            return self

        names = path.split(".")
        rest = ".".join(names[1:])
        result = getattr(self, names[0], None)
        return isinstance(result, Task) and result.get_task(rest) or None
    #@-node:get_task
    #@+node:snapshot
    def snapshot(self, indent="", name=None):
        text = indent + "def %s():\n" % (name or self.name)
        indent += "    "
        for name in ("priority", "balance", "complete",
                     "milestone", "end", "start", "effort", "load"):
            val = getattr(self, name, None)
            if val is None:
                continue

            if name[0] == "_":
                name = name[1:]

            text += "%s%s = %s\n" % (indent, name, _as_string(val))

        for name in self._properties:
            if name.startswith("performed"): continue
            val = getattr(self, name, None)
            try:
                if issubclass(val, resource.Resource): continue
            except TypeError:
                pass
            text += "%s%s = %s\n" % (indent, name, _as_string(val))

        resources = tuple(self._iter_booked_resources())
        if resources:
            text += "%sresource = \\\n" % indent
            def make_resource(res):
                return "%s    %s" \
                       % (indent, res.snapshot())

            text += "&\\\n".join(map(make_resource, resources)) + "\n"

            def make_resource_booking(res):
                def make_booking(booking):
                    return '%s    (%s, "%s", "%s", "%sM"),' \
                           % (indent, res.name,
                              booking.book_start.strftime("%Y%m%d %H:%M"),
                              booking.book_end.strftime("%Y%m%d %H:%M"),
                              booking.work_time)

                return "\n".join(map(make_booking, res.get_bookings(self)))


            text += "%sperformed = [\n" % indent
            text += "\n".join(map(make_resource_booking, resources)) + "]"


        child_text = map(lambda c: c.snapshot(indent), self.children)
        text += "\n\n"
        text += "".join(child_text)

        return text
    #@-node:snapshot
    #@+node:is_inherited
    def is_inherited(self, attrib_name):
        return not self.__dict__.has_key(attrib_name)
    #@-node:is_inherited
    #@+node:formatter
    def formatter(self, attrib_name, arg=None, format=None):
        """returns a function which is able
        to convert the value of the given attrib_name to a string"""

        formats = self.formats
        format = format or formats.get(attrib_name)

        if attrib_name in ("start", "end", "length", "effort",
                           "done", "todo", "buffer", "estimated_effort",
                           "performed_effort", "performed_start", "performed_end"):
            def save_strftime(v):
                try:
                    return v.strftime(format)
                #except AttributeError: some bug avoid catching this exception
                except Exception:
                    return str(v)

            return save_strftime

        if attrib_name == "duration":
            def save_strftime(v):
                try:
                    return v.strftime(format, True)
                except AttributeError:
                    return str(v)

            return save_strftime

        if attrib_name in ("booked_resource", "performed_resource"):
            def get_resource_name(v):
                title = getattr(v, "title", None)
                if title: return title
                return ", ".join([r.title for r in v])
            return get_resource_name

        if arg and attrib_name in ("costs", "sum", "max", "min"):
            format = formats.get("%s(%s)" % (attrib_name, arg), format)

        if format:
            return lambda v: locale.format(format, v, True)

        return str
    #@-node:formatter
    #@-node:Public methods
    #@+node:Resource allocation Methods
    #@+node:_all_resources_as_dict
    def _all_resources_as_dict(self):
        if self.children:
            result = {}
            for c in self.children:
                result.update(c._all_resources_as_dict())

            return result

        if self.resource:
            return dict(map(lambda r: (r, 1), self.resource.all_members()))

        return {}
    #@-node:_all_resources_as_dict
    #@+node:_test_allocation
    def _test_allocation(self, resource_state, allocator):
        resource = self.resource._get_resources(resource_state)
        if not resource:
            return False

        return allocator.test_allocation(self, resource)
    #@-node:_test_allocation
    #@+node:_allocate
    def _allocate(self, state, allocator):
        allocator.allocate(self, state)
        #activate cache for done and todo

        if self.start.to_datetime() > self.end.to_datetime():
            #this can happen when performed effort are
            #during non working time
            tmp = self.start
            self.start = self.end
            self.end = tmp

        for r in self.performed_resource:
            r.correct_bookings(self)

        self._resource_length = map(lambda r: (weakref.proxy(r), \
                                               r.length_of(self)),
                                    self._iter_booked_resources())
    #@-node:_allocate
    #@+node:_convert_performed
    def _convert_performed(self, all_resources):
        performed = self.performed
        if not performed: return False

        if not isinstance(performed, (tuple, list)) \
           or not isinstance(performed[0], (tuple, list)) \
           or not len(performed[0]) >= 3:
            self._raise(TypeError("""The format of the performed attribute must be:
    [( res_name, start_literal, end_literal, working_time ),  ... ].
    """), "performed")

        round_down_delta = self.root.calendar.minimum_time_unit / 2
        round_down_delta = datetime.timedelta(minutes=round_down_delta)

        def convert_item(index):
            item = performed[index]
            res, start, end = item[:3]
            if isinstance(res, str):
                found = filter(lambda r: r.name == res, all_resources)
                if found: res = found[0]

            try:
                if not isinstance(res, (resource.Resource,
                                        resource._MetaResource)):
                    raise ValueError("the resource '%s' is unknown." %  res)

                start = _to_datetime(start)
                end = _to_datetime(end)

                if len(item) > 3:
                    working_time = self._to_delta(item[3]).round()
                else:
                    working_time = self._to_delta(end - start, True)

                return ((res, start, end, working_time), index)
            except Exception, exc:
                self._raise(exc.__class__("Item %i: %s" \
                                          % (index + 1, str(exc))),
                            "performed")

        converted = dict(map(convert_item, range(len(performed))))
        converted = converted.items()
        converted.sort()

        #check for overlapping items
        last_res = None
        for item, index in converted:
            res, start, end, work_time = item
            if last_res == res and start < last_end:
                self._warn("Items %i, %i:  %s and %s are overlapping." \
                           % (last_index + 1, index + 1,
                              str(performed[last_index]),
                              str(performed[index])),
                           "performed")

            last_res = res
            last_end = end
            last_index = index

        self._performed = map(lambda x: x[0], converted)
        return True
    #@-node:_convert_performed
    #@+node:_allocate_performed
    def _allocate_performed(self, performed):
        if not performed: return

        to_delta = self._to_delta
        to_start = self._to_start
        to_end = self._to_end

        last = datetime.datetime.min
        first = datetime.datetime.max
        effort = 0
        work_time_sum = 0
        zero_minutes = to_delta(0)
        minimum_time_unit = to_delta(self.calendar.minimum_time_unit)
        summary = {}

        for item in performed:
            res, start, end, work_time = item
            effort += work_time * self.efficiency * res.efficiency
            work_time_sum += work_time

            res = res()
            ss, es, wts = summary.get(res, (datetime.datetime.max,
                                            datetime.datetime.min,
                                            zero_minutes))
            summary[res] = (min(ss, start), max(es, end), wts + work_time)

        for r, v in summary.iteritems():
            start, end, work_time = v
            assert(start.__class__ is datetime.datetime)
            assert(end.__class__ is datetime.datetime)

            #the booking limits should be inside the workingtime
            #to display them correct in resource charts
            cstart = to_start(start).to_datetime()
            if cstart > start: cstart = to_end(start).to_datetime()

            cend = to_end(end).to_datetime()
            if cend < end: cend = to_start(end).to_datetime()

            if self.root.is_snapshot:
                delta = to_end(cend) - to_start(cstart)
            else:
                delta = to_delta(cend - cstart).round()

            if not delta:
                delta = minimum_time_unit

            book_load = float(work_time) / delta
            r().book_task(self, cstart, cend, book_load, work_time, True)
            last = max(end, last)
            first = min(start, first)

        self._performed_resource_length = tuple([ (r, v[2]) for r, v in summary.iteritems() ])
        self.performed_resource = tuple(summary.keys())
        self.performed_end = last
        self.performed_start = first
        self.performed_effort = to_delta(effort)
        self.performed_work_time = to_delta(work_time_sum)
        self._check_completion()
    #@-node:_allocate_performed
    #@+node:_iter_booked_resources
    def _iter_booked_resources(self):
        result = dict(map(lambda r: (r, 1), self.performed_resource))
        result.update(dict(map(lambda r: (r, 1), self.booked_resource)))
        return result.iterkeys()
    #@-node:_iter_booked_resources
    #@-node:Resource allocation Methods
    #@+node:Compile Methods
    #@+node:_generate
    def _generate(self, deferred=None):
        do_raise = False
        deferred = deferred or [ self ]
        while deferred:
            new_deferred = []
            for task in deferred:
                task._compile(new_deferred, do_raise)

            do_raise = deferred == new_deferred
            deferred = new_deferred
    #@-node:_generate
    #@+node:_recalc_properties
    def _recalc_properties(self):
        if not self._properties: return
        self.__compile_function([], False, _MeProxyRecalc(self))
        self._is_compiled = True
    #@-node:_recalc_properties
    #@+node:_compile
    def _compile(self, deferred, do_raise):
        self.dont_inherit = ()
        self._constraint = None
        self._original_values.clear()
        self._properties.clear()

        try:
            self.__at_compile
            #@        << raise child recursion error >>
            #@+node:<< raise child recursion error >>
            self._raise(RecursionError("A child defines a "\
                                       "recursive definition at %s" % self.path))
            #@-node:<< raise child recursion error >>
            #@nl
        except AttributeError:
            self.__at_compile = self, ""

        try:
            self.__compile_function(deferred, do_raise, _MeProxy(self))
        finally:
            del self.__at_compile

        for c in self.children:
            if not c._is_compiled:
                c._compile(deferred, do_raise)

        if self._is_compiled:
            self.__check_milestone()
            self.__check_task()
            self.root.has_actual_data |= self.__dict__.has_key("performed")

    #@-node:_compile
    #@+node:__compile_function
    def __compile_function(self, deferred, do_raise, me_instance):
        self._is_compiled = self._is_frozen

        restore_globals = []
        globals_ = self._function.func_globals

        #@    << set function global values >>
        #@+node:<< set function global values >>
        def to_value_wrapper(a):
            if isinstance(a, _ValueWrapper):
                return a

            return _ValueWrapper(a, [(None, None)])

        def my_max(*args):
            return max(map(to_value_wrapper, args))

        def my_min(*args):
            return min(map(to_value_wrapper, args))

        globals_["me"] = me_instance

        if self._is_compiled:
            globals_["up"] = self.up
            globals_["root"] = self.root
        else:
            globals_["up"] = _Path(self.up, "up")
            globals_["root"] = _Path(self.root, "root")

        globals_["Delta"] = self._to_delta
        globals_["Date"] = self._to_start
        globals_["max"] = my_max
        globals_["min"] = my_min
        globals_["add_attrib"] = me_instance.add_attrib
        #@nonl
        #@-node:<< set function global values >>
        #@nl
        #@    << set me in global functions >>
        #@+node:<< set me in global functions >>
        #@+at
        # Is used for functions like YearlyMax, MonthlyMax, ....
        #@-at
        #@@code
        for name in self._function.global_names:
            try:
                obj = globals_[name]
                if isinstance(obj, types.FunctionType):
                    fg = obj.func_globals
                    if not fg.has_key("me") and "me" in obj.func_code.co_names:
                        restore_globals.append(fg)
                        fg["me"] = me_instance
            except KeyError: continue
        #@nonl
        #@-node:<< set me in global functions >>
        #@nl
        try:
            #@        << eval function >>
            #@+node:<< eval function >>
            if do_raise:
                try:
                    self._function()
                    self._is_compiled = True
                except _IncompleteError, e:
                    src = e.args[1]
                    if src is not self:
                        self.__at_compile = e.args[1:]
                        src._compile([], True)

                    raise
            else:
                try:
                    self._function()
                    self._is_compiled = True
                except AttributeError, e:
                    #print "AttributeError:", e, self.name, e.is_frozen, do_raise
                    deferred.append(self)
                except _IncompleteError:
                    #print "_IncompleteError:", id(self), self.name, do_raise
                    deferred.append(self)
                except RecursionError:
                    self._is_parent_referer = True
                    deferred.append(self)
            #@nonl
            #@-node:<< eval function >>
            #@nl
        finally:
            for fg in restore_globals:
                del fg["me"]

    #@-node:__compile_function
    #@-node:Compile Methods
    #@+node:Setting methods
    #@+node:_set_attrib
    def _set_attrib(self, name, value):
        if value is _NEVER_USED_: return

        try:
            value = self._setting_hooks[name](self, name, value)
        except KeyError: pass

        if name == "__constraint__":
            self._constraint = value
            return

        if type(value) == types.FunctionType:
            if value.func_code.co_argcount == 0:
                #@            << add child task >>
                #@+node:<< add child task >>
                try:
                    task = self.__dict__[value.func_name]
                except KeyError:
                    task = Task(value, value.func_name, self, len(self.children) + 1)
                    self.children.append(task)
                    setattr(self, value.func_name, task)
                return
                #@nonl
                #@-node:<< add child task >>
                #@nl

        if name[0] == "_":
            #private vars will not be set
            return

        if isinstance(value, _Path):
            value = value._task

        set_method = getattr(self, "_set_" + name, None)
        if set_method:
            #@        << set standard attribute >>
            #@+node:<< set standard attribute >>
            if type(value) == types.DictionaryType:
                self.root.all_scenarios.update(value.keys())
                value = value.get(self.scenario, value["_default"])

            self.__set_sources(name, value)
            self._original_values[name] = value
            set_method(_val(value))
            #@nonl
            #@-node:<< set standard attribute >>
            #@nl
        else:
            #@        << set userdefined attribute >>
            #@+node:<< set userdefined attribute >>
            if callable( getattr(self.__class__, name, None)):
                raise NameError('You may not use "%s" as attribute' % name)

            setattr(self, name, value)
            self._properties[name] = True
            self.__set_sources(name, value)
            #@nonl
            #@-node:<< set userdefined attribute >>
            #@nl
    #@-node:_set_attrib
    #@+node:read only attributes
    #@+node:_set_name
    def _set_name(self, value):
        raise AttributeError("The attribute 'name' is readonly.")
    #@nonl
    #@-node:_set_name
    #@+node:_set_done
    def _set_done(self, value):
        raise AttributeError("The attribute 'done' is readonly.")
    #@nonl
    #@-node:_set_done
    #@+node:_set_performed_work_time
    def _set_performed_work_time(self, value):
        raise AttributeError("The attribute 'performed_work_time' is readonly.")
    #@nonl
    #@-node:_set_performed_work_time
    #@+node:_set_booked_resource
    def _set_booked_resource(self, value):
        raise AttributeError("The attribute 'booked_resource' is readonly.")
    #@nonl
    #@-node:_set_booked_resource
    #@+node:_set_performed_effort
    def _set_performed_effort(self, value):
        raise AttributeError("The attribute 'performed_effort' is readonly.")
    #@nonl
    #@-node:_set_performed_effort
    #@+node:_set_children
    def _set_children(self, value):
        raise AttributeError("The attribute 'children' is readonly.")
    #@nonl
    #@-node:_set_children
    #@+node:_set_depth
    def _set_depth(self, value):
        raise AttributeError("The attribute 'depth' is readonly.")
    #@nonl
    #@-node:_set_depth
    #@+node:_set_index
    def _set_index(self, value):
        raise AttributeError("The attribute 'index' is readonly.")
    #@nonl
    #@-node:_set_index
    #@+node:_set_scenario
    def _set_scenario(self, value):
        raise AttributeError("The attribute 'scenario' is readonly.")
    #@nonl
    #@-node:_set_scenario
    #@+node:_set_buffer
    def _set_buffer(self, value):
        raise AttributeError("The attribute 'buffer' is readonly.")
    #@nonl
    #@-node:_set_buffer
    #@-node:read only attributes
    #@+node:_set_start
    def _set_start(self, value):
        self.__start_class = value.__class__
        self.start = self._to_start(value).round()
    #@-node:_set_start
    #@+node:_set_end
    def _set_end(self, value):
        self.end = self._to_end(value)
    #@-node:_set_end
    #@+node:_set_max_load
    def _set_max_load(self, max_load):
        self.max_load = float(max_load)
    #@-node:_set_max_load
    #@+node:_set_load
    def _set_load(self, load):
        self.load = float(load)
    #@-node:_set_load
    #@+node:_set_length
    def _set_length(self, value):
        self.length = self._to_delta(value).round()
    #@-node:_set_length
    #@+node:_set_effort
    def _set_effort(self, value):
        self.effort = self._to_delta(value).round()
    #@-node:_set_effort
    #@+node:_set_duration
    def _set_duration(self, value):
        self.duration = self._to_delta(value, True).round()
    #@-node:_set_duration
    #@+node:_set_complete
    def _set_complete(self, value):
        self.complete = value
    #@-node:_set_complete
    #@+node:_set_done
    def _set_done(self, value):
        self.done = self._to_delta(value).round()
    #@-node:_set_done
    #@+node:_set_todo
    def _set_todo(self, value):
        self.todo = self._to_delta(value).round()
    #@-node:_set_todo
    #@+node:_set_milestone
    def _set_milestone(self, value):
        self.milestone = value
    #@-node:_set_milestone
    #@+node:_set_resource
    def _set_resource(self, value):
        if not value:
            self.resource = None
            return

        if isinstance(value, (tuple, list)):
            value = reduce(lambda a, b: a & b, value)

        self.resource = value()

    #@-node:_set_resource
    #@+node:_set_copy_src
    def _set_copy_src(self, value):
        if isinstance(value, _MeProxy):
            raise RuntimeError("Cannot copy me.")

        if not value._is_compiled:
            raise _IncompleteError(value, "copy_src")

        if value.resource and not self.resource:
            self.resource = value.resource

        if value.balance and not self.balance:
            self.balance = value.balance

        copy_parms = ("priority", "todo", "complete",
                      "_constraint", "load", "length",
                      "effort", "duration")

        for p in copy_parms:
            v = value.__dict__.get(p)
            if v: setattr(self, p, v)

        self.copy_src = value
        self._properties.update(value._properties)
        for k in value._properties.iterkeys():
            setattr(self, k, getattr(value, k))
    #@-node:_set_copy_src
    #@+node:__set_sources
    def __set_sources(self, attrib_name, value):
        #@    << find references >>
        #@+node:<< find references >>
        def make_ref(val):
            if isinstance(val, _ValueWrapper):
                return val._ref

            if isinstance(val, Task):
                return [(val, "")]

            return []

        if isinstance(value, (list, tuple)):
            sources = _refsum(map(make_ref, value))
        else:
            sources = make_ref(value)
        #@nonl
        #@-node:<< find references >>
        #@nl
        if not sources: return

        #track only dependcies within the same project
        root = self.root
        sources = [ task.path + "." + attrib
                    for task, attrib in sources
                    if task and task.root is root ]
        self._sources[attrib_name] = tuple(sources)
        attr_path = self.path + "." + attrib_name

        #set dependencies of my sources
        for d in sources:
            path, attrib = _split_path(d)
            task = self.get_task(path)
            r_d = task._dependencies
            d_l = r_d.setdefault(attrib, {})
            d_l[attr_path] = True
    #@-node:__set_sources
    #@+node:Calendar Setters
    #@+node:_set_calendar
    def _set_calendar(self, value):
        self.calendar = value
        self._to_delta = value.Minutes
        self._to_start = value.StartDate
        self._to_end = value.EndDate
        self.__renew_dates()

    #@-node:_set_calendar
    #@+node:__renew_dates
    def __renew_dates(self):
        for attrib in ("effort", "start", "end", "length", "todo"):
            try:

                self._set_attrib(attrib, self._original_values[attrib])
            except KeyError:
                pass

    #@-node:__renew_dates
    #@+node:__make_calendar
    def __make_calendar(self):
        if not "calendar" in self.__dict__:
            cal = self.calendar = self.calendar.clone()
            self._to_delta = cal.Minutes
            self._to_start = cal.StartDate
            self._to_end = cal.EndDate
    #@nonl
    #@-node:__make_calendar
    #@+node:_set_vacation
    def _set_vacation(self, value):
        self.__make_calendar()
        self.calendar.set_vacation(value)
        self._properties["vacation"] = True
        self.vacation = value
        self.__renew_dates()
    #@-node:_set_vacation
    #@+node:_set_extra_work
    def _set_extra_work(self, value):
        self.__make_calendar()
        self.calendar.set_extra_work(value)
        self._properties["extra_work"] = True
        self.extra_work = value
        self.__renew_dates()
    #@-node:_set_extra_work
    #@+node:_set_working_days
    def _set_working_days(self, value):

        if type(value[0]) is str:
            value = (value, )

        self.working_days = value
        self._properties["working_days"] = True
        self.__make_calendar()

        for v in value:
            day_range = v[0]
            tranges = tuple(v[1:])
            self.calendar.set_working_days(day_range, *tranges)

        self.__renew_dates()
    #@nonl
    #@-node:_set_working_days
    #@+node:_set_minimum_time_unit
    def _set_minimum_time_unit(self, value):
        self.__make_calendar()
        self.calendar.minimum_time_unit = value
        self._properties["minimum_time_unit"] = True
    #@-node:_set_minimum_time_unit
    #@+node:_get_minimum_time_unit
    def _get_minimum_time_unit(self):
        return self.calendar.minimum_time_unit

    minimum_time_unit = property(_get_minimum_time_unit)
    #@-node:_get_minimum_time_unit
    #@+node:_set_working_days_per_week
    def _set_working_days_per_week(self, value):

        self.__make_calendar()
        self.calendar.working_days_per_week = value
        self._properties["working_days_per_week"] = True
    #@-node:_set_working_days_per_week
    #@+node:_get_working_days_per_week
    def _get_working_days_per_week(self):
        return self.calendar.working_days_per_week

    working_days_per_week = property(_get_working_days_per_week)
    #@-node:_get_working_days_per_week
    #@+node:_set_working_days_per_month
    def _set_working_days_per_month(self, value):
        self.__make_calendar()
        self.calendar.working_days_per_month = value
        self._properties["working_days_per_month"] = True
    #@-node:_set_working_days_per_month
    #@+node:_get_working_days_per_month
    def _get_working_days_per_month(self):
        return self.calendar.working_days_per_month

    working_days_per_month = property(_get_working_days_per_month)
    #@-node:_get_working_days_per_month
    #@+node:_set_working_days_per_year
    def _set_working_days_per_year(self, value):
        self.__make_calendar()
        self.calendar.working_days_per_year = value
        self._properties["working_days_per_year"] = True
    #@-node:_set_working_days_per_year
    #@+node:_get_working_days_per_year
    def _get_working_days_per_year(self):
        return self.calendar.working_days_per_year

    working_days_per_year = property(_get_working_days_per_year)
    #@-node:_get_working_days_per_year
    #@+node:_set_working_hours_per_day
    def _set_working_hours_per_day(self, value):
        self.__make_calendar()
        self.calendar.working_hours_per_day = value
        self._properties["set_working_hours_per_day"] = True
    #@-node:_set_working_hours_per_day
    #@+node:_get_working_hours_per_day
    def _get_working_hours_per_day(self):
        return self.calendar.working_hours_per_day

    working_hours_per_day = property(_get_working_hours_per_day)
    #@-node:_get_working_hours_per_day
    #@+node:_set_now
    def _set_now(self, value):
        proxy = weakref.proxy
        self.calendar.now = _to_datetime(value)
    #@-node:_set_now
    #@-node:Calendar Setters
    #@-node:Setting methods
    #@+node:Freezer Methods
    #@+node:_unfreeze
    def _unfreeze(self, attrib_name):
        if self.__dict__.has_key(attrib_name):
            del self.__dict__[attrib_name]
    #@-node:_unfreeze
    #@+node:_wrap_attrib
    def _wrap_attrib(self, method):
        attrib_name = method.__name__[7:]
        recursion_attrib = "_rec" + attrib_name

        try:
            dest, dattr = self.__at_compile
            raise RecursionError("Recursive definition of %s(%s) and %s(%s)." \
                                 % (self.path, attrib_name, dest.path, dattr))
        except AttributeError: pass

        if not self._is_compiled:
            raise _IncompleteError(self, attrib_name)

        try:
            getattr(self, recursion_attrib)
            raise RecursionError(self, attrib_name)
        except AttributeError: pass

        setattr(self, recursion_attrib, True)

        try:
            result = method(self)

            if self._is_frozen:
                setattr(self, attrib_name, result)

            return result
        finally:
            delattr(self, recursion_attrib)
    #@-node:_wrap_attrib
    #@+node:_find_frozen
    def _find_frozen(self, attrib_name, default=None):
        value = self.__dict__.get(attrib_name)
        if value is not None:
            return value

        up = self.up
        return up and up._find_frozen(attrib_name) or default
    #@-node:_find_frozen
    #@-node:Freezer Methods
    #@+node:Calculation Methods
    #@+node:__calc_performed_effort
    def __calc_performed_effort(self):
        if self.children:
            return self._to_delta(sum([ t.performed_effort for t in self.children ]))

        return pcalendar.Minutes(0)

    performed_effort = _TaskProperty(__calc_performed_effort)
    #@-node:__calc_performed_effort
    #@+node:__calc_estimated_effort
    def __calc_estimated_effort(self):
        if self.children:
            return self._to_delta(sum([ t.estimated_effort for t in self.children ]))

        return self.effort

    estimated_effort = _TaskProperty(__calc_estimated_effort)
    #@-node:__calc_estimated_effort
    #@+node:__calc_start
    def __calc_start(self):
        to_start = self._to_start

        if self.children:
            try:
                return min([ to_start(t.start) for t in self.children
                             if not t._is_parent_referer ])
            except ValueError:
                #@            << raise child recursion error >>
                #@+node:<< raise child recursion error >>
                self._raise(RecursionError("A child defines a "\
                                           "recursive definition at %s" % self.path))
                #@-node:<< raise child recursion error >>
                #@nl

        try:
            end = self.end
            duration = self.__dict__.get("duration")
            if duration is not None:
                start = end.to_datetime() - datetime.timedelta(minutes=duration)
            else:
                start = end - self.length

            return to_start(start)

        except RecursionError:
            start = self._find_frozen("start")
            if start: return to_start(start)
            #@        << raise recursion error >>
            #@+node:<< raise recursion error >>
            raise RecursionError("you have to specify a "\
                                 "start or an end at %s" % self.path)
            #@nonl
            #@-node:<< raise recursion error >>
            #@nl

    start = _TaskProperty(__calc_start)

    #@-node:__calc_start
    #@+node:__calc_end
    def __calc_end(self):
        to_end = self._to_end

        if self.children:
            try:
                return max([ to_end(t.end) for t in self.children
                             if not t._is_parent_referer ])
            except ValueError:
                #@            << raise child recursion error >>
                #@+node:<< raise child recursion error >>
                self._raise(RecursionError("A child defines a "\
                                           "recursive definition at %s" % self.path))
                #@-node:<< raise child recursion error >>
                #@nl

        try:
            start = self.start
            duration = self.__dict__.get("duration")
            if duration is not None:
                end = start.to_datetime() + datetime.timedelta(minutes=duration)
            else:
                end = start + self.length

            return to_end(end)

        except RecursionError:
            end = self._find_frozen("end")
            if end: return to_end(end)
            #@        << raise recursion error >>
            #@+node:<< raise recursion error >>
            raise RecursionError("you have to specify a "\
                                 "start or an end at %s" % self.path)
            #@nonl
            #@-node:<< raise recursion error >>
            #@nl


    end = _TaskProperty(__calc_end)
    #@-node:__calc_end
    #@+node:__calc_load
    def __calc_load(self):
        length = self.__dict__.get("length")
        effort = self.__dict__.get("effort")

        if length is not None and effort is not None:
            return float(effort) / (float(length) or 1.0)

        load = self._find_frozen("load")
        if load is not None: return load
        return 1.0

    load = _TaskProperty(__calc_load)
    #@-node:__calc_load
    #@+node:__calc_length
    def __calc_length(self):
        effort = self.__dict__.get("effort")
        if effort is None:
            return self.end - self.start

        return self._to_delta(effort / self.load)

    length = _RoundingTaskProperty(__calc_length, "length")
    #@-node:__calc_length
    #@+node:__calc_duration
    def __calc_duration(self):
        return self._to_delta(self.end.to_datetime()\
                              - self.start.to_datetime(), True)

    duration = _TaskProperty(__calc_duration)
    #@-node:__calc_duration
    #@+node:__calc_effort
    def __calc_effort(self):
        if self.children:
            return self._to_delta(sum([ t.effort for t in self.children ]))

        return self._to_delta(self.length * self.load)

    effort = _RoundingTaskProperty(__calc_effort, "effort")
    #@-node:__calc_effort
    #@+node:__calc_done
    def __calc_done(self):
        if self.children:
            dones = map(lambda t: t.done, self.children)
            return self._to_delta(sum(dones))

        res = self._iter_booked_resources()
        done = sum(map(lambda r: r.done_of(self), res))

        complete = self.__dict__.get("complete")
        todo = self.__dict__.get("todo")

        if not done and complete == 100 or todo == 0:
            #if now is not set
            done = self.effort

        return self._to_delta(done)

    done = _TaskProperty(__calc_done)
    #@-node:__calc_done
    #@+node:__calc_buffer
    def __calc_buffer(self):
        if self.children:
            return self._to_delta(min(map(lambda t: t.buffer, self.children)))

        scenario = self.scenario
        end = self.end
        old_end = self.__dict__.get("end")

        #@    << find all tasks, that depend on my end >>
        #@+node:<< find all tasks, that depend on my end >>
        deps = { }
        task = self
        while task:
            deps.update(task._dependencies.get("end", {}))
            task = task.up
        #@nonl
        #@-node:<< find all tasks, that depend on my end >>
        #@nl

        #@    << define unfreeze_parents >>
        #@+node:<< define unfreeze_parents >>
        def unfreeze_parents():
            task = self.up
            while task:
                task._unfreeze("end")
                task = task.up
        #@nonl
        #@-node:<< define unfreeze_parents >>
        #@nl

        buffers = [ ]
        for d in deps.keys():
            path, attrib = _split_path(d)
            if attrib != "start":
                continue

            #@        << calculate buffer to descendant 'd' >>
            #@+node:<< calculate buffer to descendant 'd' >>
            unfreeze_parents()

            # the following code considers a expressione like
            # start = predecessor.end + Delta("1d") the buffer
            # calculation must be aware of the 1d delay.
            # (therefore a simple succ_start - end would be
            # incorrect)
            # Solution: Simluate a later end and calculate the
            # real delay

            succ_task = self.get_task(path)
            simulated_task = Task(succ_task._function,
                                  succ_task.name,
                                  succ_task.up, 1)

            current_start = succ_task.start
            simulated_end = current_start
            self.end = current_start

            simulated_task._generate()
            simulated_start = simulated_task.start

            unfreeze_parents()
            if old_end: self.end = old_end
            else: self._unfreeze("end")
            del simulated_task

            current_delay = current_start - end
            simulated_delay = simulated_start - simulated_end
            real_delay = current_delay - simulated_delay
            try:
                buffer_ = real_delay + succ_task.buffer
            except RecursionError, err:
                self._raise(err)
            #@nonl
            #@-node:<< calculate buffer to descendant 'd' >>
            #@nl

            buffers.append(buffer_)
            if not buffer_:
                break

        if buffers:
            return self._to_delta(min(buffers))

        return not self.milestone \
               and self.root.end - end \
               or self._to_delta(0)

    buffer = _TaskProperty(__calc_buffer)
    #@-node:__calc_buffer
    #@+node:__calc_complete
    def __calc_complete(self):
        done = self.done
        todo = self.todo
        return int(100.0 * done / ((done + todo) or 1))

    complete = _TaskProperty(__calc_complete)
    #@-node:__calc_complete
    #@+node:__calc_todo
    def __calc_todo(self):
        complete = self.__dict__.get("complete")
        if complete:
            # effort = done + todo
            #             done               done
            # complete = ------ ==> todo = -------- - done
            #            effort            complete
            complete = float(complete)
            done = self.done
            if done:
                done = float(done)
                return self._to_delta(done * 100.0 / complete - done)
            return self._to_delta(self.effort * complete / 100.0)

        if self.children:
            todos = map(lambda t: t.todo, self.children)
            return self._to_delta(sum(todos))

        todo = sum(map(lambda r: r.todo_of(self), self.booked_resource))
        return self._to_delta(max(todo, self.effort - self.done))

    todo = _TaskProperty(__calc_todo)
    #@-node:__calc_todo
    #@-node:Calculation Methods
    #@+node:Check Methods
    #@+node:__check_task
    def __check_task(self):
        if self.children: return

        start = self._find_frozen("start")
        end = self._find_frozen("end")

        if not (start or end):
            self._raise(ValueError("You must specify either a"\
                                   " start or an end attribute"))

        if start and end: return

        length = self.__dict__.get("length")
        duration = self.__dict__.get("duration")
        effort = self.__dict__.get("effort")
        if not (effort or length or duration):
            #set a default value
            self._set_effort("1d")
            #self._raise(ValueError("You must specify either a"\
            #                       " length or a duration or "\
            #                       "an effort attribute"))
    #@-node:__check_task
    #@+node:__check_milestone
    def __check_milestone(self):
        if not self.milestone: return

        self.length = self._to_delta(0)
        start = self.__dict__.get("start")
        if not start:
            self._raise(ValueError("Milestone must have start attribute"),
                                   "milstone")

        if self.__start_class.__name__ == "edt":
            #the milestone is probably dependent on the end date of
            #an other task (see edt in pcalendar) ==> start at the end date
            self.start = self.end = self._to_end(self.start)
        else:
            self.start = self.end = self._to_start(self.start)

    #@-node:__check_milestone
    #@+node:_check_completion
    def _check_completion(self):
        if not self.performed_effort: return
        if self.root.is_snapshot: return

        # allocation is not done yet ==> self.todo, self.done,
        # self.complete cannot be calculated
        if self._find_frozen("complete", 0) < 100 \
               and self.__dict__.get("todo", 1) > 0:
            return

        start = self.performed_start
        end = self.performed_end
        #ensure that self.start.to_datetime() < self.end.to_datetime()
        cstart = self._to_start(start)
        if cstart.to_datetime() > start: cstart = self._to_end(start)

        cend = self._to_end(end)
        if cend.to_datetime() < end: cend = self._to_start(end)

        self.start = cstart
        self.end = cend

        if self.performed_effort != self.effort:
            self.estimated_effort = self.effort
            self.effort = self.performed_effort
    #@-node:_check_completion
    #@+node:check
    def check(self):
        if self._constraint and self._is_compiled:
            globals_ = self._function.func_globals
            globals_["me"] = self
            globals_["up"] = self.up
            globals_["root"] = self.root
            globals_["assert_"] = self.__assert
            self._constraint()
    #@-node:check
    #@-node:Check Methods
    #@+node:Error Methods
    #@+node:__assert
    def __assert(self, value):
        if not value:
            warnings.warn('Assertion in scenario: "%s".' % self.scenario,
                          RuntimeWarning, 2)
    #@-node:__assert
    #@+node:_warn
    def _warn(self, message, attrib=None, level=2):
        self.__compile_function([], True, _MeProxyWarn(self, attrib, message))
    #@-node:_warn
    #@+node:_raise
    def _raise(self, exc, attrib=None):
        self.__compile_function([], True, _MeProxyError(self, attrib, exc))
        raise exc
    #@-node:_raise
    #@-node:Error Methods
    #@-others
#@nonl
#@-node:class Task
#@-node:Task
#@+node:Projects
#@+node:class _ProjectBase
class _ProjectBase(Task):
    """
    Base class for all projects.
    """
    #@	<< class _ProjectBase declarations >>
    #@+node:<< class _ProjectBase declarations >>
    __attrib_completions__ = { }
    __attrib_completions__.update(Task.__attrib_completions__)
    del __attrib_completions__["milestone"] #project cannot be milestones

    priority = 500
    efficiency = 1.0
    max_load = 1.0
    balance = 0
    resource = None
    copy_src = None
    has_actual_data = False
    is_snapshot = False

    #@-node:<< class _ProjectBase declarations >>
    #@nl
    #@	@+others
    #@+node:__init__
    def __init__(self, top_task, scenario="_default", id=""):
        self.calendar = pcalendar.Calendar()
        Task.__init__(self, top_task, top_task.func_name)
        self.id = id or self.name
        self.scenario = scenario
        self.all_scenarios = set(("_default",))
        self.path = "root"
        self._globals = top_task.func_globals.copy()
        self._generate()

    #@-node:__init__
    #@+node:_idendity_
    def _idendity_(self): return self.id
    #@-node:_idendity_
    #@+node:_restore_globals
    def _restore_globals(self):
        self._function.func_globals.clear()
        self._function.func_globals.update(self._globals)
        del self._globals
    #@-node:_restore_globals
    #@+node:free
    def free(self):
        all_resources = self.all_resources()
        for r in all_resources:
            r().unbook_tasks_of_project(self.id, self.scenario)

        for t in self:
            t.booked_resource = ()

        return all_resources
    #@-node:free
    #@+node:_get_balancing_list
    def _get_balancing_list(self):

        try:
            cached_list = balancing_cache[self._function.org_code]
            if len(cached_list) != len(tuple(self)):
                # different scenarios can have different tasks
                raise KeyError()

        except KeyError:
            cached_list = _build_balancing_list(self)
            balancing_cache[self._function.org_code] = cached_list
        else:
            cached_list = [ self.get_task(t.path) for t in cached_list ]

        return cached_list
    #@-node:_get_balancing_list
    #@+node:snapshot
    def snapshot(self, indent="", name=None):
        text = Task.snapshot(self, indent, name)

        lines = text.splitlines(True)
        indent += "    "

        def make_resource(r):
            return '%sclass %s(Resource): title = "%s"\n' \
                   % (indent, r.name, r.title)

        now = datetime.datetime.now().strftime("%x %H:%M")
        resource_text = map(lambda r: make_resource(r), self.all_resources())
        lines.insert(1, "%sfrom faces import Resource\n" % indent)
        lines.insert(2, "".join(resource_text) + "\n")
        lines.insert(3, '%snow = "%s"\n' % (indent, now))
        lines.insert(4, '%sis_snapshot = True\n' % indent)
        return "".join(lines)
    #@-node:snapshot
    #@-others
#@-node:class _ProjectBase
#@+node:class Project
class Project(_ProjectBase):
    """
    Generates a Project without allocating resources.

    @param top_task: Specifies the highest function of a project definiton.

    @param scenario: Specifies the name of the scenario which should be scheduled.

    @param id: Specifiess a unique idenfication name to distinguish the project from
    other projects in the resource database. The default value for id
    is the name of top_task.
    """
    #@	<< class Project declarations >>
    #@+node:<< class Project declarations >>
    __call_completion__ = 'Project(|top_task, scenario="_default", id=None)'

    #@-node:<< class Project declarations >>
    #@nl
    #@	@+others
    #@+node:__init__
    def __init__(self, top_task, scenario="_default", id=None):
        _ProjectBase.__init__(self, top_task, scenario, id)
        no_snapshot = not self.is_snapshot
        for t in self:
            t._is_frozen = True
            t._recalc_properties()
            no_snapshot and t.check()

        self._restore_globals()

    #@-node:__init__
    #@-others

#@-node:class Project
#@+node:class _AllocationPoject
class _AllocationPoject(_ProjectBase):
    #@	@+others
    #@+node:unfreeze_parents
    def unfreeze_parents(self):
        if self.has_actual_data:
            for t in filter(lambda t: t.children, self):
                if not t._original_values.has_key("start"): t._unfreeze("start")
                if not t._original_values.has_key("end"): t._unfreeze("end")
    #@-node:unfreeze_parents
    #@-others
#@-node:class _AllocationPoject
#@+node:class BalancedProject
class BalancedProject(_AllocationPoject):
    """
    Generates a project with allocated resources. The tasks are balanced
    to fit the resources load conditions.
    """
    #@	<< class BalancedProject declarations >>
    #@+node:<< class BalancedProject declarations >>
    __call_completion__ = """BalancedProject(|top_task, scenario="_default",
    id=None, balance=SMART, performed=None)"""

    #@-node:<< class BalancedProject declarations >>
    #@nl
    #@	@+others
    #@+node:__init__
    def __init__(self, top_task, scenario="_default",
                 id=None, balance=SMART, performed=None):
        _AllocationPoject.__init__(self, top_task, scenario, id)
        self.balance = balance
        if performed:
            self._distribute_performed(performed)
            self.has_actual_data = True

        no_snapshot = not self.is_snapshot
        if no_snapshot:
            self.allocate()
        else:
            self.allocate_snapshot()

        for t in self:
            t._is_frozen = True
            t._recalc_properties()
            no_snapshot and t.check()

        self._restore_globals()
    #@nonl
    #@-node:__init__
    #@+node:allocate_snapshot
    def allocate_snapshot(self):
        all_resources = self.free()
        scenario = self.scenario
        has_actual_data = True
        for t in self:
            if not t.resource or t.milestone or t.children:
                continue

            t._convert_performed(all_resources)
            t._allocate_performed(t._performed)
    #@-node:allocate_snapshot
    #@+node:allocate
    def allocate(self):
        all_resources = self.free()
        balancing_list = self._get_balancing_list()
        scenario = self.scenario

        #for t in balancing_list:
        #    print t.path

        for t in balancing_list:
            t._compile([], True)

            if not t.resource or t.milestone or t.children:
                continue

            if t._convert_performed(all_resources):
                has_actual_data = True

            try:
                t._allocate_performed(t._performed)
            except AttributeError:
                pass

            allocator = _allocators[t.balance]
            min_val = None
            min_state = None
            for p in range(t.resource._permutation_count()):
                state = t._test_allocation(p, allocator)

                if not state: continue

                to_minimize = state[0]
                if not min_val or min_val > to_minimize:
                    min_val = to_minimize
                    min_state = state

            if min_state:
                t._allocate(min_state, allocator)
            elif t.performed_start:
                # t could not be allocated ==>
                # performance data holds all information
                t.start = t._to_start(t.performed_start)
                t.end = t._to_end(t.performed_end)

        self.unfreeze_parents()
    #@-node:allocate
    #@+node:_distribute_performed
    def _distribute_performed(self, performed):
        project_id = self._idendity_()
        plen = len(project_id)

        performed = filter(lambda item: item[0].startswith(project_id),
                           performed)
        performed.sort()

        task = None
        for item in performed:
            path = item[0]
            rpath = "root" + path[plen:]
            task = self.get_task(rpath)

            if not task:
                #@            << extract task in activity path >>
                #@+node:<< extract task in activity path >>
                #@+at
                # A performed path can have sub activities appended to the
                # task path.
                # like:
                #
                #   root.parent1.parent2.task.subactivity
                #
                # here rhe correct task path is:
                #
                #     root.parent1.parent2.task
                #
                #@-at
                #@@code
                orpath = rpath
                while not task:
                    #path can specify a sub module
                    #find the correct path to the module
                    try:
                        last_dot = rpath.rindex(".", 0, len(rpath))
                    except ValueError:
                        break

                    rpath = rpath[:last_dot]
                    task = self.get_task(rpath)

                item = list(item)
                item.append(orpath[len(rpath):])
                #@nonl
                #@-node:<< extract task in activity path >>
                #@nl

            if not task or task.children:
                self._warn("The performance data contain "
                           "a task with id '%s'. But such "
                           "a task does not exist in your "
                           "project." % path)
                continue

            if not isinstance(task.performed, list):
                task.performed = list(task.performed)

            task.performed.append(item[1:])
    #@nonl
    #@-node:_distribute_performed
    #@-others
#@-node:class BalancedProject
#@+node:class AdjustedProject
class AdjustedProject(_AllocationPoject):
    """
    Generates a project with allocated resources. The tasks are
    adjusted to the actual tracking data and balanced to fit the
    resources load conditions.
    """
    #@	<< class AdjustedProject declarations >>
    #@+node:<< class AdjustedProject declarations >>
    __call_completion__ = 'AdjustedProject(|base_project)'

    #@-node:<< class AdjustedProject declarations >>
    #@nl
    #@	@+others
    #@+node:__init__
    def __init__(self, base_project):
        _AllocationPoject.__init__(self, base_project._function,
                                   base_project.scenario,
                                   base_project.id)

        self.balance = base_project.balance
        self.has_actual_data = base_project.has_actual_data
        self.allocate(base_project)
        for t in self:
            t._is_frozen = True
            t._recalc_properties()
            t.check()

        self._restore_globals()


    #@-node:__init__
    #@+node:allocate
    def allocate(self, base):
        balancing_list = self._get_balancing_list()
        scenario = self.scenario
        cal = self.calendar
        now = cal.now

        #for t in balancing_list:
        #    print t.path

        #@    << free the resources, we have to rebook >>
        #@+node:<< free the resources, we have to rebook >>
        for t in balancing_list:
            src = base.get_task(t.path)
            if src.end > now or src.complete < 100:
                for r in src._iter_booked_resources():
                    r.unbook_task(src)
        #@nonl
        #@-node:<< free the resources, we have to rebook >>
        #@nl

        for t in balancing_list:
            src = base.get_task(t.path)
            if src.end <= now and src.complete == 100:
                #@            << copy the attribs of complete tasks >>
                #@+node:<< copy the attribs of complete tasks >>
                t.effort = src.effort
                t.load = src.load
                t.start = src.start
                t.end = src.end
                t.done = src.done
                t.todo = src.todo
                t.booked_resource = src.booked_resource
                t.performed_resource = src.performed_resource
                t._unfreeze("length")
                t._unfreeze("duration")
                #@nonl
                #@-node:<< copy the attribs of complete tasks >>
                #@nl
                continue

            t._compile([], True)
            if not t.resource or t.milestone or t.children:
                continue

            # now allocate the uncomplete tasks
            #@        << allocate performed data >>
            #@+node:<< allocate performed data >>
            try:
                t._performed = src._performed
                t._allocate_performed(t._performed)
            except AttributeError:
                pass
            #@nonl
            #@-node:<< allocate performed data >>
            #@nl
            allocator = _allocators[t.balance]

            if src.start >= now:
                #@            << allocate tasks, that have not begun yet >>
                #@+node:<< allocate tasks, that have not begun yet >>
                min_val = None
                min_state = None
                for p in range(t.resource._permutation_count()):
                    state = t._test_allocation(p, allocator)
                    if not state: continue

                    to_minimize = state[0]
                    if not min_val or min_val > to_minimize:
                        min_val = to_minimize
                        min_state = state

                if min_state:
                    t._allocate(min_state, allocator)
                elif t.performed_start:
                    t.start = t._to_start(t.performed_start)
                    t.end = t._to_end(t.performed_end)
                #@-node:<< allocate tasks, that have not begun yet >>
                #@nl
            else:
                #@            << allocate tasks, that are allready at work >>
                #@+node:<< allocate tasks, that are allready at work >>
                if t.__dict__.has_key("effort"):
                    t.effort = t._to_delta(src.done + src.todo).round()

                resource = src.booked_resource or src.performed_resource
                state = allocator.test_allocation(t, resource)
                if state:
                    t._allocate(state, allocator)
                #@nonl
                #@-node:<< allocate tasks, that are allready at work >>
                #@nl

        self.unfreeze_parents()
    #@nonl
    #@-node:allocate
    #@-others
#@-node:class AdjustedProject
#@-node:Projects
#@-others


"""
    Atttribute mit Bedeutung:

    calendar
    --------
    minimum_time_unit     |int in minutes|
    working_days_per_week |int in days   |
    working_days_per_month|int in days   |
    working_days_per_year |int in days   |
    working_hours_per_day |int in hours  |
    vacation              | [ one_day, (from, to), .. ] |
    working_days
    now



    Task
    -----
    load
    start
    end
    length
    effort
    duration
    resource
    booked_resource

    milestone
    complete
    done
    todo
    priority
    efficiency
    buffer

    children
    depth
    index
    path
    dont_inherit

    performed_effort
    performed_end
    performed_start

    sum()
    min()
    max()
    costs()
    indent_name()
    max_load

    copy_src (set: copy all attributes of another task
              get: reference of copy)

    balance

    for gantt
    -----
    line
    accumulate




    Resource
    ----------
    efficiency
    load
    vacation
    max_load

"""
#@-node:@file task.py
#@-leo

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
