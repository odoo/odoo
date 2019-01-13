# -*- coding: utf-8 -*-
import abc
import collections
import contextlib
import fnmatch
import io
import re

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList
from sphinx import addnodes
from sphinx.ext.autodoc import members_set_option, bool_option, ALL

from autojsdoc.ext.extractor import read_js
from ..parser import jsdoc, types

class DocumenterError(Exception): pass

@contextlib.contextmanager
def addto(parent, newnode):
    assert isinstance(newnode, nodes.Node), \
        "Expected newnode to be a Node, got %s" % (type(newnode))
    yield newnode
    parent.append(newnode)


def documenter_for(directive, doc):
    if isinstance(doc, jsdoc.FunctionDoc):
        return FunctionDocumenter(directive, doc)
    if isinstance(doc, jsdoc.ClassDoc):
        return ClassDocumenter(directive, doc)
    if isinstance(doc, jsdoc.MixinDoc):
        return MixinDocumenter(directive, doc)
    if isinstance(doc, (jsdoc.PropertyDoc, jsdoc.LiteralDoc)):
        return PropertyDocumenter(directive, doc)
    if isinstance(doc, jsdoc.InstanceDoc):
        return InstanceDocumenter(directive, doc)
    if isinstance(doc, jsdoc.Unknown):
        return UnknownDocumenter(directive, doc)
    if isinstance(doc, jsdoc.NSDoc):
        return NSDocumenter(directive, doc)

    raise TypeError("No documenter for %s" % type(doc))

def to_list(doc, source=None):
    return StringList([
        line.rstrip('\n')
        for line in io.StringIO(doc)
    ], source=source)

DIRECTIVE_OPTIONS = {
    'members': members_set_option,
    'undoc-members': bool_option,
    'private-members': bool_option,
    'undoc-matches': bool_option,
}
def automodule_bound(app, modules):
    class AutoModuleDirective(Directive):
        required_arguments = 1
        has_content = True
        option_spec = DIRECTIVE_OPTIONS

        # self.state.nested_parse(string, offset, node) => parse context for sub-content (body which can contain RST data)
        # => needed for doc (converted?) and for actual directive body
        def run(self):
            self.env = self.state.document.settings.env
            modname = self.arguments[0].strip()

            # TODO: cache/memoize modules & symbols?
            if not modules:
                read_js(app, modules)

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
                    self.env.note_dependency(modsource)
                # not sure what that's used for as normal xrefs are resolved using the id directly
                target = nodes.target('', '', ids=['module-' + name], ismod=True)
                self.state.document.note_explicit_target(target)

                documenter = ModuleDocumenter(self, mod)

                ret.append(target)
                ret.extend(documenter.generate())
            return ret

    return AutoModuleDirective

def autodirective_bound(app, modules):
    documenters = {
        'js:autoclass': ClassDocumenter,
        'js:autonamespace': NSDocumenter,
        'js:autofunction': FunctionDocumenter,
        'js:automixin': MixinDocumenter,
    }
    class AutoDirective(Directive):
        required_arguments = 1
        has_content = True
        option_spec = DIRECTIVE_OPTIONS

        def run(self):
            self.env = self.state.document.settings.env

            objname = self.arguments[0].strip()
            if not modules:
                read_js(app, modules)

            # build complete path to object
            path = self.env.temp_data.get('autojs:prefix', []) + objname.split('.')
            # look for module/object split
            for i in range(1, len(path)):
                modname, objpath = '.'.join(path[:-i]), path[-i:]
                module = modules.get(modname)
                if module:
                    break
            else:
                raise Exception("Found no valid module in " + '.'.join(path))

            item = module
            # deref' namespaces until we reach the object we're looking for
            for k in objpath:
                item = item.get_property(k)

            docclass = documenters[self.name]
            return docclass(self, item).generate()

    return AutoDirective

class Documenter(object):
    objtype = None
    def __init__(self, directive, doc):
        self.directive = directive
        self.env = directive.env
        self.item = doc

    @property
    def modname(self):
        return self.env.temp_data.get('autojs:module', '')
    @property
    def classname(self):
        return self.env.temp_data.get('autojs:class', '')
    def generate(self, all_members=False):
        """
        :rtype: List[nodes.Node]
        """
        try:
            return self._generate(all_members=all_members)
        except Exception as e:
            raise DocumenterError("Failed to document %s" % self.item) from e
    def _generate(self, all_members=False):
        objname = self.item.name
        prefixed = (self.item['sourcemodule'].name + '.' + objname) if self.item['sourcemodule'] else None
        objtype = self.objtype
        assert objtype, '%s has no objtype' % type(self)
        root = addnodes.desc(domain='js', desctype=objtype, objtype=objtype)
        with addto(root, addnodes.desc_signature(
            module=self.modname or '',
            fullname=objname,
        )) as s:
            s['class'] = self.classname

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

                env = self.env
                if objname:
                    env.domaindata['js']['objects'][objname] = (env.docname, objtype)
                if prefixed:
                    env.domaindata['js']['objects'][prefixed] = (env.docname, objtype)

            # TODO: linkcode_resolve
            s += self.make_signature()
        with addto(root, addnodes.desc_content()) as c:
            # must be here otherwise nested_parse(self.content) will not have
            # the prefix set
            self.env.temp_data.setdefault('autojs:prefix', []).append(self.item.name)
            c += self.make_content(all_members=all_members)
            self.env.temp_data['autojs:prefix'].pop()
        return [root]

    def make_signature(self):
        """
        :rtype: List[nodes.Node]
        """
        return [addnodes.desc_name(self.item.name, self.item.name)]

    @abc.abstractmethod
    def make_content(self, all_members):
        """
        :rtype: List[nodes.Node]
        """

    def document_subtypes(self, subtypes):
        docs = []
        with with_mapping_value(self.directive.options, 'undoc-members', True):
            for cls in subtypes:
                docs += ClassDocumenter(self.directive, cls).generate(all_members=True)
        return docs


class NSDocumenter(Documenter):
    objtype = 'namespace'
    def make_content(self, all_members):
        doc = self.item
        ret = nodes.section()

        if doc.doc:
            self.directive.state.nested_parse(to_list(doc.doc), 0, ret)

        self.directive.state.nested_parse(self.directive.content, 0, ret)

        ret += self.document_properties(all_members)
        return ret.children

    def should_document(self, member, name, all_members):
        """
        :type member: jsdoc.CommentDoc
        :type name: str
        :type all_members: bool
        :rtype: bool
        """
        options = self.directive.options

        members = options.get('members') or []
        if not (all_members or members is ALL):
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

    def document_properties(self, all_members):
        ret = nodes.section()
        # TODO: :member-order: [alphabetical | groupwise | bysource]
        for (n, p) in self.item.properties:
            if not self.should_document(p, n, all_members):
                continue
            # FIXME: maybe should use property name as name inside?
            ret += documenter_for(self.directive, p).generate(all_members=True)
        return ret.children

_NONE = object()
@contextlib.contextmanager
def with_mapping_value(mapping, key, value, restore_to=_NONE):
    """ Sets ``key`` to ``value`` for the duration of the context.

    If ``restore_to`` is not provided, restores ``key``'s old value
    afterwards, removes it entirely if there was no value for ``key`` in the
    mapping.

    .. warning:: for defaultdict & similar mappings, may restore the default
                 value (depends how the collections' .get behaves)
    """
    if restore_to is _NONE:
        restore_to = mapping.get(key, _NONE)
    mapping[key] = value
    try:
        yield
    finally:
        if restore_to is _NONE:
            del mapping[key]
        else:
            mapping[key] = restore_to
class ModuleDocumenter(NSDocumenter):
    objtype = 'module'
    def document_properties(self, all_members):
        with with_mapping_value(self.env.temp_data, 'autojs:module', self.item.name, ''):
            return super(ModuleDocumenter, self).document_properties(all_members)

    def make_content(self, all_members):
        doc = self.item
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

        if doc.doc:
            # FIXME: source offset
            self.directive.state.nested_parse(to_list(doc.doc, source=doc['sourcefile']), 0, content)

        self.directive.state.nested_parse(self.directive.content, 0, content)

        content += self.document_properties(all_members)

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

    def should_document(self, member, name, all_members):
        # member can be Nothing?
        if not member:
            return False
        modname = getattr(member['sourcemodule'], 'name', None)
        doc = self.item

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
               and super(ModuleDocumenter, self).should_document(member, name, all_members)


class ClassDocumenter(NSDocumenter):
    objtype = 'class'

    def document_properties(self, all_members):
        with with_mapping_value(self.env.temp_data, 'autojs:class', self.item.name, ''):
            return super(ClassDocumenter, self).document_properties(all_members)

    def make_signature(self):
        sig = super(ClassDocumenter, self).make_signature()
        sig.append(self.make_parameters())
        return sig

    def make_parameters(self):
        params = addnodes.desc_parameterlist('', '')
        ctor = self.item.constructor
        if ctor:
            params += make_desc_parameters(ctor.params)

        return params

    def make_content(self, all_members):
        doc = self.item
        ret = nodes.section()

        ctor = self.item.constructor
        params = subtypes = []
        if ctor:
            check_parameters(self, ctor)
            params, subtypes = extract_subtypes(doc.name, ctor)

        fields = nodes.field_list()
        fields += self.make_super()
        fields += self.make_mixins()
        fields += self.make_params(params)
        if fields.children:
            ret += fields

        if doc.doc:
            self.directive.state.nested_parse(to_list(doc.doc), 0, ret)

        self.directive.state.nested_parse(self.directive.content, 0, ret)

        ret += self.document_properties(all_members)

        ret += self.document_subtypes(subtypes)

        return ret.children

    def is_private(self, member, name):
        return name.startswith('_') or super(ClassDocumenter, self).is_private(member, name)

    def make_super(self):
        doc = self.item
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
        doc = self.item
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

    def make_params(self, params):
        if not params:
            return []

        ret = nodes.field('', nodes.field_name('Parameters', 'Parameters'))
        with addto(ret, nodes.field_body()) as body,\
             addto(body, nodes.bullet_list()) as holder:
            holder += make_parameters(params, mod=self.modname)
        return ret

class InstanceDocumenter(Documenter):
    objtype = 'object'
    def make_signature(self):
        cls = self.item.cls
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

    def make_content(self, all_members):
        ret = nodes.section()

        if self.item.doc:
            self.directive.state.nested_parse(to_list(self.item.doc), 0, ret)

        self.directive.state.nested_parse(self.directive.content, 0, ret)

        return ret.children

class FunctionDocumenter(Documenter):
    @property
    def objtype(self):
        return 'method' if self.classname else 'function'
    def make_signature(self):
        ret = super(FunctionDocumenter, self).make_signature()
        with addto(ret, addnodes.desc_parameterlist()) as params:
            params += make_desc_parameters(self.item.params)
        retval = self.item.return_val
        if retval.type or retval.doc:
            ret.append(addnodes.desc_returns(retval.type or '*', retval.type  or '*'))
        return ret

    def make_content(self, all_members):
        ret = nodes.section()
        doc = self.item

        if doc.doc:
            self.directive.state.nested_parse(to_list(doc.doc), 0, ret)

        self.directive.state.nested_parse(self.directive.content, 0, ret)

        check_parameters(self, doc)

        params, subtypes = extract_subtypes(self.item.name, self.item)
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

        ret += self.document_subtypes(subtypes)

        return ret.children

def pascal_case_ify(name):
    """
    Uppercase first letter of ``name``, or any letter following an ``_``. In
    the latter case, also strips out the ``_``.

    => key_for becomes KeyFor
    => options becomes Options
    """
    return re.sub(r'(^|_)\w', lambda m: m.group(0)[-1].upper(), name)
def extract_subtypes(parent_name, doc):
    """ Extracts composite parameters (a.b) into sub-types for the parent
    parameter, swaps the parent's type from whatever it is to the extracted
    one, and returns the extracted type for inclusion into the parent.

    :arg parent_name: name of the containing symbol (function, class), will
                      be used to compose subtype names
    :type parent_name: str
    :type doc: FunctionDoc
    :rtype: (List[ParamDoc], List[ClassDoc])
    """
    # map of {param_name: [ParamDoc]} (from complete doc)
    subparams = collections.defaultdict(list)
    for p in map(jsdoc.ParamDoc, doc.get_as_list('param')):
        pair = p.name.split('.', 1)
        if len(pair) == 2:
            k, p.name = pair # remove prefix from param name
            subparams[k].append(p)

    # keep original params order as that's the order of formal parameters in
    # the function signature
    params = collections.OrderedDict((p.name, p) for p in doc.params)
    subtypes = []
    # now we can use the subparams map to extract "compound" parameter types
    # and swap the new type for the original param's type
    for param_name, subs in subparams.items():
        typename = '%s%s' % (
            pascal_case_ify(parent_name),
            pascal_case_ify(param_name),
        )
        param = params[param_name]
        param.type = typename
        subtypes.append(jsdoc.ClassDoc({
            'name': typename,
            'doc': param.doc,
            '_members': [
                # TODO: add default value
                (sub.name, jsdoc.PropertyDoc(dict(sub.to_dict(), sourcemodule=doc['sourcemodule'])))
                for sub in subs
            ],
            'sourcemodule': doc['sourcemodule'],
        }))
    return params.values(), subtypes

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

    app = documenter.directive.env.app
    app.warn("Found documented params %s not in formal parameter list "
             "of function %s in module %s (%s)" % (
        ', '.join(odd),
        doc.name,
        documenter.modname,
        doc['sourcemodule']['sourcefile'],
    ))

def make_desc_parameters(params):
    for p in params:
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

class PropertyDocumenter(Documenter):
    objtype = 'attribute'
    def make_signature(self):
        ret = super(PropertyDocumenter, self).make_signature()
        proptype = self.item.type
        if proptype:
            typeref = addnodes.pending_xref(
                proptype, nodes.Text(proptype, proptype),
                refdomain='js', reftype='class', reftarget=proptype
            )
            typeref['js:module'] = self.item['sourcemodule'].name
            ret.append(nodes.Text(' '))
            ret.append(typeref)
        return ret

    def make_content(self, all_members):
        doc = self.item
        ret = nodes.section()

        self.directive.state.nested_parse(self.directive.content, 0, ret)

        if doc.doc:
            self.directive.state.nested_parse(to_list(doc.doc), 0, ret)
        return ret.children

class UnknownDocumenter(Documenter):
    objtype = 'unknown'
    def make_content(self, all_members):
        return []
