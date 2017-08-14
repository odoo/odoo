# -*- coding: utf-8 -*-
import re

import collections

import jinja2
import pyjsdoc
from pyjsdoc import (
    CommentDoc,
    parse_comment,
)

def strip_stars(doc_comment):
    """
    Version of jsdoc.strip_stars which always removes 1 space after * if
    one is available.
    """
    return re.sub('\n\s*?\*[\t ]?', '\n', doc_comment[3:-2]).strip()

class ParamDoc(pyjsdoc.ParamDoc):
    """
    Replace ParamDoc because FunctionDoc doesn't properly handle optional
    params or default values (TODO: or compounds) if guessed_params is used

    => augment paramdoc with "required" and "default" items to clean up name
    """
    def __init__(self, text):
        super(ParamDoc, self).__init__(text)
        self.doc = self.doc.strip().lstrip('-:').lstrip()
        self.optional = False
        self.default = None
        self.name = self.name.strip()
        if self.name.startswith('['):
            self.name = self.name.strip('[]')
            self.optional = True
        if '=' in self.name:
            self.name, self.default = self.name.rsplit('=', 1)
    def to_dict(self):
        d = super(ParamDoc, self).to_dict()
        d['optional'] = self.optional
        d['default'] = self.default
        return d
pyjsdoc.ParamDoc = ParamDoc
class FunctionDoc(pyjsdoc.FunctionDoc):
    type = 'Function'
    def set_name(self, name):
        self.parsed['guessed_function'] = name

    @property
    def return_val(self):
        ret = self.get('return') or self.get('returns')
        type = self.get('type')
        if '{' in ret and '}' in ret:
            if not '}  ' in ret:
                # Ensure that name is empty
                ret = re.sub(r'\}\s*', '}  ', ret)
            return ParamDoc(ret)
        if ret and type:
            return ParamDoc('{%s}  %s' % (type, ret))
        return ParamDoc(ret)

    _template = """.. function:: {{ name }}
{% if doc %}

{{ doc | indent(4, true) }}

{% endif %}
{% for param in params %}
    {% if param.doc or not param.type %}
    :param {{ param.name|trim }}: {{ param.doc|indent(12) }}
    {% endif %}
    {% if param.type %}
    :type {{ param.name|trim }}: {{ param.type }}
    {% endif %}
{% endfor %}
{% if return_val %}
    {% if return_val.doc %}
    :returns: {{ return_val.doc }}
    {% endif %}
    {% if return_val.type %}
    :rtype: {{ return_val.type|indent(12) }}
    {% endif %}
{% endif %}
"""

CommentDoc.is_constructor = False
CommentDoc.is_private = property(lambda self: 'private' in self.parsed)
CommentDoc.as_text = lambda self: jinja2.Template(
    getattr(self, '_template', 'No template for {}'.format(type(self))),
    trim_blocks=True,
    lstrip_blocks=True,
).render(self.to_dict(), type=type)

class ModuleDoc(CommentDoc):
    """
    Represents a toplevel module
    """
    def __init__(self, parsed_comment):
        super(ModuleDoc, self).__init__(parsed_comment)
        #: callbacks to run with the modules mapping once every module is resolved
        self._post_process = []

    def post_process(self, modules):
        for callback in self._post_process:
            callback(modules)

    @property
    def name(self):
        return self['module']

    def set_name(self, name):
        self.parsed['module'] = name

    @property
    def module(self):
        return self # lol

    @property
    def dependencies(self):
        """
        Returns the immediate dependencies of a module (only those explicitly
        declared/used).
        """
        return self.get('dependency', None) or set()

    # FIXME: modules should be namespaces, exports should be a ref to whatever is being exported (or maybe direct doc if there is no name for it?)
    @property
    def exports(self):
        """
        Returns the actual item exported from the AMD module, can be a
        namespace, a class, a function, an instance, ...
        """
        return self['exports']

    def to_dict(self):
        vars = super(ModuleDoc, self).to_dict()
        vars['dependencies'] = self.dependencies
        vars['name'] = self.name
        vars['exports'] = self.exports
        return vars

    _template = """
# Module: {{ name }}
{% if doc %}

{{ doc }}
{% endif %}
{%+ if dependencies %}
## Depends On
{% for dependency in dependencies %}
    {{ dependency }}
{% endfor %}
{% endif %}
{%+ if exports %}
## Exports
{{ exports.as_text() }}
{% endif %}
"""

class ClassDoc(pyjsdoc.ClassDoc):
    def set_name(self, name):
        # FIXME: actually need to decouple namespace propnames and namespace values
        # issue is if a class is created then added to a namespace and the
        # class name and NS keys are different, the class gets given the ns
        # key as name, which is problematic for e.g.
        #     var C = Class.extend({});
        #     var D = Class.extend({a_thing: C})
        # we don't actually want C to become a_thing.
        self.parsed['class'] = name
    def to_dict(self):
        d = super(ClassDoc, self).to_dict()
        d['mixins'] = self.mixins
        return d

    def add_method(self, method):
        if isinstance(method, FunctionDoc) and method.name == 'init':
            method.parsed['constructor'] = True
        super(ClassDoc, self).add_method(method)

    def get_method(self, method_name, default=None):
        if method_name == 'extend':
            return FunctionDoc({
                'doc': 'Create subclass for %s' % self.name,
                'guessed_function': 'extend',
            })
        # FIXME: should ideally be a proxy namespace
        if method_name == 'prototype':
            return self
        return super(ClassDoc, self).get_method(method_name, default)

    @property
    def mixins(self):
        return self.get_as_list('mixes')

    _template = """### {{ name or '<unnamed>' }} {% if extends %}(extends {{ extends.property or '<unnamed>' }}){% endif %}
{%+ if doc %}
{{ doc }}
{% endif %}
{%+ if mixins %}
#### Mixes
{% for mixin in mixins %}
    {{ mixin }}
{% endfor %}
{% endif %}

#### Methods
{% for m in method %}
.. function:: {{ m['name'] or m['guessed_name'] }}
{% if m['doc'] %}

{{ m['doc'] | indent(4, true) }}

{% endif %}
{% for param in m.params %}
    {% if param.doc or not param.type %}
    :param {{ param.name|trim }}: {{ param.doc|indent(12) }}
    {% endif %}
    {% if param.type %}
    :type {{ param.name|trim }}: {{ param.type }}
    {% endif %}
{% endfor %}
{% if m.return_val %}
    {% if m.return_val.doc %}
    :returns: {{ m.return_val.doc }}
    {% endif %}
    {% if m.return_val.type %}
    :rtype: {{ m.return_val.type|indent(12) }}
    {% endif %}
{% endif %}

{% endfor %}
"""

class PropertyDoc(pyjsdoc.CommentDoc):
    @classmethod
    def from_param(cls, s):
        return cls(ParamDoc(s).to_dict())

    @property
    def name(self):
        return self['guessed_name'] or self['name']

    def set_name(self, name):
        self.parsed['guessed_name'] = name

    @property
    def type(self):
        return self['type'].strip('{}')

    @property
    def is_private(self):
        return 'private' in self.parsed

    def to_dict(self):
        d = super(PropertyDoc, self).to_dict()
        d['name'] = self.name
        d['type'] = self.type
        d['is_private'] = self.is_private
        return d

class ObjectDoc(pyjsdoc.CommentDoc):
    def __init__(self, parsed_comment):
        super(ObjectDoc, self).__init__(parsed_comment)
        self.members = collections.OrderedDict()

    def set_name(self, name):
        self.parsed['name'] = name

    @classmethod
    def from_parsed(cls, parsed):
        if 'mixin' in parsed:
            return MixinDoc(parsed)
        return NSDoc(parsed)

    @property
    def is_mixin(self):
        return False

    @property
    def is_namespace(self):
        return False

    def add_member(self, name, member):
        self.members[name] = member

    @property
    def properties(self):
        if self.get('property'):
            return [
                (p.name, p)
                for p in map(
                    PropertyDoc.from_param,
                    self.get_as_list('property')
                )
            ]
        return self.members.items() or self['_members'] or []
    def has_property(self, name):
        return self.get_property(name) is not None
    def get_property(self, name):
        return next((p for n, p in self.properties if n == name), None)

    def to_dict(self):
        d = super(ObjectDoc, self).to_dict()
        d['properties'] = [(n, p.to_dict()) for n, p in self.properties]
        return d

    _template = """### {{ name }} ({{ nature }})
{%+ if properties %}
#### Properties:
{% for name, property in properties %}
.. attribute:: {{ name }} {% if property.type %}{{property.type}}{% endif %}

{% if property.doc %}
    {{ property.doc }}
{% endif %}
{% endfor %}
{% endif %}
"""

class NSDoc(ObjectDoc):
    @property
    def name(self):
        return self['name'] or '<Namespace>'
    @property
    def is_namespace(self):
        return True

    def to_dict(self):
        d = super(NSDoc, self).to_dict()
        d['nature'] = "Namespace"
        return d


class InstanceDoc(ObjectDoc):
    @property
    def name(self):
        return self['name']
    @property
    def cls(self):
        return self['cls']

class UnknownNS(NSDoc):
    def get_property(self, name):
        return super(UnknownNS, self).get_property(name) or \
           UnknownNS({'name': '{}.{}'.format(self.name, name)})

class MixinDoc(ObjectDoc):
    @property
    def name(self):
        return self['name'] or '<Mixin>'
    @property
    def is_mixin(self):
        return True

    def to_dict(self):
        d = super(MixinDoc, self).to_dict()
        d['nature'] = "Mixin"
        return d

class LiteralDoc(pyjsdoc.CommentDoc):
    @property
    def name(self):
        if self['name']:
            return '<literal %s: %s>' % (self['name'], self['value'])
        return '<literal %s>' % self['value']

    def set_name(self, name):
        self.parsed['name'] = name

    @property
    def type(self):
        if self['type']:
            return self['type']
        valtype = type(self['value'])
        if valtype is bool:
            return 'Boolean'
        elif valtype is float:
            return 'Number'
        elif valtype is type(u''):
            return 'String'
        return ''

    @property
    def value(self):
        return self['value']

    def to_dict(self):
        d = super(LiteralDoc, self).to_dict()
        d['type'] = self.type
        return d


class Unknown(pyjsdoc.CommentDoc):
    @classmethod
    def from_(cls, source):
        def builder(parsed):
            inst = cls(parsed)
            inst.parsed['source'] = source
            return inst
        return builder

    @property
    def name(self):
        return self['name'] + ' ' + self['source']

    def set_name(self, name):
        self.parsed['name'] = name

    @property
    def type(self):
        return "Unknown"

    def get_property(self, p):
        return Unknown(dict(self.parsed, source=self.name, name=p + '<'))

def parse_comments(comments, doctype):
    # find last comment which starts with a *
    docstring = next((
        c['value']
        for c in reversed(comments or [])
        if c['value'].startswith(u'*')
    ), None) or u""

    # \n prefix necessary otherwise parse_comment fails to take first
    # block comment parser strips delimiters, but strip_stars fails without
    # them
    extract = '\n' + strip_stars('/*' + docstring + '\n*/')
    parsed = parse_comment(extract, u'')

    if doctype is guess:
        return doctype(parsed)

    if not callable(doctype):
        doctype = NODETYPE_TO_DOCTYPE.get(doctype, PropertyDoc)

    # in case a specific doctype is given, allow overriding it anyway
    return guess(parsed, default=doctype)

NODETYPE_TO_DOCTYPE = {
    'FunctionExpression': FunctionDoc,
    'ObjectExpression': ObjectDoc.from_parsed,
}
def guess(parsed, default=NSDoc):
    if 'class' in parsed:
        return ClassDoc(parsed)
    if 'function' in parsed:
        return FunctionDoc(parsed)
    if 'mixin' in parsed:
        return MixinDoc(parsed)
    if 'namespace' in parsed:
        return NSDoc(parsed)
    if 'module' in parsed:
        return ModuleDoc(parsed)
    if 'type' in parsed:
        return PropertyDoc(parsed)

    return default(parsed)
