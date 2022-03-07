# -*- coding: utf-8 -*-
import logging
import os.path
import re
import traceback
import builtins
import token
import tokenize
import io

from markupsafe import Markup, escape
from collections.abc import Sized, Mapping
from itertools import count, chain
from textwrap import dedent, indent as _indent
from lxml import etree
from psycopg2.extensions import TransactionRollbackError

from odoo.tools import pycompat, freehash

_logger = logging.getLogger(__name__)

# same list as for `--dev-mode`
SUPPORTED_DEBUGGERS = ['pdb', 'ipdb', 'pudb', 'wdb']
token.QWEB = token.NT_OFFSET - 1
token.tok_name[token.QWEB] = 'QWEB'

####################################
###          qweb tools          ###
####################################

class QWebCodeFound(Exception):
    """
    Exception raised when a qweb compilation encounter dynamic content if the
    option `raise_on_code` is True.
    """

class QWebException(Exception):
    def __init__(self, message, qweb, options, error=None, template=None, path=None, code=None):
        self.error = error
        self.name = template
        self.code = code if options.get('dev_mode') else None
        self.path = path
        self.html = None
        if template is not None and path and ':' not in path:
            element = qweb._get_template(template, options)[0]
            nodes = element.getroottree().xpath(self.path)
            if nodes:
                node = nodes[0]
                node[:] = []
                node.text = None
                self.html = etree.tostring(node, encoding='unicode')
        self.stack = traceback.format_exc()

        self.message = message
        if self.error is not None:
            self.message = "%s\n%s: %s" % (self.message, self.error.__class__.__name__, self.error)
        if self.name is not None:
            self.message = "%s\nTemplate: %s" % (self.message, self.name)
        if self.path is not None:
            self.message = "%s\nPath: %s" % (self.message, self.path)
        if self.html is not None:
            self.message = "%s\nNode: %s" % (self.message, self.html)

        super(QWebException, self).__init__(message)

    def __str__(self):
        message = "%s\n%s\n%s" % (self.error, self.stack, self.message)
        if self.code is not None:
            message = "%s\nCompiled code:\n%s" % (message, self.code)
        return message

    def __repr__(self):
        return str(self)

class frozendict(dict):
    """ An implementation of an immutable dictionary. """
    def __delitem__(self, key):
        raise NotImplementedError("'__delitem__' not supported on frozendict")
    def __setitem__(self, key, val):
        raise NotImplementedError("'__setitem__' not supported on frozendict")
    def clear(self):
        raise NotImplementedError("'clear' not supported on frozendict")
    def pop(self, key, default=None):
        raise NotImplementedError("'pop' not supported on frozendict")
    def popitem(self):
        raise NotImplementedError("'popitem' not supported on frozendict")
    def setdefault(self, key, default=None):
        raise NotImplementedError("'setdefault' not supported on frozendict")
    def update(self, *args, **kwargs):
        raise NotImplementedError("'update' not supported on frozendict")
    def __hash__(self):
        return hash(frozenset((key, freehash(val)) for key, val in self.items()))

unsafe_eval = eval

_FORMAT_REGEX = re.compile(r'(?:#\{(.+?)\})|(?:\{\{(.+?)\}\})') # ( ruby-style )|(  jinja-style  )
_VARNAME_REGEX = re.compile(r'\W')


####################################
###             QWeb             ###
####################################


class QWeb(object):
    __slots__ = ()

    _void_elements = frozenset([
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'keygen',
        'link', 'menuitem', 'meta', 'param', 'source', 'track', 'wbr'])
    _name_gen = count()
    # _available_objects builtins is not security safe (it's dangerous), is overridden by ir_qweb to only expose the safe_eval builtins.
    _available_objects = {k: v for k, v in vars(builtins).items() if not k.startswith('_')}
    _allowed_keyword = ['False', 'None', 'True', 'and', 'as', 'elif', 'else', 'for', 'if', 'in', 'is', 'not', 'or']

    def _render(self, template, values=None, **options):
        """ render(template, values, **options)

        Render the template specified by the given name.

        :param template: template identifier, name or etree (see ``_get_template``)
        :param dict values: template values to be used for rendering
        :param options: used to compile the template (the dict available for the rendering is frozen)
            * ``load`` (function) overrides the load method (returns: (template, ref))

        :returns: str as Markup
        :rtype: markupsafe.Markup
        """
        if values and 0 in values:
            raise ValueError('values[0] should be unset when call the _render method and only set into the template.')

        render_template = self._compile(template, options)
        rendering = render_template(self, values or {})
        result = ''.join(rendering)

        return Markup(result)

    def _compile(self, template, options):
        """ Compile the given template into a rendering function (generator)::

            render(qweb, values)

        where ``qweb`` is a QWeb instance and ``values`` are the values to render.
        """
        if options is None:
            options = {}

        element, document, ref = self._get_template(template, options)
        if not ref:
            ref = element.get('t-name', str(document))

        # reference to get xml and etree (usually the template ID)
        options['ref'] = ref
        # str xml of the reference template used for compilation. Useful for debugging, dev mode and profiling.
        options['ref_xml'] = document if isinstance(document, str) else str(document, 'utf-8')

        _options = dict(options)
        options = frozendict(options)

        # Initial template value send to render method (not in the froozen dict because it may be
        # different from one render to another. Indeed, it may be the view ID or the key)
        _options['template'] = template
        # Root of the etree which will be processed during compilation.
        _options['root'] = element.getroottree()
        # Reference to the last node being compiled. It is mainly used for debugging and displaying
        # error messages.
        _options['last_path_node'] = None

        if not options.get('nsmap'):
            _options['nsmap'] = {}

        # generate code

        def_name = f"template_{ref}" if isinstance(ref, int) else "template"

        try:
            _options['_text_concat'] = []
            self._appendText("", _options) # To ensure the template function is a generator and doesn't become a regular function
            code_lines = ([f"def {def_name}(self, values, log):"] +
                self._compile_node(element, _options, 1) +
                self._flushText(_options, 1))
        except QWebException as e:
            raise e
        except QWebCodeFound as e:
            raise e
        except Exception as e:
            raise QWebException("Error when compiling xml template", self, options,
                error=e, template=template, path=_options.get('last_path_node'))
        try:
            code = '\n'.join(code_lines)
        except QWebException as e:
            raise e
        except Exception as e:
            code = '\n'.join(map(str, code_lines))
            raise QWebException("Error when compiling xml template", self, options,
                error=e, template=template, code=code)

        # compile code and defined default values

        try:
            # noinspection PyBroadException
            compiled = compile(code, f'<{def_name}>', 'exec')
            globals_dict = self._prepare_globals({}, options)
            globals_dict['__builtins__'] = globals_dict # So that unknown/unsafe builtins are never added.
            unsafe_eval(compiled, globals_dict)
            compiled_fn = globals_dict[def_name]
        except QWebException as e:
            raise e
        except Exception as e:
            raise QWebException("Error when compiling xml template", self, options,
                error=e, template=template, code=code)

        # return the wrapped function

        def render_template(self, values):
            try:
                log = {'last_path_node': None}
                values = self._prepare_values(values, options)
                yield from compiled_fn(self, values, log)
            except (QWebException, TransactionRollbackError) as e:
                raise e
            except Exception as e:
                raise QWebException("Error when render the template", self, options,
                    error=e, template=template, path=log.get('last_path_node'), code=code)

        return render_template

    def _get_template(self, template, options):
        """ Retrieve the given template, and return it as a tuple ``(etree,
        xml, ref)``, where ``element`` is an etree, ``document`` is the
        string document that contains ``element``, and ``ref`` if the uniq
        reference of the template (id, t-name or template).

        :param template: template identifier, name or etree
        :param options: used to compile the template (the dict available for
            the rendering is frozen)
            ``load`` (function) overrides the load method
        """
        ref = template
        if isinstance(template, etree._Element):
            element = template
            document = etree.tostring(template)
            return (element, document, template.get('t-name'))
        else:
            try:
                loaded = options.get('load', self._load)(template, options)
                if not loaded:
                    raise ValueError("Can not load template '%s'" % template)
                document, ref = loaded
            except QWebException as e:
                raise e
            except Exception as e:
                template = options.get('caller_template', template)
                raise QWebException("load could not load template", self, options, e, template)

        if document is None:
            raise QWebException("Template not found", self, options, template=template)

        if isinstance(document, etree._Element):
            element = document
            document = etree.tostring(document, encoding='utf-8')
        elif not document.strip().startswith('<') and os.path.exists(document):
            element = etree.parse(document).getroot()
        else:
            element = etree.fromstring(document)

        for node in element:
            if node.get('t-name') == str(template):
                return (node, document, ref)
        return (element, document, ref)

    def _load(self, template, options):
        """ Load a given template and return a tuple ``(xml, ref)``` """
        return (template, None)

    # values for running time

    def _prepare_values(self, values, options):
        """ Prepare the context that will sent to the compiled and evaluated
        function.

        :param values: template values to be used for rendering
        :param options: frozen dict of compilation parameters.
        """
        return values

    def _prepare_globals(self, globals_dict, options):
        """ Prepare the global context that will sent to eval the qweb generated
        code.

        :param globals_dict: template global values use in compiled code
        :param options: frozen dict of compilation parameters.
        """
        globals_dict['Sized'] = Sized
        globals_dict['Mapping'] = Mapping
        globals_dict['Markup'] = Markup
        globals_dict['escape'] = escape
        globals_dict['compile_options'] = options
        globals_dict.update(self._available_objects)
        return globals_dict

    # compute helpers

    def _appendText(self, text, options):
        """ Add an item (converts to a string) to the list.
            This will be concatenated and added during a call to the
            `_flushText` method. This makes it possible to return only one
            yield containing all the parts."""
        options['_text_concat'].append(self._compile_to_str(text))

    def _flushText(self, options, indent):
        """Concatenate all the textual chunks added by the `_appendText`
            method into a single yield."""
        text_concat = options['_text_concat']
        if text_concat:
            text = ''.join(text_concat)
            text_concat.clear()
            return [f"{'    ' * indent}yield {repr(text)}"]
        else:
            return []

    def _indent(self, code, indent):
        """Indent the code to respect the python syntax."""
        return _indent(code, '    ' * indent)

    def _make_name(self, prefix='var'):
        """Generates a unique name."""
        return f"{prefix}_{next(self._name_gen)}"

    def _compile_node(self, el, options, indent):
        """ Compile the given element into python code.

            The t-* attributes (directives) will be converted to a python instruction. If there
            are no t-* attributes, the element will be considered static.

            Directives are compiled using the order provided by the
            ``_directives_eval_order`` method (an create the
            ``options['iter_directives']`` iterator).
            For compilation, the directives supported are those with a
            compilation method ``_compile_directive_*``

        :return: list of string
        """
        # if tag don't have qweb attributes don't use directives
        if self._is_static_node(el, options):
            return self._compile_static_node(el, options, indent)

        if options.get('raise_on_code'):
            raise QWebCodeFound()

        path = options['root'].getpath(el)
        if options['last_path_node'] != path:
            options['last_path_node'] = path
            body = [self._indent(f'log["last_path_node"] = {repr(path)}', indent)]
        else:
            body = []

        # create an iterator on directives to compile in order
        options['iter_directives'] = iter(self._directives_eval_order() + [None])

        el.set('t-tag', el.tag)
        if not ({'t-out', 't-esc', 't-raw', 't-field'} & set(el.attrib)):
            el.set('t-content', 'True')

        return body + self._compile_directives(el, options, indent)

    def _compile_directives(self, el, options, indent):
        """ Compile the given element, following the directives given in the
        iterator ``options['iter_directives']`` create by `_compile_node``
        method.

        :return: list of code lines
        """

        if self._is_static_node(el, options):
            el.attrib.pop('t-tag', None)
            el.attrib.pop('t-content', None)
            return self._compile_static_node(el, options, indent)

        # compile the first directive present on the element
        for directive in options['iter_directives']:
            if ('t-' + directive) in el.attrib:
                return self._compile_directive(el, options, directive, indent)

        return []

    def _compile_format(self, expr):
        """ Parses the provided format string and compiles it to a single
        expression python, uses string with format method.
        Use format is faster to concat string and values.
        """
        text = ''
        values = []
        base_idx = 0
        for m in _FORMAT_REGEX.finditer(expr):
            literal = expr[base_idx:m.start()]
            if literal:
                text += literal.replace('{', '{{').replace("}", "}}")
            text += '{}'
            values.append(f'self._compile_to_str({self._compile_expr(m.group(1) or m.group(2))})')
            base_idx = m.end()
        # string past last regex match
        literal = expr[base_idx:]
        if literal:
            text += literal.replace('{', '{{').replace("}", "}}")

        code = repr(text)
        if values:
            code += f'.format({", ".join(values)})'
        return code

    def _compile_expr_tokens(self, tokens, allowed_keys, argument_names=None, raise_on_missing=False):
        """ Transform the list of token coming into a python instruction in
            textual form by adding the namepaces for the dynamic values.

            Example: `5 + a + b.c` to be `5 + values.get('a') + values['b'].c`
            Unknown values are considered to be None, but using `values['b']`
            gives a clear error message in cases where there is an attribute for
            example (have a `KeyError: 'b'`, instead of `AttributeError: 'NoneType'
            object has no attribute 'c'`).

            @returns str
        """
        # Finds and extracts the current "scope"'s "allowed values": values
        # which should not be accessed through the environment's namespace:
        # * the local variables of a lambda should be accessed directly e.g.
        #     lambda a: a + b should be compiled to lambda a: a + values['b'],
        #     since a is local to the lambda it has to be accessed directly
        #     but b needs to be accessed through the rendering environment
        # * similarly for a comprehensions [a + b for a in c] should be
        #     compiledto [a + values.get('b') for a in values.get('c')]
        # to avoid the risk of confusion between nested lambdas / comprehensions,
        # this is currently performed independently at each level of brackets
        # nesting (hence the function being recursive).
        index = 0
        open_bracket_index = -1
        bracket_depth = 0

        argument_name = '_arg_%s__'
        argument_names = argument_names or []

        while index < len(tokens):
            t = tokens[index]
            if t.exact_type in [token.LPAR, token.LSQB, token.LBRACE]:
                bracket_depth += 1
            if t.exact_type in [token.RPAR, token.RSQB, token.RBRACE]:
                bracket_depth -= 1
            elif bracket_depth == 0 and t.exact_type == token.NAME:
                string = t.string
                if string == 'lambda': # lambda => allowed values for the current bracket depth
                    i = index + 1
                    while i < len(tokens):
                        t = tokens[i]
                        if t.exact_type == token.NAME:
                            argument_names.append(t.string)
                        elif t.exact_type == token.COMMA:
                            pass
                        elif t.exact_type == token.COLON:
                            break
                        elif t.exact_type == token.EQUAL:
                            raise NotImplementedError('Lambda default values are not supported')
                        else:
                            raise NotImplementedError('This lambda code style is not implemented.')
                        i += 1
                elif string == 'for': # list comprehensions => allowed values for the current bracket depth
                    i = index + 1
                    while len(tokens) > i:
                        t = tokens[i]
                        if t.exact_type == token.NAME:
                            if t.string == 'in':
                                break
                            argument_names.append(t.string)
                        elif t.exact_type in [token.COMMA, token.LPAR, token.RPAR]:
                            pass
                        else:
                            raise NotImplementedError('This loop code style is not implemented.')
                        i += 1

            index += 1

        # Use bracket to nest structures.
        # Recursively processes the "sub-scopes", and replace their content with
        # a compiled node. During this recursive call we add to the allowed
        # values the values provided by the list comprehension, lambda, etc.,
        # previously extracted.
        index = 0
        open_bracket_index = -1
        bracket_depth = 0

        while index < len(tokens):
            t = tokens[index]
            string = t.string

            if t.exact_type in [token.LPAR, token.LSQB, token.LBRACE]:
                if bracket_depth == 0:
                    open_bracket_index = index
                bracket_depth += 1
            elif t.exact_type in [token.RPAR, token.RSQB, token.RBRACE]:
                bracket_depth -= 1
                if bracket_depth == 0:
                    code = self._compile_expr_tokens(
                        tokens[open_bracket_index + 1:index],
                        list(allowed_keys),
                        list(argument_names),
                        raise_on_missing,
                    )
                    code = tokens[open_bracket_index].string + code + t.string
                    tokens[open_bracket_index:index + 1] = [tokenize.TokenInfo(token.QWEB, code, tokens[open_bracket_index].start, t.end, '')]
                    index = open_bracket_index

            index += 1

        # The keys will be namespaced by values if they are not allowed. In
        # order to have a clear keyError message, this will be replaced by
        # values['key'] for certain cases (for example if an attribute is called
        # key.attrib, or an index key[0] ...)
        code = []
        index = 0
        pos = tokens and tokens[0].start # to keep indent when use expr on multi line
        while index < len(tokens):
            t = tokens[index]
            string = t.string

            if t.start[0] != pos[0]:
                pos = (t.start[0], 0)
            space = t.start[1] - pos[1]
            if space:
                code.append(' ' * space)
            pos = t.start

            if t.exact_type == token.NAME:
                if string == 'lambda': # lambda => allowed values
                    code.append('lambda ')
                    index += 1
                    while index < len(tokens):
                        t = tokens[index]
                        if t.exact_type == token.NAME and t.string in argument_names:
                            code.append(argument_name % t.string)
                        if t.exact_type in [token.COMMA, token.COLON]:
                            code.append(t.string)
                        if t.exact_type == token.COLON:
                            break
                        index += 1
                    if t.end[0] != pos[0]:
                        pos = (t.end[0], 0)
                    else:
                        pos = t.end
                elif string in argument_names:
                    code.append(argument_name % t.string)
                elif string in allowed_keys:
                    code.append(string)
                elif index + 1 < len(tokens) and tokens[index + 1].exact_type == token.EQUAL: # function kw
                    code.append(string)
                elif index > 0 and tokens[index - 1] and tokens[index - 1].exact_type == token.DOT:
                    code.append(string)
                elif raise_on_missing or index + 1 < len(tokens) and tokens[index + 1].exact_type in [token.DOT, token.LPAR, token.LSQB, 'qweb']:
                    # Should have values['product'].price to raise an error when get
                    # the 'product' value and not an 'NoneType' object has no
                    # attribute 'price' error.
                    code.append(f'values[{repr(string)}]')
                else:
                    # not assignation allowed, only getter
                    code.append(f'values.get({repr(string)})')
            elif t.type not in [tokenize.ENCODING, token.ENDMARKER, token.DEDENT]:
                code.append(string)

            if t.end[0] != pos[0]:
                pos = (t.end[0], 0)
            else:
                pos = t.end

            index += 1

        return ''.join(code)

    def _compile_expr(self, expr, raise_on_missing=False):
        """This method must be overridden by <ir.qweb> in order to compile the template."""
        raise NotImplementedError("Templates should use the ir.qweb compile method")

    def _compile_bool(self, attr, default=False):
        """Convert the statements as a boolean."""
        if attr:
            if attr is True:
                return True
            attr = attr.lower()
            if attr in ('false', '0'):
                return False
            elif attr in ('true', '1'):
                return True
        return bool(default)

    def _compile_to_str(self, expr):
        """ Generates a text value (an instance of text_type) from an arbitrary
            source.
        """
        return pycompat.to_text(expr)

    # order

    def _directives_eval_order(self):
        """ List all supported directives in the order in which they should be
        evaluated on a given element. For instance, a node bearing both
        ``foreach`` and ``if`` should see ``foreach`` executed before ``if`` aka
        .. code-block:: xml
            <el t-foreach="foo" t-as="bar" t-if="bar">
        should be equivalent to
        .. code-block:: xml
            <t t-foreach="foo" t-as="bar">
                <t t-if="bar">
                    <el>
        then this method should return ``['foreach', 'if']``.
        """
        return [
            'debug',
            'foreach',
            'if', 'elif', 'else',
            'field', 'esc', 'raw', 'out',
            'tag',
            'call',
            'set',
            'content',
        ]

    def _is_static_node(self, el, options):
        """ Test whether the given element is purely static, i.e. (there
        are no t-* attributes), does not require dynamic rendering for its
        attributes.
        """
        return el.tag != 't' and not any(att.startswith('t-') and att not in ['t-tag', 't-content'] for att in el.attrib)

    # compile

    def _compile_static_node(self, el, options, indent):
        """ Compile a purely static element into a list of string. """
        if not el.nsmap:
            unqualified_el_tag = el_tag = el.tag
            attrib = self._post_processing_att(el.tag, el.attrib, options)
        else:
            # Etree will remove the ns prefixes indirection by inlining the corresponding
            # nsmap definition into the tag attribute. Restore the tag and prefix here.
            unqualified_el_tag = etree.QName(el.tag).localname
            el_tag = unqualified_el_tag
            if el.prefix:
                el_tag = f'{el.prefix}:{el_tag}'

            attrib = {}
            # If `el` introduced new namespaces, write them as attribute by using the
            # `attrib` dict.
            for ns_prefix, ns_definition in set(el.nsmap.items()) - set(options['nsmap'].items()):
                if ns_prefix is None:
                    attrib['xmlns'] = ns_definition
                else:
                    attrib[f'xmlns:{ns_prefix}'] = ns_definition

            # Etree will also remove the ns prefixes indirection in the attributes. As we only have
            # the namespace definition, we'll use an nsmap where the keys are the definitions and
            # the values the prefixes in order to get back the right prefix and restore it.
            ns = chain(options['nsmap'].items(), el.nsmap.items())
            nsprefixmap = {v: k for k, v in ns}
            for key, value in el.attrib.items():
                attrib_qname = etree.QName(key)
                if attrib_qname.namespace:
                    attrib[f'{nsprefixmap[attrib_qname.namespace]}:{attrib_qname.localname}'] = value
                else:
                    attrib[key] = value

            attrib = self._post_processing_att(el.tag, attrib, options)

            # Update the dict of inherited namespaces before continuing the recursion. Note:
            # since `options['nsmap']` is a dict (and therefore mutable) and we do **not**
            # want changes done in deeper recursion to bevisible in earlier ones, we'll pass
            # a copy before continuing the recursion and restore the original afterwards.
            original_nsmap = dict(options['nsmap'])

        if unqualified_el_tag != 't':
            attributes = ''.join(f' {str(name)}="{str(escape(str(value)))}"'
                                for name, value in attrib.items() if value or isinstance(value, str))
            self._appendText(f'<{el_tag}{attributes}', options)
            if unqualified_el_tag in self._void_elements:
                self._appendText('/>', options)
            else:
                self._appendText('>', options)

        if el.nsmap:
            options['nsmap'].update(el.nsmap)
            body = self._compile_directive_content(el, options, indent)
            options['nsmap'] = original_nsmap
        else:
            body = self._compile_directive_content(el, options, indent)

        if unqualified_el_tag != 't':
            if unqualified_el_tag not in self._void_elements:
                self._appendText(f'</{el_tag}>', options)

        return body

    def _compile_attributes(self, options, indent):
        """Generates the part of the code that post-process the attributes
        (this is ``attrs`` in the compiled code) during rendering time.
        """
        # Use str(value) to change Markup into str and escape it, then use str
        # to avoid the escaping of the other html content.
        body = self._flushText(options, indent)
        body.append(self._indent(dedent("""
            attrs = self._post_processing_att(tagName, attrs, compile_options)
            for name, value in attrs.items():
                if value or isinstance(value, str):
                    yield f' {str(escape(str(name)))}="{str(escape(str(value)))}"'
        """).strip(), indent))
        return body

    def _compile_static_attributes(self, el, options, indent):
        """ Compile the static and dynamc attributes of the given element.

        We do not support namespaced dynamic attributes.
        """
        # Etree will also remove the ns prefixes indirection in the attributes. As we only have
        # the namespace definition, we'll use an nsmap where the keys are the definitions and
        # the values the prefixes in order to get back the right prefix and restore it.
        nsprefixmap = {v: k for k, v in chain(options['nsmap'].items(), el.nsmap.items())}

        code = []
        for key, value in el.attrib.items():
            if not key.startswith('t-'):
                attrib_qname = etree.QName(key)
                if attrib_qname.namespace:
                    key = f'{nsprefixmap[attrib_qname.namespace]}:{attrib_qname.localname}'
                code.append(self._indent(f'attrs[{repr(key)}] = {repr(value)}', indent))
        return code

    def _compile_dynamic_attributes(self, el, options, indent):
        """ Compile the dynamic attributes of the given element into a list
        string (this is adding elements to ``attrs`` in the compiled code).

        We do not support namespaced dynamic attributes.
        """
        code = []
        for name, value in el.attrib.items():

            if name.startswith('t-attf-'):
                code.append(self._indent(f"attrs[{repr(name[7:])}] = {self._compile_format(value)}", indent))
            elif name.startswith('t-att-'):
                code.append(self._indent(f"attrs[{repr(name[6:])}] = {self._compile_expr(value)}", indent))
            elif name == 't-att':
                code.append(self._indent(dedent(f"""
                    atts_value = {self._compile_expr(value)}
                    if isinstance(atts_value, dict):
                        attrs.update(atts_value)
                    elif isinstance(atts_value, (list, tuple)) and not isinstance(atts_value[0], (list, tuple)):
                        attrs.update([atts_value])
                    elif isinstance(atts_value, (list, tuple)):
                        attrs.update(dict(atts_value))
                    """), indent))
        return code

    def _compile_all_attributes(self, el, options, indent, attr_already_created=False):
        """ Compile the attributes (static and dynamic) of the given elements
        into a list of str.
        (this compiled The code will create the ``attrs`` in the compiled code).
        """
        code = []
        if any(name.startswith('t-att') or not name.startswith('t-') for name, value in el.attrib.items()):
            if not attr_already_created:
                attr_already_created = True
                code.append(self._indent("attrs = {}", indent))
            code.extend(self._compile_static_attributes(el, options, indent))
            code.extend(self._compile_dynamic_attributes(el, options, indent))
        if attr_already_created:
            code.append(self._indent(f"tagName = {repr(el.tag)}", indent))
            code.extend(self._compile_attributes(options, indent))
        return code

    def _compile_tag_open(self, el, options, indent, attr_already_created=False):
        """ Compile the opening tag of the given element into a list of string. """
        extra_attrib = {}
        if not el.nsmap:
            unqualified_el_tag = el_tag = el.tag
        else:
            # Etree will remove the ns prefixes indirection by inlining the corresponding
            # nsmap definition into the tag attribute. Restore the tag and prefix here.
            # Note: we do not support namespace dynamic attributes, we need a default URI
            # on the root and use attribute directive t-att="{'xmlns:example': value}".
            unqualified_el_tag = etree.QName(el.tag).localname
            el_tag = unqualified_el_tag
            if el.prefix:
                el_tag = f'{el.prefix}:{el_tag}'

            # If `el` introduced new namespaces, write them as attribute by using the
            # `extra_attrib` dict.
            for ns_prefix, ns_definition in set(el.nsmap.items()) - set(options['nsmap'].items()):
                if ns_prefix is None:
                    extra_attrib['xmlns'] = ns_definition
                else:
                    extra_attrib[f'xmlns:{ns_prefix}'] = ns_definition

        code = []
        if unqualified_el_tag != 't':
            attributes = ''.join(f' {str(name)}="{str(escape(self._compile_to_str(value)))}"'
                                for name, value in extra_attrib.items())
            self._appendText("<{}{}".format(el_tag, attributes), options)
            code.extend(self._compile_all_attributes(el, options, indent, attr_already_created))
            if unqualified_el_tag in self._void_elements:
                self._appendText('/>', options)
            else:
                self._appendText('>', options)

        return code

    def _compile_tag_close(self, el, options):
        """ Compile the closing tag of the given element into a list of string. """
        if not el.nsmap:
            unqualified_el_tag = el_tag = el.tag
        else:
            unqualified_el_tag = etree.QName(el.tag).localname
            el_tag = unqualified_el_tag
            if el.prefix:
                el_tag = f'{el.prefix}:{el_tag}'

        if unqualified_el_tag != 't' and el_tag not in self._void_elements:
            self._appendText(f'</{el_tag}>', options)
        return []

    # compile directives

    def _compile_directive(self, el, options, directive, indent):
        compile_handler = getattr(self, f"_compile_directive_{directive.replace('-', '_')}", None)
        return compile_handler(el, options, indent)

    def _compile_directive_debug(self, el, options, indent):
        """Compile `t-debug` expressions into a python code as a list of
        strings.

        The code will contains the call to the debugger chosen from the valid
        list.
        """
        debugger = el.attrib.pop('t-debug')
        code = []
        if options.get('dev_mode'):
            code.append(self._indent(f"self._debug_trace({repr(debugger)}, compile_options)", indent))
        else:
            _logger.warning("@t-debug in template is only available in qweb dev mode options")
        code.extend(self._compile_directives(el, options, indent))
        return code

    def _compile_directive_options(self, el, options, indent):
        """
        compile t-options and add to the dict the t-options-xxx values
        """
        varname = options.get('t_options_varname', 't_options')
        code = []
        dict_arg = []
        for key in list(el.attrib):
            if key.startswith('t-options-'):
                value = el.attrib.pop(key)
                option_name = key[10:]
                dict_arg.append(f'{repr(option_name)}:{self._compile_expr(value)}')

        t_options = el.attrib.pop('t-options', None)
        if t_options and dict_arg:
            code.append(self._indent(f"{varname} = {{**{self._compile_expr(t_options)}, {', '.join(dict_arg)}}}", indent))
        elif dict_arg:
            code.append(self._indent(f"{varname} = {{{', '.join(dict_arg)}}}", indent))
        elif t_options:
            code.append(self._indent(f"{varname} = {self._compile_expr(t_options)}", indent))

        return code

    def _compile_directive_tag(self, el, options, indent):
        """Compile the element tag into a python code as a list of strings.

        The code will contains the opening tag, namespace, static and dynamic
        attributes and closing tag.
        """
        el.attrib.pop('t-tag', None)

        code = self._compile_tag_open(el, options, indent, False)

        # Update the dict of inherited namespaces before continuing the recursion. Note:
        # since `options['nsmap']` is a dict (and therefore mutable) and we do **not**
        # want changes done in deeper recursion to bevisible in earlier ones, we'll pass
        # a copy before continuing the recursion and restore the original afterwards.
        if el.nsmap:
            code.extend(self._compile_directives(el, dict(options, nsmap=el.nsmap), indent))
        else:
            code.extend(self._compile_directives(el, options, indent))

        code.extend(self._compile_tag_close(el, options))

        return code

    def _compile_directive_set(self, el, options, indent):
        """Compile `t-set` expressions into a python code as a list of
        strings.

        There are 3 kinds of `t-set`:
        * `t-value` containing python code;
        * `t-valuef` containing strings to format;
        * whose value is the content of the tag (being Markup safe).

        The code will contain the assignment of the dynamically generated value.
        """
        varname = el.attrib.pop('t-set')
        code = self._flushText(options, indent)

        if 't-value' in el.attrib:
            if varname == '0':
                raise ValueError('t-set="0" should not contains t-value or t-valuef')
            expr = el.attrib.pop('t-value') or 'None'
            expr = self._compile_expr(expr)
        elif 't-valuef' in el.attrib:
            if varname == '0':
                raise ValueError('t-set="0" should not contains t-value or t-valuef')
            exprf = el.attrib.pop('t-valuef')
            expr = self._compile_format(exprf)
        else:
            # set the content as value
            def_name = f"qweb_t_set_{re.sub(_VARNAME_REGEX, '_', options['last_path_node'])}"
            content = self._compile_directive_content(el, options, indent + 1) + self._flushText(options, indent + 1)
            if content:
                code.append(self._indent(f"def {def_name}():", indent))
                code.extend(content)
                expr = f"Markup(''.join({def_name}()))"
            else:
                expr = "''"

        code.append(self._indent(f"values[{repr(varname)}] = {expr}", indent))
        return code

    def _compile_directive_content(self, el, options, indent):
        """Compiles the content of the element (is the technical `t-content`
        directive created by QWeb) into a python code as a list of
        strings.

        The code will contains the text content of the node or the compliled
        code from the recursive call of ``_compile_node``.
        """
        if el.text is not None:
            self._appendText(el.text, options)
        body = []
        if el.getchildren():
            for item in el:
                if isinstance(item, etree._Comment):
                    if self.env.context.get('preserve_comments'):
                        self._appendText("<!--%s-->" % item.text, options)
                else:
                    body.extend(self._compile_node(item, options, indent))
                # comments can also contains tail text
                if item.tail is not None:
                    self._appendText(item.tail, options)
        return body

    def _compile_directive_else(self, el, options, indent):
        """Compile `t-else` expressions into a python code as a list of strings.

        This method is linked with the `t-if` directive.
        The code will contain the compiled code of the element (without `else`
        python part).
        """
        if el.attrib.pop('t-else') == '_t_skip_else_':
            return []
        if not options.pop('t_if', None):
            raise ValueError("t-else directive must be preceded by t-if directive")
        compiled = self._compile_directives(el, options, indent)
        el.attrib['t-else'] = '_t_skip_else_'
        return compiled

    def _compile_directive_elif(self, el, options, indent):
        """Compile `t-elif` expressions into a python code as a list of strings.

        This method is linked with the `t-if` directive.
        The code will contain the compiled code of the element (without `else`
        python part).
        """
        _elif = el.attrib['t-elif']
        if _elif == '_t_skip_else_':
            el.attrib.pop('t-elif')
            return []
        if not options.pop('t_if', None):
            raise ValueError("t-elif directive must be preceded by t-if directive")
        compiled = self._compile_directive_if(el, options, indent)
        el.attrib['t-elif'] = '_t_skip_else_'
        return compiled

    def _compile_directive_if(self, el, options, indent):
        """Compile `t-if` expressions into a python code as a list of strings.

        The code will contain the condition `if`, `else` and `elif` part that
        wrap the rest of the compiled code of this element.
        """
        if 't-elif' in el.attrib:
            expr = el.attrib.pop('t-elif')
        else:
            expr = el.attrib.pop('t-if')

        code = self._flushText(options, indent)
        content_if = self._compile_directives(el, options, indent + 1) + self._flushText(options, indent + 1)

        orelse = []
        next_el = el.getnext()
        comments_to_remove = []
        while isinstance(next_el, etree._Comment):
            comments_to_remove.append(next_el)
            next_el = next_el.getnext()
        if next_el is not None and {'t-else', 't-elif'} & set(next_el.attrib):
            parent = el.getparent()
            for comment in comments_to_remove:
                parent.remove(comment)
            if el.tail and not el.tail.isspace():
                raise ValueError("Unexpected non-whitespace characters between t-if and t-else directives")
            el.tail = None
            orelse = self._compile_node(next_el, dict(options, t_if=True), indent + 1) + self._flushText(options, indent + 1)

        code.append(self._indent(f"if {self._compile_expr(expr)}:", indent))
        code.extend(content_if or [self._indent('pass', indent + 1)])
        if orelse:
            code.append(self._indent("else:", indent))
            code.extend(orelse)
        return code

    def _compile_directive_foreach(self, el, options, indent):
        """Compile `t-foreach` expressions into a python code as a list of
        strings.

        `t-as` is used to define the key name.
        `t-foreach` compiled value can be an iterable, an dictionary or a
        number.

        The code will contain loop `for` that wrap the rest of the compiled
        code of this element.
        Some key into values dictionary are create automatically:
            *_size, *_index, *_value, *_first, *_last, *_odd, *_even, *_parity
        """
        expr_foreach = el.attrib.pop('t-foreach')
        expr_as = el.attrib.pop('t-as')

        code = self._flushText(options, indent)
        content_foreach = self._compile_directives(el, options, indent + 1) + self._flushText(options, indent + 1)

        t_foreach = self._make_name('t_foreach')
        size = self._make_name('size')
        has_value = self._make_name('has_value')

        if expr_foreach.isdigit():
            code.append(self._indent(dedent(f"""
                values[{repr(expr_as + '_size')}] = {size} = {int(expr_foreach)}
                {t_foreach} = range({size})
                {has_value} = False
            """).strip(), indent))
        else:
            code.append(self._indent(dedent(f"""
                {t_foreach} = {self._compile_expr(expr_foreach)} or []
                if isinstance({t_foreach}, Sized):
                    values[{repr(expr_as + '_size')}] = {size} = len({t_foreach})
                elif ({t_foreach}).__class__ == int:
                    values[{repr(expr_as + '_size')}] = {size} = {t_foreach}
                    {t_foreach} = range({size})
                else:
                    {size} = None
                {has_value} = False
                if isinstance({t_foreach}, Mapping):
                    {t_foreach} = {t_foreach}.items()
                    {has_value} = True
            """).strip(), indent))

        code.append(self._indent(dedent(f"""
                for index, item in enumerate({t_foreach}):
                    values[{repr(expr_as + '_index')}] = index
                    if {has_value}:
                        values[{repr(expr_as)}], values[{repr(expr_as + '_value')}] = item
                    else:
                        values[{repr(expr_as)}] = values[{repr(expr_as + '_value')}] = item
                    values[{repr(expr_as + '_first')}] = values[{repr(expr_as + '_index')}] == 0
                    if {size} is not None:
                        values[{repr(expr_as + '_last')}] = index + 1 == {size}
                    values[{repr(expr_as + '_odd')}] = index % 2
                    values[{repr(expr_as + '_even')}] = not values[{repr(expr_as + '_odd')}]
                    values[{repr(expr_as + '_parity')}] = 'odd' if values[{repr(expr_as + '_odd')}] else 'even'
            """), indent))

        code.append(self._indent(f'log["last_path_node"] = {repr(options["root"].getpath(el))} ', indent + 1))
        code.extend(content_foreach or self._indent('continue', indent + 1))

        return code

    def _compile_directive_out(self, el, options, indent):
        """Compile `t-out` expressions into a python code as a list of
        strings.

        The output can have some rendering option with `t-options-widget` or
        `t-options={'widget': ...}. The compiled code will call ``_get_widget``
        method at rendering time.

        The code will contain evalution and rendering of the compiled value. If
        the compiled value is None or False, the tag is not added to the render
        (Except if the widget forces rendering or there is default content.).
        """
        ttype = 't-out'
        expr = el.attrib.pop('t-out', None)
        if expr is None:
            # deprecated use.
            ttype = 't-esc'
            expr = el.attrib.pop('t-esc', None)
            if expr is None:
                ttype = 't-raw'
                expr = el.attrib.pop('t-raw')

        code = self._flushText(options, indent)
        options['t_options_varname'] = 't_out_t_options'
        code_options = self._compile_directive(el, options, 'options', indent)
        code.extend(code_options)

        if expr == "0":
            if code_options:
                code.append(self._indent("content = Markup(''.join(values.get('0', [])))", indent))
            else:
                code.extend(self._compile_tag_open(el, options, indent))
                code.extend(self._flushText(options, indent))
                code.append(self._indent("yield from values.get('0', [])", indent))
                code.extend(self._compile_tag_close(el, options))
                return code
        else:
            code.append(self._indent(f"content = {self._compile_expr(expr)}", indent))

        if code_options:
            code.append(self._indent(f"attrs, content, force_display = self._get_widget(content, {repr(expr)}, {repr(el.tag)}, t_out_t_options, compile_options, values)", indent))
        else:
            code.append(self._indent("force_display = None", indent))

            if ttype == 't-raw':
                # deprecated use.
                code.append(self._indent(dedent("""
                    if content is not None and content is not False:
                        content = Markup(content)
                """), indent))

        code.extend(self._compile_widget_value(el, options, indent, without_attributes=not code_options))
        return code

    def _compile_directive_esc(self, el, options, indent):
        # deprecated use.
        if options.get('dev_mode'):
            _logger.warning(
                "Found deprecated directive @t-esc=%r in template %r. Replace by @t-out",
                el.get('t-esc'),
                options.get('ref', '<unknown>'),
            )
        return self._compile_directive_out(el, options, indent)

    def _compile_directive_raw(self, el, options, indent):
        # deprecated use.
        _logger.warning(
            "Found deprecated directive @t-raw=%r in template %r. Replace by "
            "@t-out, and explicitely wrap content in `Markup` if "
            "necessary (which likely is not the case)",
            el.get('t-raw'),
            options.get('ref', '<unknown>'),
        )
        return self._compile_directive_out(el, options, indent)

    def _compile_directive_field(self, el, options, indent):
        """Compile `t-field` expressions into a python code as a list of
        strings.

        The compiled code will call ``_get_field`` method at rendering time
        using the type of value supplied by the field. This behavior can be
        changed with `t-options-widget` or `t-options={'widget': ...}.

        The code will contain evalution and rendering of the compiled value
        value from the record field. If the compiled value is None or False,
        the tag is not added to the render
        (Except if the widget forces rendering or there is default content.).
        """
        tagName = el.tag
        assert tagName not in ("table", "tbody", "thead", "tfoot", "tr", "td",
                                 "li", "ul", "ol", "dl", "dt", "dd"),\
            "RTE widgets do not work correctly on %r elements" % tagName
        assert tagName != 't',\
            "t-field can not be used on a t element, provide an actual HTML node"
        assert "." in el.get('t-field'),\
            "t-field must have at least a dot like 'record.field_name'"

        expression = el.attrib.pop('t-field')
        record, field_name = expression.rsplit('.', 1)

        code = []
        options['t_options_varname'] = 't_field_t_options'
        code_options = self._compile_directive(el, options, 'options', indent) or [self._indent("t_field_t_options = {}", indent)]
        code.extend(code_options)
        code.append(self._indent(f"attrs, content, force_display = self._get_field({self._compile_expr(record, raise_on_missing=True)}, {repr(field_name)}, {repr(expression)}, {repr(tagName)}, t_field_t_options, compile_options, values)", indent))
        code.append(self._indent("content = self._compile_to_str(content)", indent))
        code.extend(self._compile_widget_value(el, options, indent))
        return code

    def _compile_widget_value(self, el, options, indent=0, without_attributes=False):
        """Take care of part of the compilation of `t-out` and `t-field` (and
        the technical directive `t-tag). This is the part that takes care of
        whether or not created the tags and the default content of the element.
        """
        el.attrib.pop('t-tag', None)

        code = self._flushText(options, indent)
        code.append(self._indent("if content is not None and content is not False:", indent))
        code.extend(self._compile_tag_open(el, options, indent + 1, not without_attributes))
        code.extend(self._flushText(options, indent + 1))
        # Use str to avoid the escaping of the other html content.
        code.append(self._indent("yield str(escape(content))", indent + 1))
        code.extend(self._compile_tag_close(el, options))
        code.extend(self._flushText(options, indent + 1))

        default_body = self._compile_directive_content(el, options, indent + 1)
        if default_body or options['_text_concat']:
            # default content
            _text_concat = list(options['_text_concat'])
            options['_text_concat'].clear()
            code.append(self._indent("else:", indent))
            code.extend(self._compile_tag_open(el, options, indent + 1, not without_attributes))
            code.extend(self._flushText(options, indent + 1))
            code.extend(default_body)
            options['_text_concat'].extend(_text_concat)
            code.extend(self._compile_tag_close(el, options))
            code.extend(self._flushText(options, indent + 1))
        else:
            content = (self._compile_tag_open(el, options, indent + 1, not without_attributes) +
                self._compile_tag_close(el, options) +
                self._flushText(options, indent + 2))
            if content:
                code.append(self._indent("elif force_display:", indent))
                code.extend(content)

        return code

    def _compile_directive_call(self, el, options, indent):
        """Compile `t-call` expressions into a python code as a list of
        strings.

        `t-call` allow formating string dynamic at rendering time.
        Can use `t-options` used to call and render the sub-template at
        rendering time.
        The sub-template is called with a copy of the rendering values
        dictionary. The dictionary contains the key 0 coming from the
        compilation of the contents of this element

        The code will contain the call of the template and a function from the
        compilation of the content of this element.
        """
        expr = el.attrib.pop('t-call')

        if el.attrib.get('t-call-options'): # retro-compatibility
            el.attrib.set('t-options', el.attrib.pop('t-call-options'))

        nsmap = options.get('nsmap')

        code = self._flushText(options, indent)
        options['t_options_varname'] = 't_call_t_options'
        code_options = self._compile_directive(el, options, 'options', indent) or [self._indent("t_call_t_options = {}", indent)]
        code.extend(code_options)

        # content (t-out="0" and variables)
        def_name = "t_call_content"
        content = self._compile_directive_content(el, options, indent + 1)
        if content and not options['_text_concat']:
            self._appendText('', options) # To ensure the template function is a generator and doesn't become a regular function
        content.extend(self._flushText(options, indent + 1))
        if content:
            code.append(self._indent(f"def {def_name}(self, values, log):", indent))
            code.extend(content)
            code.append(self._indent("t_call_values = values.copy()", indent))
            code.append(self._indent(f"t_call_values['0'] = Markup(''.join({def_name}(self, t_call_values, log)))", indent))
        else:
            code.append(self._indent("t_call_values = values.copy()", indent))
            code.append(self._indent("t_call_values['0'] = Markup()", indent))

        # options
        code.append(self._indent(dedent(f"""
            t_call_options = compile_options.copy()
            t_call_options.update({{'caller_template': {repr(str(options.get('template')))}, 'last_path_node': {repr(str(options['root'].getpath(el)))} }})
            """).strip(), indent))
        if nsmap:
            # update this dict with the current nsmap so that the callee know
            # if he outputting the xmlns attributes is relevenat or not
            nsmap = []
            for key, value in options['nsmap'].items():
                if isinstance(key, str):
                    nsmap.append(f'{repr(key)}:{repr(value)}')
                else:
                    nsmap.append(f'None:{repr(value)}')
            code.append(self._indent(f"t_call_options.update(nsmap={{{', '.join(nsmap)}}})", indent))

        template = self._compile_format(expr)

        # call
        if code_options:
            code.append(self._indent("t_call_options.update(t_call_t_options)", indent))
            code.append(self._indent(dedent(f"""
                if compile_options.get('lang') != t_call_options.get('lang'):
                    self_lang = self.with_context(lang=t_call_options.get('lang'))
                    yield from self_lang._compile({template}, t_call_options)(self_lang, t_call_values)
                else:
                    yield from self._compile({template}, t_call_options)(self, t_call_values)
                """).strip(), indent))
        else:
            code.append(self._indent(f"yield from self._compile({template}, t_call_options)(self, t_call_values)", indent))

        return code

    # method called by computing code

    def _post_processing_att(self, tagName, atts, options):
        """ Method called at compile time for the static node and called at
            runing time for the dynamic attributes.

            This method may be overwrited to filter or modify the attributes
            (during compilation for static node or after they compilation in
            the case of dynamic elements).

            @returns dict
        """
        return atts

    def _get_field(self, record, field_name, expression, tagName, field_options, options, values):
        """Method called at compile time to return the field value.

        :returns: tuple:
            * dict: attributes
            * string or None: content
            * boolean: force_display display the tag if the content and default_content are None
        """
        return self._get_widget(getattr(record, field_name, None), expression, tagName, field_options, options, values)

    def _get_widget(self, value, expression, tagName, field_options, options, values):
        """Method called at compile time to return the widget value.

        :returns: tuple:
            * dict: attributes
            * string or None: content
            * boolean: force_display display the tag if the content and default_content are None
        """
        return ({}, value, False)

    def _debug_trace(self, debugger, options):
        """Method called at compile time to load debugger."""
        if debugger in SUPPORTED_DEBUGGERS:
            __import__(debugger).set_trace()
        else:
            raise QWebException(f"unsupported t-debug value: {debugger}", self, options)
