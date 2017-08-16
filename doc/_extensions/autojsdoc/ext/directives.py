# -*- coding: utf-8 -*-
import abc
import contextlib
import fnmatch
import io


from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList
from sphinx import addnodes
from sphinx.ext.autodoc import members_set_option, bool_option, ALL

from autojsdoc.ext.extractor import read_js
from ..parser import jsdoc, types


@contextlib.contextmanager
def addto(parent, newnode):
    assert isinstance(newnode, nodes.Node), \
        "Expected newnode to be a Node, got %s" % (type(newnode))
    yield newnode
    parent.append(newnode)


def documenter_for(directive, modname, classname, doc):
    if isinstance(doc, jsdoc.FunctionDoc):
        return FunctionDocumenter(directive, modname, classname, doc)
    if isinstance(doc, jsdoc.ClassDoc):
        return ClassDocumenter(directive, modname, None, doc)
    if isinstance(doc, jsdoc.MixinDoc):
        return MixinDocumenter(directive, modname, None, doc)
    if isinstance(doc, (jsdoc.PropertyDoc, jsdoc.LiteralDoc)):
        return PropertyDocumenter(directive, modname, classname, doc)
    if isinstance(doc, jsdoc.InstanceDoc):
        return InstanceDocumenter(directive, modname, classname, doc)
    if isinstance(doc, jsdoc.Unknown):
        return UnknownDocumenter(directive, None, None, doc)
    if isinstance(doc, jsdoc.NSDoc):
        return NSDocumenter(directive, modname, None, doc)

    raise TypeError("No documenter for %s" % type(doc))
def doc_for(directive, modname, classname, doc):
    return documenter_for(directive, modname, classname, doc).generate()

def to_list(doc, source=None):
    return StringList([
        line.rstrip('\n')
        for line in io.StringIO(doc)
    ], source=source)
def automodule_bound(app, modules, symbols):
    class AutoModuleDirective(Directive):
        required_arguments = 1
        has_content = True
        option_spec = {
            'members': members_set_option,
            'undoc-members': bool_option,
            'private-members': bool_option,
            'undoc-matches': bool_option,
        }

        # self.state.nested_parse(string, offset, node) => parse context for sub-content (body which can contain RST data)
        # => needed for doc (converted?) and for actual directive body
        def run(self):
            modname = self.arguments[0].strip()

            # TODO: cache/memoize modules & symbols?
            if not modules:
                read_js(app, modules, symbols)

            mods = [
                (name, mod)
                for name, mod in modules.items()
                if fnmatch.fnmatch(name, modname)
            ]
            ret = []
            for name, mod in mods:
                if mod.is_private:
                    continue
                if name != modname and not (mod.doc or mod.exports):
                    # this module has no documentation, no exports and was
                    # not specifically requested through automodule -> skip
                    # unless requested
                    if not self.options.get('undoc-matches'):
                        continue
                modsource = mod['sourcefile']
                if modsource:
                    self.state.document.settings.env.note_dependency(modsource)
                # not sure what that's used for as normal xrefs are resolved using the id directly
                target = nodes.target('', '', ids=['module-' + name], ismod=True)
                self.state.document.note_explicit_target(target)

                documenter = ModuleDocumenter(self, None, None, mod)

                ret.append(target)
                ret.extend(documenter.generate())
            return ret

    return AutoModuleDirective
# FIXME: autoclass/automethod/autofunction/autons/automixin/... directive
class Documenter(object):
    objtype = None
    def __init__(self, directive, mod, classname, doc):
        self._directive = directive
        self._module = mod
        self._class = classname
        self._doc = doc
    def generate(self):
        """
        :rtype: List[nodes.Node]
        """
        objname = self._doc.name
        prefixed = (self._doc['sourcemodule'].name + '.' + objname) if self._doc['sourcemodule'] else None
        objtype = self.objtype
        assert objtype, '%s has no objtype' % type(self)
        root = addnodes.desc(domain='js', desctype=objtype, objtype=objtype)
        with addto(root, addnodes.desc_signature(
            module=self._module or '',
            fullname=objname,
        )) as s:
            s['class'] = self._class or ''

            s['ids'] = []
            if objname:
                s['ids'].append(objname)
            if prefixed:
                s['ids'].append(prefixed)

            if objtype:
                s += addnodes.desc_annotation(
                    objtype, objtype,
                    nodes.Text(' '),
                )

                env = self._directive.state.document.settings.env
                if objname:
                    env.domaindata['js']['objects'][objname] = (env.docname, objtype)
                if prefixed:
                    env.domaindata['js']['objects'][prefixed] = (env.docname, objtype)

            # TODO: linkcode_resolve
            s += self.make_signature()
        with addto(root, addnodes.desc_content()) as c:
            c += self.make_content()
        return [root]

    def make_signature(self):
        """
        :rtype: List[nodes.Node]
        """
        return [addnodes.desc_name(self._doc.name, self._doc.name)]

    @abc.abstractmethod
    def make_content(self):
        """
        :rtype: List[nodes.Node]
        """

class NSDocumenter(Documenter):
    objtype = 'namespace'
    def make_content(self):
        doc = self._doc
        ret = nodes.section()
        if doc.doc:
            self._directive.state.nested_parse(to_list(doc.doc), 0, ret)
        ret += self.document_properties()
        return ret.children

    def should_document(self, member, name):
        """
        :type member: jsdoc.CommentDoc
        :rtype: bool
        """
        options = self._directive.options

        members = options.get('members')
        if members is not ALL:
            # if a member is requested by name, it's always documented
            return name in members

        # ctor params are merged into the class doc
        if member.is_constructor:
            return False

        # only document "private" members if option is set
        if self.is_private(member, name) and not options.get('private-members'):
            return False

        # TODO: what if member doesn't have a description but has non-desc tags set?
        # TODO: add @public to force documenting symbol? => useful for implicit typedef
        return bool(member.doc or options.get('undoc-members'))

    def is_private(self, member, name):
        return member.is_private

    def document_properties(self):
        ret = nodes.section()
        # TODO: :member-order: [alphabetical | groupwise | bysource]
        for (n, p) in self._doc.properties:
            if not self.should_document(p, n):
                continue
            # FIXME: maybe should use property name as name inside?
            ret += doc_for(self._directive, self._module, None, p)
        return ret.children

class ModuleDocumenter(NSDocumenter):
    objtype = 'module'
    def make_content(self):
        doc = self._doc
        content = addnodes.desc_content()

        if doc.exports or doc.dependencies:
            with addto(content, nodes.field_list()) as fields:
                if doc.exports:
                    with addto(fields, nodes.field()) as field:
                        field += nodes.field_name('Exports', 'Exports')
                        with addto(field, nodes.field_body()) as body:
                            ref = doc['exports'] # warning: not the same as doc.exports
                            label = ref or '<anonymous>'
                            link = addnodes.pending_xref(
                                ref, nodes.paragraph(ref, label),
                                refdomain='js',
                                reftype='any',
                                reftarget=ref,
                            )
                            link['js:module'] = doc.name
                            body += link

                if doc.dependencies:
                    with addto(fields, nodes.field()) as field:
                        self.make_dependencies(field, doc)

        self._directive.state.nested_parse(self._directive.content, 0, content)

        if doc.doc:
            # FIXME: source offset
            self._directive.state.nested_parse(to_list(doc.doc, source=doc['sourcefile']), 0, content)

        content += self.document_properties()

        return content

    def make_dependencies(self, field, doc):
        field += nodes.field_name("Depends On", "Depends On")
        with addto(field, nodes.field_body()) as body:
            with addto(body, nodes.bullet_list()) as deps:
                for dep in sorted(doc.dependencies):
                    ref = addnodes.pending_xref(
                        dep, nodes.paragraph(dep, dep),
                        refdomain='js',
                        reftype='module',
                        reftarget=dep,
                    )
                    deps += nodes.list_item(dep, ref)

    def should_document(self, member, name):
        # member can be Nothing?
        if not member:
            return False
        modname = getattr(member['sourcemodule'], 'name', None)
        doc = self._doc

        # always document exported symbol (regardless undoc, private, ...)
        # otherwise things become... somewhat odd
        if name == doc['exports']:
            return True

        # if doc['exports'] the module is exporting a "named" item which
        # does not need to be documented twice, if not doc['exports'] it's
        # exporting an anonymous item (e.g. object literal) which needs to
        # be documented on its own
        if name == '<exports>' and not doc['exports']:
            return True

        # TODO: :imported-members:
        # FIXME: *directly* re-exported "foreign symbols"?
        return (not modname or modname == doc.name) \
               and super(ModuleDocumenter, self).should_document(member, name)


class ClassDocumenter(NSDocumenter):
    objtype = 'class'
    def make_signature(self):
        sig = super(ClassDocumenter, self).make_signature()
        sig.append(self.make_parameters())
        return sig

    def make_parameters(self):
        params = addnodes.desc_parameterlist('', '')
        ctor = self._doc.constructor
        if ctor:
            params += make_desc_parameters(ctor.params)

        return params

    def make_content(self):
        doc = self._doc
        ret = nodes.section()
        if doc.superclass or doc.mixins:
            with addto(ret, nodes.field_list()) as fields:
                fields += self.make_super()
                fields += self.make_mixins()
                fields += self.make_params()

        if doc.doc:
            self._directive.state.nested_parse(to_list(doc.doc), 0, ret)

        ret += self.document_properties()

        return ret.children

    def is_private(self, member, name):
        return name.startswith('_') or super(ClassDocumenter, self).is_private(member, name)

    def make_super(self):
        doc = self._doc
        if not doc.superclass:
            return []

        sup_link = addnodes.pending_xref(
            doc.superclass.name, nodes.paragraph(doc.superclass.name, doc.superclass.name),
            refdomain='js', reftype='class', reftarget=doc.superclass.name,
        )
        sup_link['js:module'] = doc.superclass['sourcemodule'].name
        return nodes.field(
            '',
            nodes.field_name("Extends", "Extends"),
            nodes.field_body(doc.superclass.name, sup_link),
        )


    def make_mixins(self):
        doc = self._doc
        if not doc.mixins:
            return []

        ret = nodes.field('', nodes.field_name("Mixes", "Mixes"))
        with addto(ret, nodes.field_body()) as body:
            with addto(body, nodes.bullet_list()) as mixins:
                for mixin in sorted(doc.mixins, key=lambda m: m.name):
                    mixin_link = addnodes.pending_xref(
                        mixin.name, nodes.paragraph(mixin.name, mixin.name),
                        refdomain='js', reftype='mixin', reftarget=mixin.name
                    )
                    mixin_link['js:module'] = mixin['sourcemodule'].name
                    mixins += nodes.list_item('', mixin_link)
        return ret

    def make_params(self):
        ctor = self._doc.constructor
        if not (ctor and ctor.params):
            return []

        ret = nodes.field('', nodes.field_name('Parameters', 'Parameters'))
        check_parameters(self, ctor)
        with addto(ret, nodes.field_body()) as body,\
             addto(body, nodes.bullet_list()) as holder:
            holder += make_parameters(ctor.params, mod=self._module)
        return ret

class InstanceDocumenter(Documenter):
    objtype = 'object'
    def make_signature(self):
        cls = self._doc.cls
        ret = super(InstanceDocumenter, self).make_signature()
        if cls:
            super_ref = addnodes.pending_xref(
                cls.name, nodes.Text(cls.name, cls.name),
                refdomain='js', reftype='class', reftarget=cls.name
            )
            super_ref['js:module'] = cls['sourcemodule'].name
            ret.append(addnodes.desc_annotation(' instance of ', ' instance of '))
            ret.append(addnodes.desc_type(cls.name, '', super_ref))
        if not ret:
            return [addnodes.desc_name('???', '???')]
        return ret

    def make_content(self):
        ret = nodes.section()
        if self._doc.doc:
            self._directive.state.nested_parse(to_list(self._doc.doc), 0, ret)
            return ret.children
        return ret.children

class FunctionDocumenter(Documenter):
    @property
    def objtype(self):
        return 'method' if self._class else 'function'
    def make_signature(self):
        ret = super(FunctionDocumenter, self).make_signature()
        with addto(ret, addnodes.desc_parameterlist()) as params:
            params += make_desc_parameters(self._doc.params)
        retval = self._doc.return_val
        if retval.type or retval.doc:
            ret.append(addnodes.desc_returns(retval.type or '*', retval.type  or '*'))
        return ret

    def make_content(self):
        ret = nodes.section()
        doc = self._doc
        if doc.doc:
            self._directive.state.nested_parse(to_list(doc.doc), 0, ret)

        check_parameters(self, doc)

        params = doc.params
        rdoc = doc.return_val.doc
        rtype = doc.return_val.type
        if params or rtype or rdoc:
            with addto(ret, nodes.field_list()) as fields:
                if params:
                    with addto(fields, nodes.field()) as field:
                        field += nodes.field_name('Parameters', 'Parameters')
                        with addto(field, nodes.field_body()) as body,\
                             addto(body, nodes.bullet_list()) as holder:
                            holder.extend(make_parameters(params, mod=doc['sourcemodule'].name))
                if rdoc:
                    with addto(fields, nodes.field()) as field:
                        field += nodes.field_name("Returns", "Returns")
                        with addto(field, nodes.field_body()) as body,\
                             addto(body, nodes.paragraph()) as p:
                            p += nodes.inline(rdoc, rdoc)
                if rtype:
                    with addto(fields, nodes.field()) as field:
                        field += nodes.field_name("Return Type", "Return Type")
                        with addto(field, nodes.field_body()) as body, \
                             addto(body, nodes.paragraph()) as p:
                            p += make_types(rtype, mod=doc['sourcemodule'].name)
        return ret.children

def check_parameters(documenter, doc):
    """
    Check that all documented parameters match a formal parameter for the
    function. Documented params which don't match the actual function may be
    typos.
    """
    guessed = set(doc['guessed_params'] or [])
    if not guessed:
        return

    documented = {
        # param name can be of the form [foo.bar.baz=default]\ndescription
        jsdoc.ParamDoc(text).name.split('.')[0]
        for text in doc.get_as_list('param')
    }
    odd = documented - guessed
    if not odd:
        return

    app = documenter._directive.state.document.settings.env.app
    app.warn("Found documented params %s not in formal parameter list "
             "of function %s in module %s (%s)" % (
        ', '.join(odd),
        doc.name,
        documenter._module,
        doc['sourcemodule']['sourcefile'],
    ))

def make_desc_parameters(params):
    for p in params:
        # FIXME: extract sub-params to typedef (in body?)
        if '.' in p.name:
            continue

        node = addnodes.desc_parameter(p.name, p.name)
        if p.optional:
            node = addnodes.desc_optional('', '', node)
        yield node

def make_parameters(params, mod=None):
    for param in params:
        p = nodes.paragraph('', '', nodes.strong(param.name, param.name))
        if param.default is not None:
            p += nodes.Text('=', '=')
            p += nodes.emphasis(param.default, param.default)
        if param.type:
            p += nodes.Text(' (')
            p += make_types(param.type, mod=mod)
            p += nodes.Text(')')
        if param.doc:
            p += [
                nodes.Text(' -- '),
                nodes.inline(param.doc, param.doc)
            ]
        yield p


def _format_value(v):
    if v == '|':
        return nodes.emphasis(' or ', ' or ')
    if v == ',':
        return nodes.Text(', ', ', ')
    return nodes.Text(v, v)
def make_types(typespec, mod=None):
    # TODO: in closure notation {type=} => optional, do we care?
    def format_type(t):
        ref = addnodes.pending_xref(
            t, addnodes.literal_emphasis(t, t),
            refdomain='js', reftype='class', reftarget=t,
        )
        if mod:
            ref['js:module'] = mod
        return ref

    try:
        return types.iterate(
            types.parse(typespec),
            format_type,
            _format_value
        )
    except ValueError as e:
        raise ValueError("%s in '%s'" % (e, typespec))


class MixinDocumenter(NSDocumenter):
    objtype = 'mixin'

# FIXME: add typedef support

class PropertyDocumenter(Documenter):
    objtype = 'attribute'
    def make_signature(self):
        ret = super(PropertyDocumenter, self).make_signature()
        proptype = self._doc.type
        if proptype:
            typeref = addnodes.pending_xref(
                proptype, nodes.Text(proptype, proptype),
                refdomain='js', reftype='class', reftarget=proptype
            )
            typeref['js:module'] = self._doc['sourcemodule'].name
            ret.append(nodes.Text(' '))
            ret.append(typeref)
        return ret

    def make_content(self):
        doc = self._doc
        ret = nodes.section()
        if doc.doc:
            self._directive.state.nested_parse(to_list(doc.doc), 0, ret)
        return ret.children

class UnknownDocumenter(Documenter):
    objtype = 'unknown'
    def make_content(self):
        return []
