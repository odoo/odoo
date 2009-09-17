# runtime.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""provides runtime services for templates, including Context, Namespace, and various helper functions."""

from mako import exceptions, util
import __builtin__, inspect, sys

class Context(object):
    """provides runtime namespace, output buffer, and various callstacks for templates."""
    def __init__(self, buffer, **data):
        self._buffer_stack = [buffer]
        self._orig = data  # original data, minus the builtins
        self._data = __builtin__.__dict__.copy() # the context data which includes builtins
        self._data.update(data)
        self._kwargs = data.copy()
        self._with_template = None
        self.namespaces = {}

        # "capture" function which proxies to the generic "capture" function
        self._data['capture'] = lambda x, *args, **kwargs: capture(self, x, *args, **kwargs)

        # "caller" stack used by def calls with content
        self.caller_stack = self._data['caller'] = CallerStack()

    lookup = property(lambda self:self._with_template.lookup)
    kwargs = property(lambda self:self._kwargs.copy())

    def push_caller(self, caller):
        self.caller_stack.append(caller)

    def pop_caller(self):
        del self.caller_stack[-1]

    def keys(self):
        return self._data.keys()

    def __getitem__(self, key):
        return self._data[key]

    def _push_writer(self):
        """push a capturing buffer onto this Context and return the new Writer function."""

        buf = util.FastEncodingBuffer()
        self._buffer_stack.append(buf)
        return buf.write

    def _pop_buffer_and_writer(self):
        """pop the most recent capturing buffer from this Context
        and return the current writer after the pop.

        """

        buf = self._buffer_stack.pop()
        return buf, self._buffer_stack[-1].write

    def _push_buffer(self):
        """push a capturing buffer onto this Context."""

        self._push_writer()

    def _pop_buffer(self):
        """pop the most recent capturing buffer from this Context."""

        return self._buffer_stack.pop()

    def get(self, key, default=None):
        return self._data.get(key, default)

    def write(self, string):
        """write a string to this Context's underlying output buffer."""

        self._buffer_stack[-1].write(string)

    def writer(self):
        """return the current writer function"""

        return self._buffer_stack[-1].write

    def _copy(self):
        c = Context.__new__(Context)
        c._buffer_stack = self._buffer_stack
        c._data = self._data.copy()
        c._orig = self._orig
        c._kwargs = self._kwargs
        c._with_template = self._with_template
        c.namespaces = self.namespaces
        c.caller_stack = self.caller_stack
        return c
    def locals_(self, d):
        """create a new Context with a copy of this Context's current state, updated with the given dictionary."""
        if len(d) == 0:
            return self
        c = self._copy()
        c._data.update(d)
        return c
    def _clean_inheritance_tokens(self):
        """create a new copy of this Context with tokens related to inheritance state removed."""
        c = self._copy()
        x = c._data
        x.pop('self', None)
        x.pop('parent', None)
        x.pop('next', None)
        return c

class CallerStack(list):
    def __init__(self):
        self.nextcaller = None
    def __nonzero__(self):
        return self._get_caller() and True or False
    def _get_caller(self):
        return self[-1]
    def __getattr__(self, key):
        return getattr(self._get_caller(), key)
    def _push_frame(self):
        self.append(self.nextcaller or None)
        self.nextcaller = None
    def _pop_frame(self):
        self.nextcaller = self.pop()


class Undefined(object):
    """represents an undefined value in a template."""
    def __str__(self):
        raise NameError("Undefined")
    def __nonzero__(self):
        return False

UNDEFINED = Undefined()

class _NSAttr(object):
    def __init__(self, parent):
        self.__parent = parent
    def __getattr__(self, key):
        ns = self.__parent
        while ns:
            if hasattr(ns.module, key):
                return getattr(ns.module, key)
            else:
                ns = ns.inherits
        raise AttributeError(key)

class Namespace(object):
    """provides access to collections of rendering methods, which can be local, from other templates, or from imported modules"""
    def __init__(self, name, context, module=None, template=None, templateuri=None, callables=None, inherits=None, populate_self=True, calling_uri=None):
        self.name = name
        if module is not None:
            mod = __import__(module)
            for token in module.split('.')[1:]:
                mod = getattr(mod, token)
            self._module = mod
        else:
            self._module = None
        if templateuri is not None:
            self.template = _lookup_template(context, templateuri, calling_uri)
            self._templateuri = self.template.module._template_uri
        else:
            self.template = template
            if self.template is not None:
                self._templateuri = self.template.module._template_uri
        self.context = context
        self.inherits = inherits
        if callables is not None:
            self.callables = dict([(c.func_name, c) for c in callables])
        else:
            self.callables = None
        if populate_self and self.template is not None:
            (lclcallable, lclcontext) = _populate_self_namespace(context, self.template, self_ns=self)

    module = property(lambda s:s._module or s.template.module)
    filename = property(lambda s:s._module and s._module.__file__ or s.template.filename)
    uri = property(lambda s:s.template.uri)

    def attr(self):
        if not hasattr(self, '_attr'):
            self._attr = _NSAttr(self)
        return self._attr
    attr = property(attr)

    def get_namespace(self, uri):
        """return a namespace corresponding to the given template uri.

        if a relative uri, it is adjusted to that of the template of this namespace"""
        key = (self, uri)
        if self.context.namespaces.has_key(key):
            return self.context.namespaces[key]
        else:
            ns = Namespace(uri, self.context._copy(), templateuri=uri, calling_uri=self._templateuri)
            self.context.namespaces[key] = ns
            return ns

    def get_template(self, uri):
        return _lookup_template(self.context, uri, self._templateuri)

    def get_cached(self, key, **kwargs):
        if self.template:
            if not self.template.cache_enabled:
                createfunc = kwargs.get('createfunc', None)
                if createfunc:
                    return createfunc()
                else:
                    return None

            if self.template.cache_dir:
                kwargs.setdefault('data_dir', self.template.cache_dir)
            if self.template.cache_type:
                kwargs.setdefault('type', self.template.cache_type)
            if self.template.cache_url:
                kwargs.setdefault('url', self.template.cache_url)
        return self.cache.get(key, **kwargs)

    def cache(self):
        return self.template.cache
    cache = property(cache)

    def include_file(self, uri, **kwargs):
        """include a file at the given uri"""
        _include_file(self.context, uri, self._templateuri, **kwargs)

    def _populate(self, d, l):
        for ident in l:
            if ident == '*':
                for (k, v) in self._get_star():
                    d[k] = v
            else:
                d[ident] = getattr(self, ident)

    def _get_star(self):
        if self.callables:
            for key in self.callables:
                yield (key, self.callables[key])
        if self.template:
            def get(key):
                callable_ = self.template.get_def(key).callable_
                return lambda *args, **kwargs:callable_(self.context, *args, **kwargs)
            for k in self.template.module._exports:
                yield (k, get(k))
        if self._module:
            def get(key):
                callable_ = getattr(self._module, key)
                return lambda *args, **kwargs:callable_(self.context, *args, **kwargs)
            for k in dir(self._module):
                if k[0] != '_':
                    yield (k, get(k))

    def __getattr__(self, key):
        if self.callables and key in self.callables:
            return self.callables[key]

        if self.template and self.template.has_def(key):
            callable_ = self.template.get_def(key).callable_
            return lambda *args, **kwargs:callable_(self.context, *args, **kwargs)

        if self._module and hasattr(self._module, key):
            callable_ = getattr(self._module, key)
            return lambda *args, **kwargs:callable_(self.context, *args, **kwargs)

        if self.inherits is not None:
            return getattr(self.inherits, key)
        raise exceptions.RuntimeException("Namespace '%s' has no member '%s'" % (self.name, key))

def supports_caller(func):
    """apply a caller_stack compatibility decorator to a plain Python function."""
    def wrap_stackframe(context,  *args, **kwargs):
        context.caller_stack._push_frame()
        try:
            return func(context, *args, **kwargs)
        finally:
            context.caller_stack._pop_frame()
    return wrap_stackframe

def capture(context, callable_, *args, **kwargs):
    """execute the given template def, capturing the output into a buffer."""
    if not callable(callable_):
        raise exceptions.RuntimeException("capture() function expects a callable as its argument (i.e. capture(func, *args, **kwargs))")
    context._push_buffer()
    try:
        callable_(*args, **kwargs)
    finally:
        buf = context._pop_buffer()
    return buf.getvalue()

def _include_file(context, uri, calling_uri, **kwargs):
    """locate the template from the given uri and include it in the current output."""
    template = _lookup_template(context, uri, calling_uri)
    (callable_, ctx) = _populate_self_namespace(context._clean_inheritance_tokens(), template)
    callable_(ctx, **_kwargs_for_callable(callable_, context._orig, **kwargs))

def _inherit_from(context, uri, calling_uri):
    """called by the _inherit method in template modules to set up the inheritance chain at the start
    of a template's execution."""
    if uri is None:
        return None
    template = _lookup_template(context, uri, calling_uri)
    self_ns = context['self']
    ih = self_ns
    while ih.inherits is not None:
        ih = ih.inherits
    lclcontext = context.locals_({'next':ih})
    ih.inherits = Namespace("self:%s" % template.uri, lclcontext, template = template, populate_self=False)
    context._data['parent'] = lclcontext._data['local'] = ih.inherits
    callable_ = getattr(template.module, '_mako_inherit', None)
    if callable_ is not None:
        ret = callable_(template, lclcontext)
        if ret:
            return ret

    gen_ns = getattr(template.module, '_mako_generate_namespaces', None)
    if gen_ns is not None:
        gen_ns(context)
    return (template.callable_, lclcontext)

def _lookup_template(context, uri, relativeto):
    lookup = context._with_template.lookup
    if lookup is None:
        raise exceptions.TemplateLookupException("Template '%s' has no TemplateLookup associated" % context._with_template.uri)
    uri = lookup.adjust_uri(uri, relativeto)
    try:
        return lookup.get_template(uri)
    except exceptions.TopLevelLookupException, e:
        raise exceptions.TemplateLookupException(str(e))

def _populate_self_namespace(context, template, self_ns=None):
    if self_ns is None:
        self_ns = Namespace('self:%s' % template.uri, context, template=template, populate_self=False)
    context._data['self'] = context._data['local'] = self_ns
    if hasattr(template.module, '_mako_inherit'):
        ret = template.module._mako_inherit(template, context)
        if ret:
            return ret
    return (template.callable_, context)

def _render(template, callable_, args, data, as_unicode=False):
    """create a Context and return the string output of the given template and template callable."""

    if as_unicode:
        buf = util.FastEncodingBuffer(unicode=True)
    elif template.output_encoding:
        buf = util.FastEncodingBuffer(unicode=as_unicode, encoding=template.output_encoding, errors=template.encoding_errors)
    else:
        buf = util.StringIO()
    context = Context(buf, **data)
    context._with_template = template
    _render_context(template, callable_, context, *args, **_kwargs_for_callable(callable_, data))
    return context._pop_buffer().getvalue()

def _kwargs_for_callable(callable_, data, **kwargs):
    argspec = inspect.getargspec(callable_)
    namedargs = argspec[0] + [v for v in argspec[1:3] if v is not None]
    for arg in namedargs:
        if arg != 'context' and arg in data and arg not in kwargs:
            kwargs[arg] = data[arg]
    return kwargs

def _render_context(tmpl, callable_, context, *args, **kwargs):
    import mako.template as template
    # create polymorphic 'self' namespace for this template with possibly updated context
    if not isinstance(tmpl, template.DefTemplate):
        # if main render method, call from the base of the inheritance stack
        (inherit, lclcontext) = _populate_self_namespace(context, tmpl)
        _exec_template(inherit, lclcontext, args=args, kwargs=kwargs)
    else:
        # otherwise, call the actual rendering method specified
        (inherit, lclcontext) = _populate_self_namespace(context, tmpl.parent)
        _exec_template(callable_, context, args=args, kwargs=kwargs)

def _exec_template(callable_, context, args=None, kwargs=None):
    """execute a rendering callable given the callable, a Context, and optional explicit arguments

    the contextual Template will be located if it exists, and the error handling options specified
    on that Template will be interpreted here.
    """
    template = context._with_template
    if template is not None and (template.format_exceptions or template.error_handler):
        error = None
        try:
            callable_(context, *args, **kwargs)
        except Exception, e:
            error = e
        except:
            e = sys.exc_info()[0]
            error = e
        if error:
            if template.error_handler:
                result = template.error_handler(context, error)
                if not result:
                    raise error
            else:
                error_template = exceptions.html_error_template()
                context._buffer_stack[:] = [util.FastEncodingBuffer(error_template.output_encoding, error_template.encoding_errors)]
                context._with_template = error_template
                error_template.render_context(context, error=error)
    else:
        callable_(context, *args, **kwargs)
