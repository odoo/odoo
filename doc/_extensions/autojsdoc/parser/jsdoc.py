# -*- coding: utf-8 -*-
import re

import collections

import pyjsdoc

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
        # param name and doc can be separated by - or :, strip it
        self.doc = self.doc.strip().lstrip('-:').lstrip()
        self.optional = False
        self.default = None
        # there may not be a space between the param name and the :, in which
        # case the : gets attached to the name, strip *again*
        # TODO: formal @param/@property parser to handle this crap properly once and for all
        self.name = self.name.strip().rstrip(':')
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

class CommentDoc(pyjsdoc.CommentDoc):
    namekey = object()
    is_constructor = False

    @property
    def name(self):
        return self[self.namekey] or self['name'] or self['guessed_name']
    def set_name(self, name):
        # not great...
        if name != '<exports>':
            self.parsed['guessed_name'] = name

    @property
    def is_private(self):
        return 'private' in self.parsed

    def to_dict(self):
        d = super(CommentDoc, self).to_dict()
        d['name'] = self.name
        return d

class PropertyDoc(CommentDoc):
    @classmethod
    def from_param(cls, s, sourcemodule=None):
        parsed = ParamDoc(s).to_dict()
        parsed['sourcemodule'] = sourcemodule
        return cls(parsed)

    @property
    def type(self):
        return self['type'].strip('{}')

    def to_dict(self):
        d = super(PropertyDoc, self).to_dict()
        d['type'] = self.type
        d['is_private'] = self.is_private
        return d

class InstanceDoc(CommentDoc):
    @property
    def cls(self):
        return self['cls']

    def to_dict(self):
        return dict(super(InstanceDoc, self).to_dict(), cls=self.cls)

class LiteralDoc(CommentDoc):
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
        d['value'] = self.value
        return d

class FunctionDoc(CommentDoc):
    type = 'Function'
    namekey = 'function'

    @property
    def is_constructor(self):
        return self.name == 'init'

    @property
    def params(self):
        tag_texts = self.get_as_list('param')
        if self.get('guessed_params') is None:
            return [ParamDoc(text) for text in tag_texts]
        else:
            param_dict = {}
            for text in tag_texts:
                param = ParamDoc(text)
                param_dict[param.name] = param
            return [param_dict.get(name) or ParamDoc('{} ' + name)
                    for name in self.get('guessed_params')]
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

    def to_dict(self):
        d = super(FunctionDoc, self).to_dict()
        d['name'] = self.name
        d['params'] = [param.to_dict() for param in self.params]
        d['return_val']=  self.return_val.to_dict()
        return d

class NSDoc(CommentDoc):
    namekey = 'namespace'
    def __init__(self, parsed_comment):
        super(NSDoc, self).__init__(parsed_comment)
        self.members = collections.OrderedDict()
    def add_member(self, name, member):
        """
        :type name: str
        :type member: CommentDoc
        """
        member.set_name(name)
        self.members[name] = member

    @property
    def properties(self):
        if self.get('property'):
            return [
                (p.name, p)
                for p in (
                    PropertyDoc.from_param(p, self['sourcemodule'])
                    for p in self.get_as_list('property')
                )
            ]
        return list(self.members.items()) or self['_members'] or []

    def has_property(self, name):
        return self.get_property(name) is not None

    def get_property(self, name):
        return next((p for n, p in self.properties if n == name), None)

    def to_dict(self):
        d = super(NSDoc, self).to_dict()
        d['properties'] = [(n, p.to_dict()) for n, p in self.properties]
        return d

class MixinDoc(NSDoc):
    namekey = 'mixin'

class ModuleDoc(NSDoc):
    namekey = 'module'
    def __init__(self, parsed_comment):
        super(ModuleDoc, self).__init__(parsed_comment)
        #: callbacks to run with the modules mapping once every module is resolved
        self._post_process = []

    def post_process(self, modules):
        for callback in self._post_process:
            callback(modules)

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

    @property
    def exports(self):
        """
        Returns the actual item exported from the AMD module, can be a
        namespace, a class, a function, an instance, ...
        """
        return self.get_property('<exports>')

    def to_dict(self):
        vars = super(ModuleDoc, self).to_dict()
        vars['dependencies'] = self.dependencies
        vars['exports'] = self.exports
        return vars

class ClassDoc(NSDoc):
    namekey = 'class'
    @property
    def constructor(self):
        return self.get_property('init')

    @property
    def superclass(self):
        return self['extends'] or self['base']

    def get_property(self, method_name):
        if method_name == 'extend':
            return FunctionDoc({
                'doc': 'Create subclass for %s' % self.name,
                'guessed_function': 'extend',
            })
        # FIXME: should ideally be a proxy namespace
        if method_name == 'prototype':
            return self
        return super(ClassDoc, self).get_property(method_name)

    @property
    def mixins(self):
        return self.get_as_list('mixes')

    def to_dict(self):
        d = super(ClassDoc, self).to_dict()
        d['mixins'] = self.mixins
        return d

class UnknownNS(NSDoc):
    def get_property(self, name):
        return super(UnknownNS, self).get_property(name) or \
           UnknownNS({'name': '{}.{}'.format(self.name, name)})

class Unknown(CommentDoc):
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

    @property
    def type(self):
        return "Unknown"

    def get_property(self, p):
        return Unknown(dict(self.parsed, source=self.name, name=p + '<'))

def parse_comments(comments, doctype=None):
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
    parsed = pyjsdoc.parse_comment(extract, u'')

    if doctype == 'FunctionExpression':
        doctype = FunctionDoc
    elif doctype == 'ObjectExpression' or doctype is None:
        doctype = guess

    if doctype is guess:
        return doctype(parsed)

    # in case a specific doctype is given, allow overriding it anyway
    return guess(parsed, default=doctype)

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
