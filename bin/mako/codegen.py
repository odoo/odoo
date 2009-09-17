# codegen.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""provides functionality for rendering a parsetree constructing into module source code."""

import time
import re
from mako.pygen import PythonPrinter
from mako import util, ast, parsetree, filters

MAGIC_NUMBER = 5


def compile(node, uri, filename=None, default_filters=None, buffer_filters=None, imports=None, source_encoding=None, generate_unicode=True):
    """generate module source code given a parsetree node, uri, and optional source filename"""

    buf = util.FastEncodingBuffer(unicode=generate_unicode)

    printer = PythonPrinter(buf)
    _GenerateRenderMethod(printer, _CompileContext(uri, filename, default_filters, buffer_filters, imports, source_encoding, generate_unicode), node)
    return buf.getvalue()

class _CompileContext(object):
    def __init__(self, uri, filename, default_filters, buffer_filters, imports, source_encoding, generate_unicode):
        self.uri = uri
        self.filename = filename
        self.default_filters = default_filters
        self.buffer_filters = buffer_filters
        self.imports = imports
        self.source_encoding = source_encoding
        self.generate_unicode = generate_unicode
        
class _GenerateRenderMethod(object):
    """a template visitor object which generates the full module source for a template."""
    def __init__(self, printer, compiler, node):
        self.printer = printer
        self.last_source_line = -1
        self.compiler = compiler
        self.node = node
        self.identifier_stack = [None]
        
        self.in_def = isinstance(node, parsetree.DefTag)

        if self.in_def:
            name = "render_" + node.name
            args = node.function_decl.get_argument_expressions()
            filtered = len(node.filter_args.args) > 0 
            buffered = eval(node.attributes.get('buffered', 'False'))
            cached = eval(node.attributes.get('cached', 'False'))
            defs = None
            pagetag = None
        else:
            defs = self.write_toplevel()
            pagetag = self.compiler.pagetag
            name = "render_body"
            if pagetag is not None:
                args = pagetag.body_decl.get_argument_expressions()
                if not pagetag.body_decl.kwargs:
                    args += ['**pageargs']
                cached = eval(pagetag.attributes.get('cached', 'False'))
            else:
                args = ['**pageargs']
                cached = False
            buffered = filtered = False
        if args is None:
            args = ['context']
        else:
            args = [a for a in ['context'] + args]
            
        self.write_render_callable(pagetag or node, name, args, buffered, filtered, cached)
        
        if defs is not None:
            for node in defs:
                _GenerateRenderMethod(printer, compiler, node)
    
    identifiers = property(lambda self:self.identifier_stack[-1])
    
    def write_toplevel(self):
        """traverse a template structure for module-level directives and generate the
        start of module-level code."""
        inherit = []
        namespaces = {}
        module_code = []
        encoding =[None]

        self.compiler.pagetag = None
        
        class FindTopLevel(object):
            def visitInheritTag(s, node):
                inherit.append(node)
            def visitNamespaceTag(s, node):
                namespaces[node.name] = node
            def visitPageTag(s, node):
                self.compiler.pagetag = node
            def visitCode(s, node):
                if node.ismodule:
                    module_code.append(node)
            
        f = FindTopLevel()
        for n in self.node.nodes:
            n.accept_visitor(f)

        self.compiler.namespaces = namespaces

        module_ident = util.Set()
        for n in module_code:
            module_ident = module_ident.union(n.declared_identifiers())

        module_identifiers = _Identifiers()
        module_identifiers.declared = module_ident
        
        # module-level names, python code
        if not self.compiler.generate_unicode and self.compiler.source_encoding:
            self.printer.writeline("# -*- encoding:%s -*-" % self.compiler.source_encoding)
            
        self.printer.writeline("from mako import runtime, filters, cache")
        self.printer.writeline("UNDEFINED = runtime.UNDEFINED")
        self.printer.writeline("__M_dict_builtin = dict")
        self.printer.writeline("__M_locals_builtin = locals")
        self.printer.writeline("_magic_number = %s" % repr(MAGIC_NUMBER))
        self.printer.writeline("_modified_time = %s" % repr(time.time()))
        self.printer.writeline("_template_filename=%s" % repr(self.compiler.filename))
        self.printer.writeline("_template_uri=%s" % repr(self.compiler.uri))
        self.printer.writeline("_template_cache=cache.Cache(__name__, _modified_time)")
        self.printer.writeline("_source_encoding=%s" % repr(self.compiler.source_encoding))
        if self.compiler.imports:
            buf = ''
            for imp in self.compiler.imports:
                buf += imp + "\n"
                self.printer.writeline(imp)
            impcode = ast.PythonCode(buf, source='', lineno=0, pos=0, filename='template defined imports')
        else:
            impcode = None
        
        main_identifiers = module_identifiers.branch(self.node)
        module_identifiers.topleveldefs = module_identifiers.topleveldefs.union(main_identifiers.topleveldefs)
        [module_identifiers.declared.add(x) for x in ["UNDEFINED"]]
        if impcode:
            [module_identifiers.declared.add(x) for x in impcode.declared_identifiers]
            
        self.compiler.identifiers = module_identifiers
        self.printer.writeline("_exports = %s" % repr([n.name for n in main_identifiers.topleveldefs.values()]))
        self.printer.write("\n\n")

        if len(module_code):
            self.write_module_code(module_code)

        if len(inherit):
            self.write_namespaces(namespaces)
            self.write_inherit(inherit[-1])
        elif len(namespaces):
            self.write_namespaces(namespaces)

        return main_identifiers.topleveldefs.values()

    def write_render_callable(self, node, name, args, buffered, filtered, cached):
        """write a top-level render callable.
        
        this could be the main render() method or that of a top-level def."""
        self.printer.writelines(
            "def %s(%s):" % (name, ','.join(args)),
                "context.caller_stack._push_frame()",
                "try:"
        )
        if buffered or filtered or cached:
            self.printer.writeline("context._push_buffer()")
        
        self.identifier_stack.append(self.compiler.identifiers.branch(self.node))
        if not self.in_def and '**pageargs' in args:
            self.identifier_stack[-1].argument_declared.add('pageargs')

        if not self.in_def and (len(self.identifiers.locally_assigned) > 0 or len(self.identifiers.argument_declared)>0):
            self.printer.writeline("__M_locals = __M_dict_builtin(%s)" % ','.join(["%s=%s" % (x, x) for x in self.identifiers.argument_declared]))

        self.write_variable_declares(self.identifiers, toplevel=True)

        for n in self.node.nodes:
            n.accept_visitor(self)

        self.write_def_finish(self.node, buffered, filtered, cached)
        self.printer.writeline(None)
        self.printer.write("\n\n")
        if cached:
            self.write_cache_decorator(node, name, args, buffered, self.identifiers, toplevel=True)
            
    def write_module_code(self, module_code):
        """write module-level template code, i.e. that which is enclosed in <%! %> tags
        in the template."""
        for n in module_code:
            self.write_source_comment(n)
            self.printer.write_indented_block(n.text)

    def write_inherit(self, node):
        """write the module-level inheritance-determination callable."""
        self.printer.writelines(
            "def _mako_inherit(template, context):",
                "_mako_generate_namespaces(context)",
                "return runtime._inherit_from(context, %s, _template_uri)" % (node.parsed_attributes['file']),
                None
            )

    def write_namespaces(self, namespaces):
        """write the module-level namespace-generating callable."""
        self.printer.writelines(
            "def _mako_get_namespace(context, name):",
                "try:",
                    "return context.namespaces[(__name__, name)]",
                "except KeyError:",
                    "_mako_generate_namespaces(context)",
                "return context.namespaces[(__name__, name)]",
            None,None
            )
        self.printer.writeline("def _mako_generate_namespaces(context):")
        for node in namespaces.values():
            if node.attributes.has_key('import'):
                self.compiler.has_ns_imports = True
            self.write_source_comment(node)
            if len(node.nodes):
                self.printer.writeline("def make_namespace():")
                export = []
                identifiers = self.compiler.identifiers.branch(node)
                class NSDefVisitor(object):
                    def visitDefTag(s, node):
                        self.write_inline_def(node, identifiers, nested=False)
                        export.append(node.name)
                vis = NSDefVisitor()
                for n in node.nodes:
                    n.accept_visitor(vis)
                self.printer.writeline("return [%s]" % (','.join(export)))
                self.printer.writeline(None)
                callable_name = "make_namespace()"
            else:
                callable_name = "None"
            self.printer.writeline("ns = runtime.Namespace(%s, context._clean_inheritance_tokens(), templateuri=%s, callables=%s, calling_uri=_template_uri, module=%s)" % (repr(node.name), node.parsed_attributes.get('file', 'None'), callable_name, node.parsed_attributes.get('module', 'None')))
            if eval(node.attributes.get('inheritable', "False")):
                self.printer.writeline("context['self'].%s = ns" % (node.name))
            self.printer.writeline("context.namespaces[(__name__, %s)] = ns" % repr(node.name))
            self.printer.write("\n")
        if not len(namespaces):
            self.printer.writeline("pass")
        self.printer.writeline(None)
            
    def write_variable_declares(self, identifiers, toplevel=False, limit=None):
        """write variable declarations at the top of a function.
        
        the variable declarations are in the form of callable definitions for defs and/or
        name lookup within the function's context argument.  the names declared are based on the
        names that are referenced in the function body, which don't otherwise have any explicit
        assignment operation.  names that are assigned within the body are assumed to be 
        locally-scoped variables and are not separately declared.
        
        for def callable definitions, if the def is a top-level callable then a 
        'stub' callable is generated which wraps the current Context into a closure.  if the def
        is not top-level, it is fully rendered as a local closure."""
        
        # collection of all defs available to us in this scope
        comp_idents = dict([(c.name, c) for c in identifiers.defs])
        to_write = util.Set()
        
        # write "context.get()" for all variables we are going to need that arent in the namespace yet
        to_write = to_write.union(identifiers.undeclared)
        
        # write closure functions for closures that we define right here
        to_write = to_write.union(util.Set([c.name for c in identifiers.closuredefs.values()]))

        # remove identifiers that are declared in the argument signature of the callable
        to_write = to_write.difference(identifiers.argument_declared)

        # remove identifiers that we are going to assign to.  in this way we mimic Python's behavior,
        # i.e. assignment to a variable within a block means that variable is now a "locally declared" var,
        # which cannot be referenced beforehand.  
        to_write = to_write.difference(identifiers.locally_declared)
        
        # if a limiting set was sent, constraint to those items in that list
        # (this is used for the caching decorator)
        if limit is not None:
            to_write = to_write.intersection(limit)
        
        if toplevel and getattr(self.compiler, 'has_ns_imports', False):
            self.printer.writeline("_import_ns = {}")
            self.compiler.has_imports = True
            for ident, ns in self.compiler.namespaces.iteritems():
                if ns.attributes.has_key('import'):
                    self.printer.writeline("_mako_get_namespace(context, %s)._populate(_import_ns, %s)" % (repr(ident),  repr(re.split(r'\s*,\s*', ns.attributes['import']))))
                        
        for ident in to_write:
            if ident in comp_idents:
                comp = comp_idents[ident]
                if comp.is_root():
                    self.write_def_decl(comp, identifiers)
                else:
                    self.write_inline_def(comp, identifiers, nested=True)
            elif ident in self.compiler.namespaces:
                self.printer.writeline("%s = _mako_get_namespace(context, %s)" % (ident, repr(ident)))
            else:
                if getattr(self.compiler, 'has_ns_imports', False):
                    self.printer.writeline("%s = _import_ns.get(%s, context.get(%s, UNDEFINED))" % (ident, repr(ident), repr(ident)))
                else:
                    self.printer.writeline("%s = context.get(%s, UNDEFINED)" % (ident, repr(ident)))
        
        self.printer.writeline("__M_writer = context.writer()")
        
    def write_source_comment(self, node):
        """write a source comment containing the line number of the corresponding template line."""
        if self.last_source_line != node.lineno:
            self.printer.writeline("# SOURCE LINE %d" % node.lineno)
            self.last_source_line = node.lineno

    def write_def_decl(self, node, identifiers):
        """write a locally-available callable referencing a top-level def"""
        funcname = node.function_decl.funcname
        namedecls = node.function_decl.get_argument_expressions()
        nameargs = node.function_decl.get_argument_expressions(include_defaults=False)
        if not self.in_def and (len(self.identifiers.locally_assigned) > 0 or len(self.identifiers.argument_declared) > 0):
            nameargs.insert(0, 'context.locals_(__M_locals)')
        else:
            nameargs.insert(0, 'context')
        self.printer.writeline("def %s(%s):" % (funcname, ",".join(namedecls)))
        self.printer.writeline("return render_%s(%s)" % (funcname, ",".join(nameargs)))
        self.printer.writeline(None)
        
    def write_inline_def(self, node, identifiers, nested):
        """write a locally-available def callable inside an enclosing def."""
        namedecls = node.function_decl.get_argument_expressions()
        self.printer.writeline("def %s(%s):" % (node.name, ",".join(namedecls)))
        filtered = len(node.filter_args.args) > 0 
        buffered = eval(node.attributes.get('buffered', 'False'))
        cached = eval(node.attributes.get('cached', 'False'))
        self.printer.writelines(
            "context.caller_stack._push_frame()",
            "try:"
            )
        if buffered or filtered or cached:
            self.printer.writelines(
                "context._push_buffer()",
                )

        identifiers = identifiers.branch(node, nested=nested)

        self.write_variable_declares(identifiers)
        
        self.identifier_stack.append(identifiers)
        for n in node.nodes:
            n.accept_visitor(self)
        self.identifier_stack.pop()
        
        self.write_def_finish(node, buffered, filtered, cached)
        self.printer.writeline(None)
        if cached:
            self.write_cache_decorator(node, node.name, namedecls, False, identifiers, inline=True, toplevel=False)
            
    def write_def_finish(self, node, buffered, filtered, cached, callstack=True):
        """write the end section of a rendering function, either outermost or inline.
        
        this takes into account if the rendering function was filtered, buffered, etc.
        and closes the corresponding try: block if any, and writes code to retrieve captured content, 
        apply filters, send proper return value."""
        if not buffered and not cached and not filtered:
            self.printer.writeline("return ''")
            if callstack:
                self.printer.writelines(
                    "finally:",
                        "context.caller_stack._pop_frame()",
                    None
                )
                
        if buffered or filtered or cached:
            if buffered or cached:
                # in a caching scenario, don't try to get a writer
                # from the context after popping; assume the caching
                # implemenation might be using a context with no
                # extra buffers
                self.printer.writelines(
                    "finally:",
                        "__M_buf = context._pop_buffer()"
                )
            else:
                self.printer.writelines(
                    "finally:",
                        "__M_buf, __M_writer = context._pop_buffer_and_writer()"
                )
                
            if callstack:
                self.printer.writeline("context.caller_stack._pop_frame()")
                
            s = "__M_buf.getvalue()"
            if filtered:
                s = self.create_filter_callable(node.filter_args.args, s, False)
            self.printer.writeline(None)
            if buffered and not cached:
                s = self.create_filter_callable(self.compiler.buffer_filters, s, False)
            if buffered or cached:
                self.printer.writeline("return %s" % s)
            else:
                self.printer.writelines(
                    "__M_writer(%s)" % s,
                    "return ''"
                )

    def write_cache_decorator(self, node_or_pagetag, name, args, buffered, identifiers, inline=False, toplevel=False):
        """write a post-function decorator to replace a rendering callable with a cached version of itself."""
        self.printer.writeline("__M_%s = %s" % (name, name))
        cachekey = node_or_pagetag.parsed_attributes.get('cache_key', repr(name))
        cacheargs = {}
        for arg in (('cache_type', 'type'), ('cache_dir', 'data_dir'), ('cache_timeout', 'expiretime'), ('cache_url', 'url')):
            val = node_or_pagetag.parsed_attributes.get(arg[0], None)
            if val is not None:
                if arg[1] == 'expiretime':
                    cacheargs[arg[1]] = int(eval(val))
                else:
                    cacheargs[arg[1]] = val
            else:
                if self.compiler.pagetag is not None:
                    val = self.compiler.pagetag.parsed_attributes.get(arg[0], None)
                    if val is not None:
                        if arg[1] == 'expiretime':
                            cacheargs[arg[1]] == int(eval(val))
                        else:
                            cacheargs[arg[1]] = val
        
        self.printer.writeline("def %s(%s):" % (name, ','.join(args)))
        
        # form "arg1, arg2, arg3=arg3, arg4=arg4", etc.
        pass_args = [ '=' in a and "%s=%s" % ((a.split('=')[0],)*2) or a for a in args]

        self.write_variable_declares(identifiers, toplevel=toplevel, limit=node_or_pagetag.undeclared_identifiers())
        if buffered:
            s = "context.get('local').get_cached(%s, defname=%r, %screatefunc=lambda:__M_%s(%s))" % (cachekey, name, ''.join(["%s=%s, " % (k,v) for k, v in cacheargs.iteritems()]), name, ','.join(pass_args))
            # apply buffer_filters
            s = self.create_filter_callable(self.compiler.buffer_filters, s, False)
            self.printer.writelines("return " + s,None)
        else:
            self.printer.writelines(
                    "__M_writer(context.get('local').get_cached(%s, defname=%r, %screatefunc=lambda:__M_%s(%s)))" % (cachekey, name, ''.join(["%s=%s, " % (k,v) for k, v in cacheargs.iteritems()]), name, ','.join(pass_args)),
                    "return ''",
                None
            )

    def create_filter_callable(self, args, target, is_expression):
        """write a filter-applying expression based on the filters present in the given 
        filter names, adjusting for the global 'default' filter aliases as needed."""
        def locate_encode(name):
            if re.match(r'decode\..+', name):
                return "filters." + name
            else:
                return filters.DEFAULT_ESCAPES.get(name, name)
        
        if 'n' not in args:
            if is_expression:
                if self.compiler.pagetag:
                    args = self.compiler.pagetag.filter_args.args + args
                if self.compiler.default_filters:
                    args = self.compiler.default_filters + args
        for e in args:
            # if filter given as a function, get just the identifier portion
            if e == 'n':
                continue
            m = re.match(r'(.+?)(\(.*\))', e)
            if m:
                (ident, fargs) = m.group(1,2)
                f = locate_encode(ident)
                e = f + fargs
            else:
                x = e
                e = locate_encode(e)
                assert e is not None
            target = "%s(%s)" % (e, target)
        return target
        
    def visitExpression(self, node):
        self.write_source_comment(node)
        if len(node.escapes) or (self.compiler.pagetag is not None and len(self.compiler.pagetag.filter_args.args)) or len(self.compiler.default_filters):
            s = self.create_filter_callable(node.escapes_code.args, "%s" % node.text, True)
            self.printer.writeline("__M_writer(%s)" % s)
        else:
            self.printer.writeline("__M_writer(%s)" % node.text)
            
    def visitControlLine(self, node):
        if node.isend:
            self.printer.writeline(None)
        else:
            self.write_source_comment(node)
            self.printer.writeline(node.text)
    def visitText(self, node):
        self.write_source_comment(node)
        self.printer.writeline("__M_writer(%s)" % repr(node.content))
    def visitTextTag(self, node):
        filtered = len(node.filter_args.args) > 0
        if filtered:
            self.printer.writelines(
                "__M_writer = context._push_writer()",
                "try:",
            )
        for n in node.nodes:
            n.accept_visitor(self)
        if filtered:
            self.printer.writelines(
                "finally:",
                "__M_buf, __M_writer = context._pop_buffer_and_writer()",
                "__M_writer(%s)" % self.create_filter_callable(node.filter_args.args, "__M_buf.getvalue()", False),
                None
                )
        
    def visitCode(self, node):
        if not node.ismodule:
            self.write_source_comment(node)
            self.printer.write_indented_block(node.text)

            if not self.in_def and len(self.identifiers.locally_assigned) > 0:
                # if we are the "template" def, fudge locally declared/modified variables into the "__M_locals" dictionary,
                # which is used for def calls within the same template, to simulate "enclosing scope"
                self.printer.writeline('__M_locals.update(__M_dict_builtin([(__M_key, __M_locals_builtin()[__M_key]) for __M_key in [%s] if __M_key in __M_locals_builtin()]))' % ','.join([repr(x) for x in node.declared_identifiers()]))
                
    def visitIncludeTag(self, node):
        self.write_source_comment(node)
        args = node.attributes.get('args')
        if args:
            self.printer.writeline("runtime._include_file(context, %s, _template_uri, %s)" % (node.parsed_attributes['file'], args))
        else:
            self.printer.writeline("runtime._include_file(context, %s, _template_uri)" % (node.parsed_attributes['file']))
            
    def visitNamespaceTag(self, node):
        pass
            
    def visitDefTag(self, node):
        pass

    def visitCallNamespaceTag(self, node):
        # TODO: we can put namespace-specific checks here, such
        # as ensure the given namespace will be imported,
        # pre-import the namespace, etc.
        self.visitCallTag(node)
        
    def visitCallTag(self, node):
        self.printer.writeline("def ccall(caller):")
        export = ['body']
        callable_identifiers = self.identifiers.branch(node, nested=True)
        body_identifiers = callable_identifiers.branch(node, nested=False)
        # we want the 'caller' passed to ccall to be used for the body() function,
        # but for other non-body() <%def>s within <%call> we want the current caller off the call stack (if any)
        body_identifiers.add_declared('caller')
        
        self.identifier_stack.append(body_identifiers)
        class DefVisitor(object):
            def visitDefTag(s, node):
                self.write_inline_def(node, callable_identifiers, nested=False)
                export.append(node.name)
                # remove defs that are within the <%call> from the "closuredefs" defined
                # in the body, so they dont render twice
                if node.name in body_identifiers.closuredefs:
                    del body_identifiers.closuredefs[node.name]

        vis = DefVisitor()
        for n in node.nodes:
            n.accept_visitor(vis)
        self.identifier_stack.pop()
        
        bodyargs = node.body_decl.get_argument_expressions()    
        self.printer.writeline("def body(%s):" % ','.join(bodyargs))
        # TODO: figure out best way to specify buffering/nonbuffering (at call time would be better)
        buffered = False
        if buffered:
            self.printer.writelines(
                "context._push_buffer()",
                "try:"
            )
        self.write_variable_declares(body_identifiers)
        self.identifier_stack.append(body_identifiers)
        
        for n in node.nodes:
            n.accept_visitor(self)
        self.identifier_stack.pop()
        
        self.write_def_finish(node, buffered, False, False, callstack=False)
        self.printer.writelines(
            None,
            "return [%s]" % (','.join(export)),
            None
        )

        self.printer.writelines(
            # get local reference to current caller, if any
            "caller = context.caller_stack._get_caller()",
            # push on caller for nested call
            "context.caller_stack.nextcaller = runtime.Namespace('caller', context, callables=ccall(caller))",
            "try:")
        self.write_source_comment(node)
        self.printer.writelines(
                "__M_writer(%s)" % self.create_filter_callable([], node.expression, True),
            "finally:",
                "context.caller_stack.nextcaller = None",
            None
        )

class _Identifiers(object):
    """tracks the status of identifier names as template code is rendered."""
    def __init__(self, node=None, parent=None, nested=False):
        if parent is not None:
            # things that have already been declared in an enclosing namespace (i.e. names we can just use)
            self.declared = util.Set(parent.declared).union([c.name for c in parent.closuredefs.values()]).union(parent.locally_declared).union(parent.argument_declared)
            
            # if these identifiers correspond to a "nested" scope, it means whatever the 
            # parent identifiers had as undeclared will have been declared by that parent, 
            # and therefore we have them in our scope.
            if nested:
                self.declared = self.declared.union(parent.undeclared)
            
            # top level defs that are available
            self.topleveldefs = util.SetLikeDict(**parent.topleveldefs)
        else:
            self.declared = util.Set()
            self.topleveldefs = util.SetLikeDict()
        
        # things within this level that are referenced before they are declared (e.g. assigned to)
        self.undeclared = util.Set()
        
        # things that are declared locally.  some of these things could be in the "undeclared"
        # list as well if they are referenced before declared
        self.locally_declared = util.Set()
    
        # assignments made in explicit python blocks.  these will be propigated to 
        # the context of local def calls.
        self.locally_assigned = util.Set()
        
        # things that are declared in the argument signature of the def callable
        self.argument_declared = util.Set()
        
        # closure defs that are defined in this level
        self.closuredefs = util.SetLikeDict()
        
        self.node = node
        
        if node is not None:
            node.accept_visitor(self)
        
    def branch(self, node, **kwargs):
        """create a new Identifiers for a new Node, with this Identifiers as the parent."""
        return _Identifiers(node, self, **kwargs)
    
    defs = property(lambda self:util.Set(self.topleveldefs.union(self.closuredefs).values()))
    
    def __repr__(self):
        return "Identifiers(declared=%s, locally_declared=%s, undeclared=%s, topleveldefs=%s, closuredefs=%s, argumenetdeclared=%s)" % (repr(list(self.declared)), repr(list(self.locally_declared)), repr(list(self.undeclared)), repr([c.name for c in self.topleveldefs.values()]), repr([c.name for c in self.closuredefs.values()]), repr(self.argument_declared))
        
    def check_declared(self, node):
        """update the state of this Identifiers with the undeclared and declared identifiers of the given node."""
        for ident in node.undeclared_identifiers():
            if ident != 'context' and ident not in self.declared.union(self.locally_declared):
                self.undeclared.add(ident)
        for ident in node.declared_identifiers():
            self.locally_declared.add(ident)
    
    def add_declared(self, ident):
        self.declared.add(ident)
        if ident in self.undeclared:
            self.undeclared.remove(ident)
                        
    def visitExpression(self, node):
        self.check_declared(node)
    def visitControlLine(self, node):
        self.check_declared(node)
    def visitCode(self, node):
        if not node.ismodule:
            self.check_declared(node)
            self.locally_assigned = self.locally_assigned.union(node.declared_identifiers())
    def visitDefTag(self, node):
        if node.is_root():
            self.topleveldefs[node.name] = node
        elif node is not self.node:
            self.closuredefs[node.name] = node
        for ident in node.undeclared_identifiers():
            if ident != 'context' and ident not in self.declared.union(self.locally_declared):
                self.undeclared.add(ident)
        # visit defs only one level deep
        if node is self.node:
            for ident in node.declared_identifiers():
                self.argument_declared.add(ident)
            for n in node.nodes:
                n.accept_visitor(self)
    def visitIncludeTag(self, node):
        self.check_declared(node)
    def visitPageTag(self, node):
        for ident in node.declared_identifiers():
            self.argument_declared.add(ident)
        self.check_declared(node)
    
    def visitCallNamespaceTag(self, node):
        self.visitCallTag(node)
        
    def visitCallTag(self, node):
        if node is self.node:
            for ident in node.undeclared_identifiers():
                if ident != 'context' and ident not in self.declared.union(self.locally_declared):
                    self.undeclared.add(ident)
            for ident in node.declared_identifiers():
                self.argument_declared.add(ident)
            for n in node.nodes:
                n.accept_visitor(self)
        else:
            for ident in node.undeclared_identifiers():
                if ident != 'context' and ident not in self.declared.union(self.locally_declared):
                    self.undeclared.add(ident)
                
