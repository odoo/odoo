# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
================
IrQWeb / ir.qweb
================

Preamble
========

Technical documentation of the python operation of the rendering QWeb engine.

Templating
==========

QWeb is the primary templating engine used by Odoo. It is an XML templating
engine and used mostly to generate XML, HTML fragments and pages.

Template directives are specified as XML attributes prefixed with ``t-``,
for instance ``t-if`` for :ref:`reference/qweb/conditionals`, with elements
and other attributes being rendered directly.

To avoid element rendering, a placeholder element ``<t>`` is also available,
which executes its directive but doesn't generate any output in and of
itself.

To create new XML template, please see :doc:`QWeb Templates documentation
<https://www.odoo.com/documentation/16.0/developer/reference/frontend/qweb.html>`

Rendering process
=================

In **input** you have an XML template giving the corresponding input etree.
Each etree input nodes are used to generate a python function. This fonction is
called and will give the XML **output**.
The ``_compile`` method is responsible to generate the function from the
etree, that function is a python generator that yield one output line at a
time. This generator is consumed by ``_render``. The generated function is orm
cached.

For performance, the **compile time** (when input, XML template or template
id, is compiled into a function) is less important than the **rendering time**
(when the function is called with the different values). The generation of the
function is only done once (for a set of options, language, branding ...)
because it is cached orm

The output is in ``MarkupSafe`` format. ``MarkupSafe`` escapes characters so
text is safe to use in HTML and XML. Characters that have special meanings
are replaced so that they display as the actual characters. This mitigates
injection attacks, meaning untrusted user input can safely be displayed on a
page.

At **compile time**, each dynamic attribute ``t-*`` will be compiled into
specific python code. (For example ``<t t-out="5 + 5"/>`` will insert the
template "10" inside the output)

At **compile time**, each directive removes the dynamic attribute it uses from
the input node attributes. At the end of the compilation each input node, no
dynamic attributes must remain.

How the code works
==================

In the graphic below you can see theresume of the call of the methods performed
in the IrQweb class.

.. code-block:: rst

    Odoo
     ┗━► _render (returns MarkupSafe)
        ┗━► _compile (returns function)                                        ◄━━━━━━━━━━┓
           ┗━► _compile_node (returns code string array)                       ◄━━━━━━━━┓ ┃
              ┃  (skip the current node if found t-qweb-skip)                           ┃ ┃
              ┃  (add technical directives: t-tag-open, t-tag-close, t-inner-content)   ┃ ┃
              ┃                                                                         ┃ ┃
              ┣━► _directives_eval_order (defined directive order)                      ┃ ┃
              ┣━► _compile_directives (loop)    Consume all remaining directives ◄━━━┓  ┃ ┃
              ┃  ┃                              (e.g.: to change the indentation)    ┃  ┃ ┃
              ┃  ┣━► _compile_directive                                              ┃  ┃ ┃
              ┃  ┃    ┗━► t-nocache       ━━► _compile_directive_nocache            ━┫  ┃ ┃
              ┃  ┃    ┗━► t-cache         ━━► _compile_directive_cache              ━┫  ┃ ┃
              ┃  ┃    ┗━► t-groups        ━━► _compile_directive_groups             ━┫  ┃ ┃
              ┃  ┃    ┗━► t-foreach       ━━► _compile_directive_foreach            ━┫  ┃ ┃
              ┃  ┃    ┗━► t-if            ━━► _compile_directive_if                 ━┛  ┃ ┃
              ┃  ┃    ┗━► t-inner-content ━━► _compile_directive_inner_content ◄━━━━━┓ ━┛ ┃
              ┃  ┃    ┗━► t-options       ━━► _compile_directive_options             ┃    ┃
              ┃  ┃    ┗━► t-set           ━━► _compile_directive_set           ◄━━┓  ┃    ┃
              ┃  ┃    ┗━► t-call          ━━► _compile_directive_call            ━┛ ━┫ ━━━┛
              ┃  ┃    ┗━► t-att           ━━► _compile_directive_att                 ┃
              ┃  ┃    ┗━► t-tag-open      ━━► _compile_directive_open          ◄━━┓  ┃
              ┃  ┃    ┗━► t-tag-close     ━━► _compile_directive_close         ◄━━┫  ┃
              ┃  ┃    ┗━► t-out           ━━► _compile_directive_out             ━┛ ━┫ ◄━━┓
              ┃  ┃    ┗━► t-field         ━━► _compile_directive_field               ┃   ━┫
              ┃  ┃    ┗━► t-esc           ━━► _compile_directive_esc                 ┃   ━┛
              ┃  ┃    ┗━► t-*             ━━► ...                                    ┃
              ┃  ┃                                                                   ┃
              ┗━━┻━► _compile_static_node                                           ━┛


The QWeb ``_render`` uses the function generated by the ``_compile`` method.
Each XML node will go through the ``_compile_node`` method. If the
node does not have dynamic directives or attributes (``_is_static_node``).
A ``static`` is a node without ``t-*`` attributes, does not require dynamic
rendering for its attributes.
If it's a ``static`` node, the ``_compile_static_node`` method is called,
otherwise it is the ``_compile_directives`` method after having prepared the
order for calling the directives using the ``_directives_eval_order`` method.
In the defined order, for each directive the method ``_compile_directive`` is
called which itself dispatches to the methods corresponding to the directives
``_compile_directive_[name of the directive]`` (for example: ``t-if`` =>
``_compile_directive_if``). After all ordered directives, the directives
attributes still present on the element are compiled.

The ``_post_processing_att`` method is used for the generation of rendering
attributes. If the attributes come from static XML template nodes then the
method is called only once when generating the render function. Otherwise the
method is called during each rendering.

Each expression is compiled by the method ``_compile_expr`` into a python
expression whose values are namespaced.

Directives
----------

``t-debug``
~~~~~~~~~~~
**Values**: ``pdb``, ``ipdb``, ``pudb``, ``wdb``

Activate the choosed debugger.

When dev mode is enabled this allows python developers to have access to the
state of variables being rendered. The code generated by the QWeb engine is
not accessible, only the variables (values, self) can be analyzed or the
methods that called the QWeb rendering.

``t-if``
~~~~~~~~
**Values**: python expression


Add an python ``if`` condition to the code string array, and call
``_compile_directives`` to level and add the code string array corresponding
to the other directives and content.

The structure of the dom is checked to possibly find a ``t-else`` or
``t-elif``. If these directives exist then the compilation is performed and
the nodes are marked not to be rendered twice.

At **rendering time** the other directives code and content will used only if
the expression is evaluated as truely.

The ``t-else``, ``t-elif`` and ``t-if`` are not compiled at the same time like
defined in ``_directives_eval_order`` method.
```
<t t-set="check" t-value="1"/>
<section t-if="False">10</section>
<span t-elif="check == 1" t-foreach="range(3)" t-as="check" t-esc="check"/>

<section t-if="False">10</section>
<div t-else="" t-if="check == 1" t-foreach="range(3)" t-as="check" t-esc="check"/>

Result:

<span>0</span>
<span>1</span>
<span>2</span>

<div>1</div>
```

``t-else``
~~~~~~~~~~
**Values**: nothing

Only validate the **input**, the compilation if inside the ``t-if`` directive.

``t-elif``
~~~~~~~~~~
**Values**: python expression

Only validate the **input**, the compilation if inside the ``t-if`` directive.

``t-groups`` (``groups`` is an alias)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Values**: name of the allowed odoo user group, or preceded by ``!`` for
prohibited groups

The generated code uses ``user_has_groups`` Odoo method.

``t-foreach``
~~~~~~~~~~~~~
**Values**: an expression returning the collection to iterate on

This directive is used with ``t-as`` directive to defined the key name. The
directive will be converted into a ``for`` loop. In this loop, different values
are added to the dict (``values`` in the generated method) in addition to the
key defined by ``t-name``, these are (``*_value``, ``*_index``, ``*_size``,
``*_first``, ``*_last``).

``t-as``
~~~~~~~~
**Values**: key name

The compilation method only validates if ``t-as`` and ``t-foreach`` are on the
same node.

``t-options`` and ``t-options-*``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Values**: python expression

It's use on the same node of another directive, it's used to configure the
other directive. Used on the same ``input node`` of the directives ``t-call``,
``t-field`` or ``t-out``.

Create a ``values['__qweb_options__']`` dict from the optional ``t-options``
expression and add each key-value ``t-options-key="expression value"`` to this
dict. (for example: ``t-options="{'widget': 'float'}"`` is equal to
``t-options-widget="'float'"``)

``t-att``, ``t-att-*`` and ``t-attf-*``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Values**: python expression (or format string expression for ``t-attf-``)

Compile the attributes to create ``values['__qweb_attrs__']`` dictionary code
in the compiled function. Use the ``t-att`` expression and add each key-value
``t-att-key="expression value"`` to this dict. (for example:
``t-att="{'class': f'float_{1}'}"`` is equal to ``t-att-class="f'float_{1}'"``
and is equal to ``t-attf-class="float_{{1}}")

The attributes come from new namespaces, static elements (not preceded
by ``t-``) and dynamic attributes ``t-att``, attributes prefixed by ``t-att-``
(python expression) or ``t-attf`` (format string expression).

``t-call``
~~~~~~~~~~
**Values**: format string expression for template name

Serves the called template in place of the current ``t-call`` node.

Here are the different steps performed by the generated python code:

#. copy the ``values`` dictionary;
#. render the content (``_compile_directive_inner_content``) of the tag in a
   separate method called with the previous copied values. This values can be
   updated via t-set. The visible content of the rendering of the sub-content
   is added as a magical value ``0`` (can be rendered with ``t-out="0"``);
#. copy the ``compile_context`` dictionary;
#. compile the directive ``t-options`` and update the ``compile_context``
    are, in added to the calling template and the ``nsmap`` values;
#. get the compiled function from the ``_compile`` method;
#. use the compiled function to serves the called template.

``t-lang``
~~~~~~~~~~
**Values**: python expression

Used to serve the called template (``t-call``) in another language. Used
together with ``t-call``.

This directive will be evaluate like ``t-options-lang``. Allows you to change
the language in which the called template is rendered. It's in the ``t-call``
directive that the language of the context of the ``ir.qweb`` recordset on
which the ``_compile`` function is called is updated.

``t-call-assets``
~~~~~~~~~~~~~~~~~
**Values**: format string for template name

The generated code call the ``_get_asset_nodes`` method to get the list of
(tagName, attrs and content). From each tuple a tag is created into the
rendering.

``t-out``
~~~~~~~~~
**Values**: python expression

Output the given value or if falsy, display the content as default value.
(for example: ``<t t-out="given_value">Default content</t>``)

The generated code add the value into the ``MarkupSafe`` rendering.
If a widget is defined (``t-options-widget``), the generated code call the
``_get_widget`` method to have the formatted field value and attributes. It's
the ``ir.qweb.field.*`` models that format the value.

``t-field``
~~~~~~~~~~~
**Values**: String representing the path to the field. (for example:
``t-field="record.name"``)

Output the field value or if falsy, display the content as default value.
(for example: ``<span t-field="record.name">Default content</span>``)

Use ``t-out`` compile method but the generated code call ``_get_field``
instead of ``_get_widget``. It's the ``ir.qweb.field.*`` models that format
the value. The rendering model is chosen according to the type of field. The
rendering model can be modified via the ``t-options-widget``.

``t-esc``
~~~~~~~~~
Deprecated, please use ``t-out``

``t-raw``
~~~~~~~~~
Deprecated, please use ``t-out``

``t-set``
~~~~~~~~~
**Values**: key name

The generated code update the key ``values`` dictionary equal to the value
defined by ``t-value`` expression, ``t-valuef`` format string expression or
to the ``MarkupSafe`` rendering come from the content of the node.

``t-value``
~~~~~~~~~~~
**Values**: python expression

The compilation method only validates if ``t-value`` and ``t-set`` are on the
same node.

``t-valuef``
~~~~~~~~~~~~
**Values**: format string expression

The compilation method only validates if ``t-valuef`` and ``t-set`` are on the
same node.

Technical directives
--------------------

Directive added automatically by IrQweb in order to go through the compilation
methods.

``t-tag-open``
~~~~~~~~~~~~~~
Used to generate the opening HTML/XML tags.

``t-tag-close``
~~~~~~~~~~~~~~
Used to generate the closing HTML/XML tags.

``t-inner-content``
~~~~~~~~~~~~~~~~~~~
Used to add the content of the node (text, tail and children nodes).
If namespaces are declared on the current element then a copy of the options
is made.

``t-consumed-options``
~~~~~~~~~~~~~~~~~~~~~~
Raise an exception if the ``t-options`` is not consumed.

``t-qweb-skip``
~~~~~~~~~~~~~~~~~~~~~~
Ignore rendering and directives for the curent **input** node.

``t-else-valid``
~~~~~~~~~~~~~~~~~~~~~~
Mark a node with ``t-else`` or ``t-elif`` having a valid **input** dom
structure.

"""

import fnmatch
import io
import logging
import math
import re
import textwrap
import time
import token
import tokenize
import traceback
import werkzeug

from markupsafe import Markup, escape
from collections.abc import Sized, Mapping
from itertools import count, chain
from lxml import etree
from dateutil.relativedelta import relativedelta
from psycopg2.extensions import TransactionRollbackError

from odoo import api, models, tools
from odoo.tools import config, safe_eval, pycompat, SUPPORTED_DEBUGGER
from odoo.tools.safe_eval import assert_valid_codeobj, _BUILTINS, to_opcodes, _EXPR_OPCODES, _BLACKLIST
from odoo.tools.json import scriptsafe
from odoo.tools.misc import str2bool
from odoo.tools.image import image_data_uri
from odoo.http import request
from odoo.modules.module import get_resource_path, get_module_path
from odoo.tools.profiler import QwebTracker
from odoo.exceptions import UserError, AccessDenied, AccessError, MissingError, ValidationError

from odoo.addons.base.models.assetsbundle import AssetsBundle
from odoo.addons.base.models.ir_asset import can_aggregate, STYLE_EXTENSIONS, SCRIPT_EXTENSIONS, TEMPLATE_EXTENSIONS

_logger = logging.getLogger(__name__)


# QWeb token usefull for generate expression used in `_compile_expr_tokens` method
token.QWEB = token.NT_OFFSET - 1
token.tok_name[token.QWEB] = 'QWEB'


# security safe eval opcodes for generated expression validation, used in `_compile_expr`
_SAFE_QWEB_OPCODES = _EXPR_OPCODES.union(to_opcodes([
    'MAKE_FUNCTION', 'CALL_FUNCTION', 'CALL_FUNCTION_KW', 'CALL_FUNCTION_EX',
    'CALL_METHOD', 'LOAD_METHOD',

    'GET_ITER', 'FOR_ITER', 'YIELD_VALUE',
    'JUMP_FORWARD', 'JUMP_ABSOLUTE', 'JUMP_BACKWARD',
    'JUMP_IF_FALSE_OR_POP', 'JUMP_IF_TRUE_OR_POP', 'POP_JUMP_IF_FALSE', 'POP_JUMP_IF_TRUE',

    'LOAD_NAME', 'LOAD_ATTR',
    'LOAD_FAST', 'STORE_FAST', 'UNPACK_SEQUENCE',
    'STORE_SUBSCR',
    'LOAD_GLOBAL',
    # Following opcodes were added in 3.11 https://docs.python.org/3/whatsnew/3.11.html#new-opcodes
    'RESUME',
    'CALL',
    'PRECALL',
    'POP_JUMP_FORWARD_IF_FALSE',
    'PUSH_NULL',
    'POP_JUMP_FORWARD_IF_TRUE', 'KW_NAMES',
    'FORMAT_VALUE', 'BUILD_STRING',
    'RETURN_GENERATOR',
    'POP_JUMP_BACKWARD_IF_FALSE',
    'SWAP',
])) - _BLACKLIST


# eval to compile generated string python code into binary code, used in `_compile`
unsafe_eval = eval


VOID_ELEMENTS = frozenset([
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'keygen',
    'link', 'menuitem', 'meta', 'param', 'source', 'track', 'wbr'])
# Terms allowed in addition to AVAILABLE_OBJECTS when compiling python expressions
ALLOWED_KEYWORD = frozenset(['False', 'None', 'True', 'and', 'as', 'elif', 'else', 'for', 'if', 'in', 'is', 'not', 'or'] + list(_BUILTINS))
# regexpr for string formatting and extract ( ruby-style )|( jinja-style  ) used in `_compile_format`
FORMAT_REGEX = re.compile(r'(?:#\{(.+?)\})|(?:\{\{(.+?)\}\})')
RSTRIP_REGEXP = re.compile(r'\n[ \t]*$')
LSTRIP_REGEXP = re.compile(r'^[ \t]*\n')
FIRST_RSTRIP_REGEXP = re.compile(r'^(\n[ \t]*)+(\n[ \t])')
VARNAME_REGEXP = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
TO_VARNAME_REGEXP = re.compile(r'[^A-Za-z0-9_]+')
# Attribute name used outside the context of the QWeb.
SPECIAL_DIRECTIVES = {'t-translation', 't-ignore', 't-title'}
# Name of the variable to insert the content in t-call in the template.
# The slot will be replaced by the `t-call` tag content of the caller.
T_CALL_SLOT = '0'


def indent_code(code, level):
    """Indent the code to respect the python syntax."""
    return textwrap.indent(textwrap.dedent(code).strip(), ' ' * 4 * level)


def keep_query(*keep_params, **additional_params):
    """
    Generate a query string keeping the current request querystring's parameters specified
    in ``keep_params`` and also adds the parameters specified in ``additional_params``.

    Multiple values query string params will be merged into a single one with comma seperated
    values.

    The ``keep_params`` arguments can use wildcards too, eg:

        keep_query('search', 'shop_*', page=4)
    """
    if not keep_params and not additional_params:
        keep_params = ('*',)
    params = additional_params.copy()
    qs_keys = list(request.httprequest.args) if request else []
    for keep_param in keep_params:
        for param in fnmatch.filter(qs_keys, keep_param):
            if param not in additional_params and param in qs_keys:
                params[param] = request.httprequest.args.getlist(param)
    return werkzeug.urls.url_encode(params)

####################################
###        QWebException         ###
####################################

class QWebException(Exception):
    """ Management of errors that raised when rendering a QWeb template.
    """
    def __init__(self, message, qweb, template=None, ref=None, path_xml=None, code=None):
        self.stack = traceback.format_exc()
        self.name = template
        self.ref = ref
        self.path, self.html = path_xml or (None, None)
        self.code = None
        if code:
            self.code = '\n'.join(code.split('\n')[:-1]) if qweb.env.context.get('dev_mode') else None
            line_nb = 0
            for error_line in reversed(self.stack.split('\n')):
                if f'File "<{self.ref}>"' in error_line:
                    line_function = error_line.split(', line ')[1]
                    line_nb = int(line_function.split(',')[0])
                    break
            for code_line in reversed(code.split('\n')[:line_nb]):
                match = re.match(r'\s*# element: (.*) , (.*)', code_line)
                if match:
                    self.path = match[1][1:-1]
                    self.html = match[2][1:-1]
                    break

        self.title = message
        super().__init__(message)

    def __str__(self):
        parts = [self.title]
        if self.__cause__ and str(self.__cause__) != '':
            parts.append(f"{self.__cause__.__class__.__name__}: {self.__cause__}")
        elif self.__context__ and str(self.__context__) != '':
            parts.append(f"{self.__context__.__class__.__name__}: {self.__context__}")
        if self.name is not None:
            parts.append(f"Template: {self.name}")
        if self.path is not None:
            parts.append(f"Path: {self.path}")
        if self.html is not None:
            parts.append(f"Node: {self.html}")
        if self.code is not None:
            parts.append(f"Compiled code:\n{self.code}")
        return "\n".join(parts)

    def __repr__(self):
        return f"QWebException({self.title!r})"

####################################
###             QWeb             ###
####################################


class IrQWeb(models.AbstractModel):
    """ Base QWeb rendering engine
    * to customize ``t-field`` rendering, subclass ``ir.qweb.field`` and
      create new models called :samp:`ir.qweb.field.{widget}`
    Beware that if you need extensions or alterations which could be
    incompatible with other subsystems, you should create a local object
    inheriting from ``ir.qweb`` and customize that.
    """

    _name = 'ir.qweb'
    _description = 'Qweb'

    @QwebTracker.wrap_render
    @api.model
    def _render(self, template, values=None, **options):
        """ render(template, values, **options)

        Render the template specified by the given name.

        :param template: etree, xml_id, template name (see _get_template)
            * Call the method ``load`` is not an etree.
        :param dict values: template values to be used for rendering
        :param options: used to compile the template
            Options will be add into the IrQweb.env.context for the rendering.
            * ``lang`` (str) used language to render the template
            * ``inherit_branding`` (bool) add the tag node branding
            * ``inherit_branding_auto`` (bool) add the branding on fields
            * ``minimal_qcontext``(bool) To use the minimum context and options
                from ``_prepare_environment``

        :returns: bytes marked as markup-safe (decode to :class:`markupsafe.Markup`
                  instead of `str`)
        :rtype: MarkupSafe
        """
        values = values.copy() if values else {}
        if T_CALL_SLOT in values:
            raise ValueError(f'values[{T_CALL_SLOT}] should be unset when call the _render method and only set into the template.')

        irQweb = self.with_context(**options)._prepare_environment(values)

        safe_eval.check_values(values)

        template_functions, def_name = irQweb._compile(template)
        render_template = template_functions[def_name]
        rendering = render_template(irQweb, values)
        result = ''.join(rendering)

        return Markup(result)

    # assume cache will be invalidated by third party on write to ir.ui.view
    def _get_template_cache_keys(self):
        """ Return the list of context keys to use for caching ``_compile``. """
        return ['lang', 'inherit_branding', 'edit_translations', 'profile']

    @tools.conditional(
        'xml' not in tools.config['dev_mode'],
        tools.ormcache('template', 'tuple(self.env.context.get(k) for k in self._get_template_cache_keys())'),
    )
    def _get_view_id(self, template):
        try:
            return self.env['ir.ui.view'].sudo().with_context(load_all_views=True)._get_view_id(template)
        except Exception:
            return None

    @QwebTracker.wrap_compile
    def _compile(self, template):
        if isinstance(template, etree._Element):
            self = self.with_context(is_t_cache_disabled=True)
            ref = None
        else:
            ref = self._get_view_id(template)

        # define the base key cache for code in cache and t-cache feature
        base_key_cache = None
        if ref:
            base_key_cache = self._get_cache_key(tuple([ref] + [self.env.context.get(k) for k in self._get_template_cache_keys()]))
        self = self.with_context(__qweb_base_key_cache=base_key_cache)

        # generate the template functions and the root function name
        def generate_functions():
            code, options, def_name = self._generate_code(template)
            profile_options = {
                'ref': options.get('ref') and int(options['ref']) or None,
                'ref_xml': options.get('ref_xml') and str(options['ref_xml']) or None,
            } if self.env.context.get('profile') else None
            code = '\n'.join([
                "def generate_functions():",
                "    template_functions = {}",
                indent_code(code, 1),
                f"    template_functions['options'] = {profile_options!r}",
                "    return template_functions",
            ])

            try:
                compiled = compile(code, f"<{ref}>", 'exec')
                globals_dict = self._prepare_globals()
                globals_dict['__builtins__'] = globals_dict # So that unknown/unsafe builtins are never added.
                unsafe_eval(compiled, globals_dict)
                return globals_dict['generate_functions'](), def_name
            except QWebException:
                raise
            except Exception as e:
                raise QWebException("Error when compiling xml template",
                    self, template, code=code, ref=ref) from e

        return self._load_values(base_key_cache, generate_functions)

    def _generate_code(self, template):
        """ Compile the given template into a rendering function (generator)::

            render_template(qweb, values)
            This method can be called only by the IrQweb `_render` method or by
            the compiled code of t-call from an other template.

            An `options` dictionary is created and attached to the function. It
            contains rendering options that are part of the cache key in
            addition to template references.

            where ``qweb`` is a QWeb instance and ``values`` are the values to
            render.

            :returns: tuple containing code, options and main method name
        """
        # The `compile_context`` dictionary includes the elements used for the
        # cache key to which are added the template references as well as
        # technical information useful for generating the function. This
        # dictionary is only used when compiling the template.
        compile_context = self.env.context.copy()

        try:
            element, document, ref = self._get_template(template)
        except (ValueError, UserError) as e:
            # return the error function if the template is not found or fail
            message = str(e)
            code = indent_code(f"""
                def not_found_template(self, values):
                    if self.env.context.get('raise_if_not_found', True):
                        raise {e.__class__.__name__}({message!r})
                    warning('Cannot load template %s: %s', {template!r}, {message!r})
                    return ''
                template_functions = {{'not_found_template': not_found_template}}
            """, 0)
            return (code, {}, 'not_found_template')

        compile_context.pop('raise_if_not_found', None)

        # reference to get xml and etree (usually the template ID)
        compile_context['ref'] = ref
        # reference name or key to get xml and etree (usually the template XML ID)
        compile_context['ref_name'] = element.attrib.pop('t-name', template if isinstance(template, str) and '<' not in template else None)
        # str xml of the reference template used for compilation. Useful for debugging, dev mode and profiling.
        compile_context['ref_xml'] = document
        # Identifier used to call `_compile`
        compile_context['template'] = template
        # Root of the etree which will be processed during compilation.
        compile_context['root'] = element.getroottree()
        # Reference to the last node being compiled. It is mainly used for debugging and displaying error messages.
        compile_context['_qweb_error_path_xml'] = None

        if not compile_context.get('nsmap'):
            compile_context['nsmap'] = {}

        # The options dictionary includes cache key elements and template
        # references. It will be attached to the generated function. This
        # dictionary is only there for logs, performance or test information.
        # The values of these `options` cannot be changed and must always be
        # identical in `context` and `self.env.context`.
        options = {k: compile_context.get(k) for k in self._get_template_cache_keys() + ['ref', 'ref_name', 'ref_xml']}

        # generate code

        def_name = TO_VARNAME_REGEXP.sub(r'_', f'template_{ref}')

        name_gen = count()
        compile_context['make_name'] = lambda prefix: f"{def_name}_{prefix}_{next(name_gen)}"

        try:
            if element.text:
                element.text = FIRST_RSTRIP_REGEXP.sub(r'\2', element.text)

            compile_context['template_functions'] = {}

            compile_context['_text_concat'] = []
            self._append_text("", compile_context) # To ensure the template function is a generator and doesn't become a regular function
            compile_context['template_functions'][f'{def_name}_content'] = (
                [f"def {def_name}_content(self, values):"]
                + self._compile_node(element, compile_context, 2)
                + self._flush_text(compile_context, 2, rstrip=True))

            compile_context['template_functions'][def_name] = [indent_code(f"""
                def {def_name}(self, values):
                    try:
                        if '__qweb_loaded_values' not in values:
                            values['__qweb_loaded_values'] = {{}}
                            values['__qweb_root_values'] = values.copy()
                            values['xmlid'] = {options['ref_name']!r}
                            values['viewid'] = {options['ref']!r}
                        values['__qweb_loaded_values'].update(template_functions)

                        yield from {def_name}_content(self, values)
                    except QWebException:
                        raise
                    except Exception as e:
                        if isinstance(e, TransactionRollbackError):
                            raise
                        raise QWebException("Error while render the template",
                            self, template, ref={compile_context['ref']!r}, code=code) from e
                    """, 0)]
        except QWebException:
            raise
        except Exception as e:
            raise QWebException("Error when compiling xml template",
                self, template, ref=compile_context['ref'], path_xml=compile_context['_qweb_error_path_xml']) from e

        code_lines = ['code = None']
        code_lines.append(f'template = {(document if isinstance(template, etree._Element) else template)!r}')
        code_lines.append('template_functions = {}')

        for lines in compile_context['template_functions'].values():
            code_lines.extend(lines)

        for name in compile_context['template_functions']:
            code_lines.append(f'template_functions[{name!r}] = {name}')

        code = '\n'.join(code_lines)
        code += f'\n\ncode = {code!r}'

        return (code, options, def_name)

    # read and load input template

    def _get_template(self, template):
        """ Retrieve the given template, and return it as a tuple ``(etree,
        xml, ref)``, where ``element`` is an etree, ``document`` is the
        string document that contains ``element``, and ``ref`` if the uniq
        reference of the template (id, t-name or template).

        :param template: template identifier or etree
        """
        assert template not in (False, None, ""), "template is required"

        # template is an xml etree already
        if isinstance(template, etree._Element):
            element = template
            document = etree.tostring(template, encoding='unicode')
            ref = None
        # template is xml as string
        elif isinstance(template, str) and '<' in template:
            raise ValueError('Inline templates must be passed as `etree` documents')

        # template is (id or ref) to a database stored template
        else:
            try:
                ref_alias = int(template)  # e.g. <t t-call="33"/>
            except ValueError:
                ref_alias = template  # e.g. web.layout

            doc_or_elem, ref = self._load(ref_alias) or (None, None)
            if doc_or_elem is None:
                raise ValueError(f"Can not load template: {ref_alias!r}")
            if isinstance(doc_or_elem, etree._Element):
                element = doc_or_elem
                document = etree.tostring(doc_or_elem, encoding='unicode')
            elif isinstance(doc_or_elem, str):
                element = etree.fromstring(doc_or_elem)
                document = doc_or_elem
            else:
                raise TypeError(f"Loaded template {ref!r} should be a string.")

        # return etree, document and ref, or try to find the ref
        if ref:
            return (element, document, ref)

        # <templates>
        #   <template t-name=... /> <!-- return ONLY this element -->
        #   <template t-name=... />
        # </templates>
        for node in element.iter():
            ref = node.get('t-name')
            if ref:
                return (node, document, ref)

        # use the document itself as ref when no t-name was found
        return (element, document, document)

    def _load(self, ref):
        """
        Load the template referenced by ``ref``.

        :returns: The loaded template (as string or etree) and its
            identifier
        :rtype: Tuple[Union[etree, str], Optional[str, int]]
        """
        IrUIView = self.env['ir.ui.view'].sudo()
        view = IrUIView._get(ref)
        template = IrUIView._read_template(view.id)
        etree_view = etree.fromstring(template)

        xmlid = view.key or ref
        if isinstance(ref, int):
            domain = [('model', '=', 'ir.ui.view'), ('res_id', '=', view.id)]
            model_data = self.env['ir.model.data'].sudo().search_read(domain, ['module', 'name'], limit=1)
            if model_data:
                xmlid = f"{model_data[0]['module']}.{model_data[0]['name']}"

        # QWeb's ``_read_template`` will check if one of the first children of
        # what we send to it has a "t-name" attribute having ``ref`` as value
        # to consider it has found it. As it'll never be the case when working
        # with view ids or children view or children primary views, force it here.
        if view.inherit_id is not None:
            for node in etree_view:
                if node.get('t-name') == str(ref) or node.get('t-name') == str(view.key):
                    node.attrib.pop('name', None)
                    node.attrib.pop('id', None)
                    etree_view = node
                    break
        etree_view.set('t-name', str(xmlid))
        return (etree_view, view.id)

    # values for running time

    def _prepare_environment(self, values):
        """ Prepare the values and context that will sent to the
        compiled and evaluated function.

        :param values: template values to be used for rendering

        :returns self (with new context)
        """
        debug = request and request.session.debug or ''
        values.update(
            true=True,
            false=False,
        )
        if not self.env.context.get('minimal_qcontext'):
            values.setdefault('debug', debug)
            values.setdefault('user_id', self.env.user.with_env(self.env))
            values.setdefault('res_company', self.env.company.sudo())

            values.update(
                request=request,  # might be unbound if we're not in an httprequest context
                test_mode_enabled=bool(config['test_enable'] or config['test_file']),
                json=scriptsafe,
                quote_plus=werkzeug.urls.url_quote_plus,
                time=safe_eval.time,
                datetime=safe_eval.datetime,
                relativedelta=relativedelta,
                image_data_uri=image_data_uri,
                # specific 'math' functions to ease rounding in templates and lessen controller marshmalling
                floor=math.floor,
                ceil=math.ceil,
                env=self.env,
                lang=self.env.context.get('lang'),
                keep_query=keep_query,
            )

        context = {'dev_mode': 'qweb' in tools.config['dev_mode']}
        if 'xml' in tools.config['dev_mode']:
            context['is_t_cache_disabled'] = True
        elif 'disable-t-cache' in debug:
            context['is_t_cache_disabled'] = True
        return self.with_context(**context)

    def _prepare_globals(self):
        """ Prepare the global context that will sent to eval the qweb
        generated code.
        """
        return {
            'Sized': Sized,
            'Mapping': Mapping,
            'Markup': Markup,
            'escape': escape,
            'VOID_ELEMENTS': VOID_ELEMENTS,
            'QWebException': QWebException,
            'Exception': Exception,
            'TransactionRollbackError': TransactionRollbackError, # for SerializationFailure in assets
            'ValueError': ValueError,
            'UserError': UserError,
            'AccessDenied': AccessDenied,
            'AccessError': AccessError,
            'MissingError': MissingError,
            'ValidationError': ValidationError,
            'warning': lambda *args: _logger.warning(*args),
            **_BUILTINS,
        }

    # helpers for compilation

    def _append_text(self, text, compile_context):
        """ Add an item (converts to a string) to the list.
            This will be concatenated and added during a call to the
            `_flush_text` method. This makes it possible to return only one
            yield containing all the parts."""
        compile_context['_text_concat'].append(self._compile_to_str(text))

    def _rstrip_text(self, compile_context):
        """ The text to flush is right stripped, and the stripped content are
        returned.
        """
        text_concat = compile_context['_text_concat']
        if not text_concat:
            return ''

        result = RSTRIP_REGEXP.search(text_concat[-1])
        strip = result.group(0) if result else ''
        text_concat[-1] = RSTRIP_REGEXP.sub('', text_concat[-1])

        return strip

    def _flush_text(self, compile_context, level, rstrip=False):
        """Concatenate all the textual chunks added by the `_append_text`
            method into a single yield.
            If no text to flush, return an empty list

            If rstrip the text is right stripped.

            @returns list(str)
        """
        text_concat = compile_context['_text_concat']
        if not text_concat:
            return []
        if rstrip:
            self._rstrip_text(compile_context)
        text = ''.join(text_concat)
        text_concat.clear()
        return [f"{'    ' * level}yield {text!r}"]

    def _is_static_node(self, el, compile_context):
        """ Test whether the given element is purely static, i.e. (there
        are no t-* attributes), does not require dynamic rendering for its
        attributes.
        """
        return el.tag != 't' and 'groups' not in el.attrib and not any(
            att.startswith('t-') and att not in ('t-tag-open', 't-inner-content')
            for att in el.attrib
        )

    # compile python expression and format string

    def _compile_format(self, expr):
        """ Parses the provided format string and compiles it to a single
        expression python, uses string with format method.
        Use format is faster to concat string and values.
        """
        # <t t-setf-name="Hello #{world} %s !"/>
        # =>
        # values['name'] = 'Hello %s %%s !' % (values['world'],)
        values = [
            f'self._compile_to_str({self._compile_expr(m.group(1) or m.group(2))})'
            for m in FORMAT_REGEX.finditer(expr)
        ]
        code = repr(FORMAT_REGEX.sub('%s', expr.replace('%', '%%')))
        if values:
            code += f' % ({", ".join(values)},)'
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
        open_bracket_index = -1
        bracket_depth = 0

        argument_name = '_arg_%s__'
        argument_names = argument_names or []

        for index, t in enumerate(tokens):
            if t.exact_type in [token.LPAR, token.LSQB, token.LBRACE]:
                bracket_depth += 1
            elif t.exact_type in [token.RPAR, token.RSQB, token.RBRACE]:
                bracket_depth -= 1
            elif bracket_depth == 0 and t.exact_type == token.NAME:
                string = t.string
                if string == 'lambda': # lambda => allowed values for the current bracket depth
                    for i in range(index + 1, len(tokens)):
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
                elif string == 'for': # list comprehensions => allowed values for the current bracket depth
                    for i in range(index + 1, len(tokens)):
                        t = tokens[i]
                        if t.exact_type == token.NAME:
                            if t.string == 'in':
                                break
                            argument_names.append(t.string)
                        elif t.exact_type in [token.COMMA, token.LPAR, token.RPAR]:
                            pass
                        else:
                            raise NotImplementedError('This loop code style is not implemented.')

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
        pos = tokens and tokens[0].start # to keep level when use expr on multi line
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
                    code.append(f'values[{string!r}]')
                else:
                    # not assignation allowed, only getter
                    code.append(f'values.get({string!r})')
            elif t.type not in [tokenize.ENCODING, token.ENDMARKER, token.DEDENT]:
                code.append(string)

            if t.end[0] != pos[0]:
                pos = (t.end[0], 0)
            else:
                pos = t.end

            index += 1

        return ''.join(code)

    def _compile_expr(self, expr, raise_on_missing=False):
        """Transform string coming into a python instruction in textual form by
        adding the namepaces for the dynamic values.
        This method tokenize the string and call ``_compile_expr_tokens``
        method.

        :param expr: string: python expression
        :param [raise_on_missing]: boolean:
            Compile has `values['product'].price` instead of
            `values.get('product').price` to raise an error when get the
            'product' value and not an 'NoneType' object has no attribute
            'price' error.
        """
        # Parentheses are useful for compiling multi-line expressions such as
        # conditions existing in some templates. (see test_compile_expr tests)
        readable = io.BytesIO(f"({expr or ''})".encode('utf-8'))
        try:
            tokens = list(tokenize.tokenize(readable.readline))
        except tokenize.TokenError:
            raise ValueError(f"Can not compile expression: {expr}")

        expression = self._compile_expr_tokens(tokens, ALLOWED_KEYWORD, raise_on_missing=raise_on_missing)

        assert_valid_codeobj(_SAFE_QWEB_OPCODES, compile(expression, '<>', 'eval'), expr)

        return f"({expression})"

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
            'elif', # Must be the first because compiled by the previous if.
            'else', # Must be the first because compiled by the previous if.
            'debug',
            'nocache',
            'cache',
            'groups',
            'as', 'foreach',
            'if',
            'call-assets',
            'lang',
            'options',
            'att',
            'field', 'esc', 'raw', 'out',
            'tag-open',
            'call',
            'set',
            'inner-content',
            'tag-close',
        ]

    # compile

    def _compile_node(self, el, compile_context, level):
        """ Compile the given element into python code.

            The t-* attributes (directives) will be converted to a python instruction. If there
            are no t-* attributes, the element will be considered static.

            Directives are compiled using the order provided by the
            ``_directives_eval_order`` method (an create the
            ``compile_context['iter_directives']`` iterator).
            For compilation, the directives supported are those with a
            compilation method ``_compile_directive_*``

        :return: list of string
        """
        # Internal directive used to skip a rendering.
        if 't-qweb-skip' in el.attrib:
            return []

        # if tag don't have qweb attributes don't use directives
        if self._is_static_node(el, compile_context):
            return self._compile_static_node(el, compile_context, level)

        path = compile_context['root'].getpath(el)
        xml = etree.tostring(etree.Element(el.tag, el.attrib), encoding='unicode')
        compile_context['_qweb_error_path_xml'] = (path, xml)
        body = [indent_code(f'# element: {path!r} , {xml!r}', level)]

        # create an iterator on directives to compile in order
        compile_context['iter_directives'] = iter(self._directives_eval_order())

        # add technical directive tag-open, tag-close, inner-content and take
        # care of the namspace
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

        if unqualified_el_tag != 't':
            el.set('t-tag-open', el_tag)
            if unqualified_el_tag not in VOID_ELEMENTS:
                el.set('t-tag-close', el_tag)

        if not ({'t-out', 't-esc', 't-raw', 't-field'} & set(el.attrib)):
            el.set('t-inner-content', 'True')

        return body + self._compile_directives(el, compile_context, level)

    def _compile_static_node(self, el, compile_context, level):
        """ Compile a purely static element into a list of string. """
        if not el.nsmap:
            unqualified_el_tag = el_tag = el.tag
            attrib = self._post_processing_att(el.tag, el.attrib)
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
            for ns_prefix, ns_definition in set(el.nsmap.items()) - set(compile_context['nsmap'].items()):
                if ns_prefix is None:
                    attrib['xmlns'] = ns_definition
                else:
                    attrib[f'xmlns:{ns_prefix}'] = ns_definition

            # Etree will also remove the ns prefixes indirection in the attributes. As we only have
            # the namespace definition, we'll use an nsmap where the keys are the definitions and
            # the values the prefixes in order to get back the right prefix and restore it.
            ns = chain(compile_context['nsmap'].items(), el.nsmap.items())
            nsprefixmap = {v: k for k, v in ns}
            for key, value in el.attrib.items():
                attrib_qname = etree.QName(key)
                if attrib_qname.namespace:
                    attrib[f'{nsprefixmap[attrib_qname.namespace]}:{attrib_qname.localname}'] = value
                else:
                    attrib[key] = value

            attrib = self._post_processing_att(el.tag, attrib)

            # Update the dict of inherited namespaces before continuing the recursion. Note:
            # since `compile_context['nsmap']` is a dict (and therefore mutable) and we do **not**
            # want changes done in deeper recursion to bevisible in earlier ones, we'll pass
            # a copy before continuing the recursion and restore the original afterwards.
            original_nsmap = dict(compile_context['nsmap'])

        if unqualified_el_tag != 't':
            attributes = ''.join(f' {name}="{escape(str(value))}"'
                                for name, value in attrib.items() if value or isinstance(value, str))
            self._append_text(f'<{el_tag}{"".join(attributes)}', compile_context)
            if unqualified_el_tag in VOID_ELEMENTS:
                self._append_text('/>', compile_context)
            else:
                self._append_text('>', compile_context)

        el.attrib.clear()

        if el.nsmap:
            compile_context['nsmap'].update(el.nsmap)
            body = self._compile_directive(el, compile_context, 'inner-content', level)
            compile_context['nsmap'] = original_nsmap
        else:
            body = self._compile_directive(el, compile_context, 'inner-content', level)

        if unqualified_el_tag != 't':
            if unqualified_el_tag not in VOID_ELEMENTS:
                self._append_text(f'</{el_tag}>', compile_context)

        return body

    def _compile_directives(self, el, compile_context, level):
        """ Compile the given element, following the directives given in the
        iterator ``compile_context['iter_directives']`` create by
        `_compile_node`` method.

        :return: list of code lines
        """
        if self._is_static_node(el, compile_context):
            el.attrib.pop('t-tag-open', None)
            el.attrib.pop('t-inner-content', None)
            el.attrib.pop('t-tag-close', None)
            return self._compile_static_node(el, compile_context, level)

        code = []

        # compile the directives still present on the element
        for directive in compile_context['iter_directives']:
            if ('t-' + directive) in el.attrib:
                code.extend(self._compile_directive(el, compile_context, directive, level))
            elif directive == 'groups':
                if directive in el.attrib:
                    code.extend(self._compile_directive(el, compile_context, directive, level))
            elif directive == 'att':
                code.extend(self._compile_directive(el, compile_context, directive, level))
            elif directive == 'options':
                if any(name.startswith('t-options-') for name in el.attrib):
                    code.extend(self._compile_directive(el, compile_context, directive, level))
            elif directive == 'nocache':
                if any(name.startswith('t-nocache-') for name in el.attrib):
                    code.extend(self._compile_directive(el, compile_context, directive, level))

        # compile unordered directives still present on the element
        for att in el.attrib:
            if att not in SPECIAL_DIRECTIVES and att.startswith('t-') and getattr(self, f"_compile_directive_{att[2:].replace('-', '_')}", None):
                code.extend(self._compile_directive(el, compile_context, directive, level))

        remaining = set(el.attrib) - SPECIAL_DIRECTIVES
        if remaining:
            _logger.warning('Unknown directives or unused attributes: %s in %s', remaining, compile_context['template'])

        return code

    @QwebTracker.wrap_compile_directive
    def _compile_directive(self, el, compile_context, directive, level):
        compile_handler = getattr(self, f"_compile_directive_{directive.replace('-', '_')}", None)
        return compile_handler(el, compile_context, level)

    # compile directives

    def _compile_directive_debug(self, el, compile_context, level):
        """Compile `t-debug` expressions into a python code as a list of
        strings.

        The code will contains the call to the debugger chosen from the valid
        list.
        """
        debugger = el.attrib.pop('t-debug')
        code = []
        if compile_context.get('dev_mode'):
            code.append(indent_code(f"self._debug_trace({debugger!r}, values)", level))
        else:
            _logger.warning("@t-debug in template is only available in qweb dev mode")
        return code

    def _compile_directive_options(self, el, compile_context, level):
        """
        compile t-options and add to the dict the t-options-xxx. Will create
        the dictionary ``values['__qweb_options__']`` in compiled code.
        """
        code = []
        dict_options = []
        for key in list(el.attrib):
            if key.startswith('t-options-'):
                value = el.attrib.pop(key)
                option_name = key[10:]
                dict_options.append(f'{option_name!r}:{self._compile_expr(value)}')

        t_options = el.attrib.pop('t-options', None)
        if t_options and dict_options:
            code.append(indent_code(f"values['__qweb_options__'] = {{**{self._compile_expr(t_options)}, {', '.join(dict_options)}}}", level))
        elif dict_options:
            code.append(indent_code(f"values['__qweb_options__'] = {{{', '.join(dict_options)}}}", level))
        elif t_options:
            code.append(indent_code(f"values['__qweb_options__'] = {self._compile_expr(t_options)}", level))
        else:
            code.append(indent_code("values['__qweb_options__'] = {}", level))

        el.set('t-consumed-options', str(bool(code)))

        return code

    def _compile_directive_consumed_options(self, el, compile_context, level):
        raise SyntaxError('the t-options must be on the same tag as a directive that consumes it (for example: t-out, t-field, t-call)')

    def _compile_directive_att(self, el, compile_context, level):
        """ Compile the attributes of the given elements.

        The compiled function will create the ``values['__qweb_attrs__']``
        dictionary. Then the dictionary will be output.


        The new namespaces of the current element.

        The static attributes (not prefixed by ``t-``) are add to the
        dictionary in first.

        The dynamic attributes values will be add after. The dynamic
        attributes has different origins.
        - value from key equal to ``t-att``: python dictionary expression;
        - value from keys that start with ``t-att-``: python expression;
        - value from keys that start with ``t-attf-``: format string
            expression.
        """
        code = [indent_code("attrs = values['__qweb_attrs__'] = {}", level)]

        # Compile the introduced new namespaces of the given element.
        #
        # Add the found new attributes into the `attrs` dictionary like
        # the static attributes.
        if el.nsmap:
            for ns_prefix, ns_definition in set(el.nsmap.items()) - set(compile_context['nsmap'].items()):
                key = 'xmlns'
                if ns_prefix is not None:
                    key = f'xmlns:{ns_prefix}'
                code.append(indent_code(f'attrs[{key!r}] = {ns_definition!r}', level))

        # Compile the static attributes of the given element.
        #
        # Etree will also remove the ns prefixes indirection in the
        # attributes. As we only have the namespace definition, we'll use
        # an nsmap where the keys are the definitions and the values the
        # prefixes in order to get back the right prefix and restore it.
        if any(not name.startswith('t-') for name in el.attrib):
            nsprefixmap = {v: k for k, v in chain(compile_context['nsmap'].items(), el.nsmap.items())}
            for key in list(el.attrib):
                if not key.startswith('t-'):
                    value = el.attrib.pop(key)
                    attrib_qname = etree.QName(key)
                    if attrib_qname.namespace:
                        key = f'{nsprefixmap[attrib_qname.namespace]}:{attrib_qname.localname}'
                    code.append(indent_code(f'attrs[{key!r}] = {value!r}', level))

        # Compile the dynamic attributes of the given element. All
        # attributes will be add to the ``attrs`` dictionary in the
        # compiled function.
        for key in list(el.attrib):
            if key.startswith('t-attf-'):
                value = el.attrib.pop(key)
                code.append(indent_code(f"attrs[{key[7:]!r}] = {self._compile_format(value)}", level))
            elif key.startswith('t-att-'):
                value = el.attrib.pop(key)
                code.append(indent_code(f"attrs[{key[6:]!r}] = {self._compile_expr(value)}", level))
            elif key == 't-att':
                value = el.attrib.pop(key)
                code.append(indent_code(f"""
                    atts_value = {self._compile_expr(value)}
                    if isinstance(atts_value, dict):
                        attrs.update(atts_value)
                    elif isinstance(atts_value, (list, tuple)) and not isinstance(atts_value[0], (list, tuple)):
                        attrs.update([atts_value])
                    elif isinstance(atts_value, (list, tuple)):
                        attrs.update(dict(atts_value))
                    """, level))

        return code

    def _compile_directive_tag_open(self, el, compile_context, level):
        """ Compile the opening tag with attributes of the given element into
        a list of python code line.

        The compiled function will fill the ``attrs`` dictionary. Then the
        ``attrs`` dictionary will be output and reset the value of ``attrs``.

        The static attributes (not prefixed by ``t-``) are add to the
        ``attrs`` dictionary in first.

        The dynamic attributes values will be add after. The dynamic
        attributes has different origins.
        - value from key equal to ``t-att``: python dictionary expression;
        - value from keys that start with ``t-att-``: python expression;
        - value from keys that start with ``t-attf-``: format string
            expression.
        """

        el_tag = el.attrib.pop('t-tag-open', None)
        if not el_tag:
            return []

        # open the open tag
        self._append_text(f"<{el_tag}", compile_context)

        code = self._flush_text(compile_context, level)

        # Generates the part of the code that prost process and output the
        # attributes from ``attrs`` dictionary. Consumes `attrs` dictionary
        # and reset it.
        #
        # Use str(value) to change Markup into str and escape it, then use str
        # to avoid the escaping of the other html content.
        code.append(indent_code(f"""
            attrs = values.pop('__qweb_attrs__', None)
            if attrs:
                tagName = {el.tag!r}
                attrs = self._post_processing_att(tagName, attrs)
                for name, value in attrs.items():
                    if value or isinstance(value, str):
                        yield f' {{escape(str(name))}}="{{escape(str(value))}}"'
        """, level))

        # close the open tag
        if 't-tag-close' in el.attrib:
            self._append_text('>', compile_context)
        else:
            self._append_text('/>', compile_context)

        return code

    def _compile_directive_tag_close(self, el, compile_context, level):
        """ Compile the closing tag of the given element into string.
        Returns an empty list because it's use only `_append_text`.
        """
        el_tag = el.attrib.pop("t-tag-close", None)
        if el_tag:
            self._append_text(f'</{el_tag}>', compile_context)
        return []

    def _compile_directive_set(self, el, compile_context, level):
        """Compile `t-set` expressions into a python code as a list of
        strings.

        There are 3 kinds of `t-set`:
        * `t-value` containing python code;
        * `t-valuef` containing strings to format;
        * whose value is the content of the tag (being Markup safe).

        The code will contain the assignment of the dynamically generated value.
        """

        code = self._flush_text(compile_context, level, rstrip=el.tag.lower() == 't')

        if 't-set' in el.attrib:
            varname = el.attrib.pop('t-set')
            if varname == "":
                raise KeyError('t-set')
            if varname != T_CALL_SLOT and varname[0] != '{' and not VARNAME_REGEXP.match(varname):
                raise ValueError('The varname can only contain alphanumeric characters and underscores.')

            if 't-value' in el.attrib or 't-valuef' in el.attrib or varname[0] == '{':
                el.attrib.pop('t-inner-content') # The content is considered empty.
                if varname == T_CALL_SLOT:
                    raise SyntaxError('t-set="0" should not be set from t-value or t-valuef')

            if 't-value' in el.attrib:
                expr = el.attrib.pop('t-value') or 'None'
                code.append(indent_code(f"values[{varname!r}] = {self._compile_expr(expr)}", level))
            elif 't-valuef' in el.attrib:
                exprf = el.attrib.pop('t-valuef')
                code.append(indent_code(f"values[{varname!r}] = {self._compile_format(exprf)}", level))
            elif varname[0] == '{':
                code.append(indent_code(f"values.update({self._compile_expr(varname)})", level))
            else:
                # set the content as value
                content = (
                    self._compile_directive(el, compile_context, 'inner-content', 1) +
                    self._flush_text(compile_context, 1))
                if content:
                    def_name = compile_context['make_name']('t_set')
                    compile_context['template_functions'][def_name] = [f"def {def_name}(self, values):"] + content
                    code.append(indent_code(f"""
                            t_set = []
                            for item in {def_name}(self, values):
                                if isinstance(item, str):
                                    t_set.append(item)
                                else:
                                    ref, function_name, cached_values = item
                                    t_nocache_function = values['__qweb_loaded_values'].get(function_name)
                                    if not t_nocache_function:
                                        t_call_template_functions, def_name = self._compile(ref)
                                        t_nocache_function = t_call_template_functions[function_name]

                                    nocache_values = values['__qweb_root_values'].copy()
                                    nocache_values.update(cached_values)
                                    t_set.extend(t_nocache_function(self, nocache_values))
                        """, level))
                    expr = "Markup(''.join(t_set))"
                else:
                    expr = "''"
                code.append(indent_code(f"values[{varname!r}] = {expr}", level))

        return code

    def _compile_directive_value(self, el, compile_context, level):
        """Compile `t-value` expressions into a python code as a list of strings.

        This method only check if this attributes is on the same node of a
         `t-set` attribute.
        """
        raise SyntaxError("t-value must be on the same node of t-set")

    def _compile_directive_valuef(self, el, compile_context, level):
        """Compile `t-valuef` expressions into a python code as a list of strings.

        This method only check if this attributes is on the same node of a
         `t-set` attribute.
        """
        raise SyntaxError("t-valuef must be on the same node of t-set")

    def _compile_directive_inner_content(self, el, compile_context, level):
        """Compiles the content of the element (is the technical `t-inner-content`
        directive created by QWeb) into a python code as a list of
        strings.

        The code will contains the text content of the node or the compliled
        code from the recursive call of ``_compile_node``.
        """
        el.attrib.pop('t-inner-content', None)

        if el.nsmap:
            # Update the dict of inherited namespaces before continuing the recursion. Note:
            # since `compile_context['nsmap']` is a dict (and therefore mutable) and we do **not**
            # want changes done in deeper recursion to bevisible in earlier ones, we'll pass
            # a copy before continuing the recursion and restore the original afterwards.
            compile_context = dict(compile_context, nsmap=el.nsmap)

        if el.text is not None:
            self._append_text(el.text, compile_context)
        body = []
        for item in el:
            if isinstance(item, etree._Comment):
                if compile_context.get('preserve_comments'):
                    self._append_text(f"<!--{item.text}-->", compile_context)
            elif isinstance(item, etree._ProcessingInstruction):
                if compile_context.get('preserve_comments'):
                    self._append_text(f"<?{item.target} {item.text}?>", compile_context)
            else:
                body.extend(self._compile_node(item, compile_context, level))
            # comments can also contains tail text
            if item.tail is not None:
                self._append_text(item.tail, compile_context)
        return body

    def _compile_directive_if(self, el, compile_context, level):
        """Compile `t-if` expressions into a python code as a list of strings.

        The code will contain the condition `if`, `else` and `elif` part that
        wrap the rest of the compiled code of this element.
        """
        expr = el.attrib.pop('t-if', el.attrib.pop('t-elif', None))

        assert not expr.isspace(), 't-if or t-elif expression should not be empty.'

        strip = self._rstrip_text(compile_context)  # the withspaces is visible only when display a content
        if el.tag.lower() == 't' and el.text and LSTRIP_REGEXP.search(el.text):
            strip = ''  # remove technical spaces
        code = self._flush_text(compile_context, level)

        code.append(indent_code(f"if {self._compile_expr(expr)}:", level))
        body = []
        if strip:
            self._append_text(strip, compile_context)
        body.extend(
            self._compile_directives(el, compile_context, level + 1) +
            self._flush_text(compile_context, level + 1, rstrip=True))
        code.extend(body or [indent_code('pass', level + 1)])

        # Look for the else or elif conditions
        next_el = el.getnext()
        comments_to_remove = []
        while isinstance(next_el, etree._Comment):
            comments_to_remove.append(next_el)
            next_el = next_el.getnext()

        # If there is a t-else directive, the comment nodes are deleted
        # and the t-else or t-elif is validated.
        if next_el is not None and {'t-else', 't-elif'} & set(next_el.attrib):
            # Insert a flag to allow t-else or t-elif rendering.
            next_el.attrib['t-else-valid'] = 'True'

            # remove comment node
            parent = el.getparent()
            for comment in comments_to_remove:
                parent.remove(comment)
            if el.tail and not el.tail.isspace():
                raise SyntaxError("Unexpected non-whitespace characters between t-if and t-else directives")
            el.tail = None

            # You have to render the `t-else` and `t-elif` here in order
            # to be able to put the log. Otherwise, the parent's
            # `t-inner-content`` directive will render the different
            # nodes without taking indentation into account such as:
            #    if (if_expression):
            #         content_if
            #    log ['last_path_node'] = path
            #    else:
            #       content_else

            code.append(indent_code("else:", level))
            body = []
            if strip:
                self._append_text(strip, compile_context)
            body.extend(
                self._compile_node(next_el, compile_context, level + 1)+
                self._flush_text(compile_context, level + 1, rstrip=True))
            code.extend(body or [indent_code('pass', level + 1)])

            # Insert a flag to avoid the t-else or t-elif rendering when
            # the parent t-inner-content dirrective compile his
            # children.
            next_el.attrib['t-qweb-skip'] = 'True'

        return code

    def _compile_directive_elif(self, el, compile_context, level):
        """Compile `t-elif` expressions into a python code as a list of
        strings. This method is linked with the `t-if` directive.

        Check if this directive is valide, the t-qweb-skip flag and call
        `t-if` directive
        """
        if not el.attrib.pop('t-else-valid', None):
            raise SyntaxError("t-elif directive must be preceded by t-if or t-elif directive")

        return self._compile_directive_if(el, compile_context, level)

    def _compile_directive_else(self, el, compile_context, level):
        """Compile `t-else` expressions into a python code as a list of strings.
        This method is linked with the `t-if` directive.

        Check if this directive is valide and add the t-qweb-skip flag.
        """
        if not el.attrib.pop('t-else-valid', None):
            raise SyntaxError("t-elif directive must be preceded by t-if or t-elif directive")
        el.attrib.pop('t-else')
        return []

    def _compile_directive_groups(self, el, compile_context, level):
        """Compile `t-groups` expressions into a python code as a list of
        strings.

        The code will contain the condition `if self.user_has_groups(groups)`
        part that wrap the rest of the compiled code of this element.
        """
        groups = el.attrib.pop('t-groups', el.attrib.pop('groups', None))

        strip = self._rstrip_text(compile_context)
        code = self._flush_text(compile_context, level)
        code.append(indent_code(f"if self.user_has_groups({groups!r}):", level))
        if strip and el.tag.lower() != 't':
            self._append_text(strip, compile_context)
        code.extend([
            *self._compile_directives(el, compile_context, level + 1),
            *self._flush_text(compile_context, level + 1, rstrip=True),
        ] or [indent_code('pass', level + 1)])
        return code

    def _compile_directive_foreach(self, el, compile_context, level):
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

        if not expr_as:
            raise KeyError('t-as')

        if not VARNAME_REGEXP.match(expr_as):
            raise ValueError(f'The varname {expr_as!r} can only contain alphanumeric characters and underscores.')

        if el.tag.lower() == 't':
            self._rstrip_text(compile_context)

        code = self._flush_text(compile_context, level)

        content_foreach = (
            self._compile_directives(el, compile_context, level + 1) +
            self._flush_text(compile_context, level + 1, rstrip=True))

        t_foreach = compile_context['make_name']('t_foreach')
        size = compile_context['make_name']('size')
        has_value = compile_context['make_name']('has_value')

        if expr_foreach.isdigit():
            code.append(indent_code(f"""
                values[{expr_as + '_size'!r}] = {size} = {int(expr_foreach)}
                {t_foreach} = range({size})
                {has_value} = False
            """, level))
        else:
            code.append(indent_code(f"""
                {t_foreach} = {self._compile_expr(expr_foreach)} or []
                if isinstance({t_foreach}, Sized):
                    values[{expr_as + '_size'!r}] = {size} = len({t_foreach})
                elif ({t_foreach}).__class__ == int:
                    values[{expr_as + '_size'!r}] = {size} = {t_foreach}
                    {t_foreach} = range({size})
                else:
                    {size} = None
                {has_value} = False
                if isinstance({t_foreach}, Mapping):
                    {t_foreach} = {t_foreach}.items()
                    {has_value} = True
            """, level))

        code.append(indent_code(f"""
                for index, item in enumerate({t_foreach}):
                    values[{expr_as + '_index'!r}] = index
                    if {has_value}:
                        values[{expr_as!r}], values[{expr_as + '_value'!r}] = item
                    else:
                        values[{expr_as!r}] = values[{expr_as + '_value'!r}] = item
                    values[{expr_as + '_first'!r}] = values[{expr_as + '_index'!r}] == 0
                    if {size} is not None:
                        values[{expr_as + '_last'!r}] = index + 1 == {size}
                    values[{expr_as + '_odd'!r}] = index % 2
                    values[{expr_as + '_even'!r}] = not values[{expr_as + '_odd'!r}]
                    values[{expr_as + '_parity'!r}] = 'odd' if values[{expr_as + '_odd'!r}] else 'even'
            """, level))

        code.extend(content_foreach or indent_code('continue', level + 1))

        return code

    def _compile_directive_as(self, el, compile_context, level):
        """Compile `t-as` expressions into a python code as a list of strings.

        This method only check if this attributes is on the same node of a
         `t-foreach` attribute.
        """
        if 't-foreach' not in el.attrib:
            raise SyntaxError("t-as must be on the same node of t-foreach")
        return []

    def _compile_directive_out(self, el, compile_context, level):
        """Compile `t-out` expressions into a python code as a list of
        strings.

        The code will contain evalution and rendering of the compiled value. If
        the compiled value is None or False, the tag is not added to the render
        (Except if the widget forces rendering or there is default content).
        (eg: `<t t-out="my_value">Default content if falsy</t>`)

        The output can have some rendering option with `t-options-widget` or
        `t-options={'widget': ...}. At rendering time, The compiled code will
        call ``_get_widget`` method or ``_get_field`` method for `t-field`.

        A `t-field` will necessarily be linked to the value of a record field
        (eg: `<span t-field="record.field_name"/>`), a t-out` can be applied
        to any value (eg: `<span t-out="10" t-options-widget="'float'"/>`).
        """
        ttype = 't-out'
        expr = el.attrib.pop('t-out', None)
        if expr is None:
            ttype = 't-field'
            expr = el.attrib.pop('t-field', None)
            if expr is None:
                # deprecated use.
                ttype = 't-esc'
                expr = el.attrib.pop('t-esc', None)
                if expr is None:
                    ttype = 't-raw'
                    expr = el.attrib.pop('t-raw')

        code = self._flush_text(compile_context, level)

        code_options = el.attrib.pop('t-consumed-options', 'None')
        tag_open = (
            self._compile_directive(el, compile_context, 'tag-open', level + 1) +
            self._flush_text(compile_context, level + 1))
        tag_close = (
            self._compile_directive(el, compile_context, 'tag-close', level + 1) +
            self._flush_text(compile_context, level + 1))
        default_body = (
            self._compile_directive(el, compile_context, 'inner-content', level + 1) +
            self._flush_text(compile_context, level + 1))

        # The generated code will set the values of the content, attrs (used to
        # output attributes) and the force_display (if the widget or field
        # mark force_display as True, the tag will be inserted in the output
        # even the value of content is None and without default value)

        if expr == T_CALL_SLOT and code_options != 'True':
            code.append(indent_code("if True:", level))
            code.extend(tag_open)
            code.append(indent_code(f"yield from values.get({T_CALL_SLOT}, [])", level + 1))
            code.extend(tag_close)
            return code
        elif ttype == 't-field':
            record, field_name = expr.rsplit('.', 1)
            code.append(indent_code(f"""
                field_attrs, content, force_display = self._get_field({self._compile_expr(record, raise_on_missing=True)}, {field_name!r}, {expr!r}, {el.tag!r}, values.pop('__qweb_options__', {{}}), values)
                if values.get('__qweb_attrs__') is None:
                    values['__qweb_attrs__'] = field_attrs
                else:
                    values['__qweb_attrs__'].update(field_attrs)
                if content is not None and content is not False:
                    content = self._compile_to_str(content)
                """, level))
            force_display_dependent = True
        else:
            if expr == T_CALL_SLOT:
                code.append(indent_code(f"content = Markup(''.join(values.get({T_CALL_SLOT}, [])))", level))
            else:
                code.append(indent_code(f"content = {self._compile_expr(expr)}", level))

            if code_options == 'True':
                code.append(indent_code(f"""
                    widget_attrs, content, force_display = self._get_widget(content, {expr!r}, {el.tag!r}, values.pop('__qweb_options__', {{}}), values)
                    if values.get('__qweb_attrs__') is None:
                        values['__qweb_attrs__'] = widget_attrs
                    else:
                        values['__qweb_attrs__'].update(widget_attrs)
                    content = self._compile_to_str(content)
                    """, level))
                force_display_dependent = True
            else:
                force_display_dependent = False

            if ttype == 't-raw':
                # deprecated use.
                code.append(indent_code("""
                    if content is not None and content is not False:
                        content = Markup(content)
                """, level))

        # The generated code will create the output tag with all attribute.
        # If the value is not falsy or if there is default content or if it's
        # in force_display mode, the tag is add into the output.

        el.attrib.pop('t-tag', None) # code generating the output is done here

        # generate code to display the tag if the value is not Falsy

        code.append(indent_code("if content is not None and content is not False:", level))
        code.extend(tag_open)
        # Use str to avoid the escaping of the other html content because the
        # yield generator MarkupSafe values will be join into an string in
        # `_render`.
        code.append(indent_code("yield str(escape(content))", level + 1))
        code.extend(tag_close)

        # generate code to display the tag with default content if the value is
        # Falsy

        if default_body or compile_context['_text_concat']:
            _text_concat = list(compile_context['_text_concat'])
            compile_context['_text_concat'].clear()
            code.append(indent_code("else:", level))
            code.extend(tag_open)
            code.extend(default_body)
            compile_context['_text_concat'].extend(_text_concat)
            code.extend(tag_close)
        elif force_display_dependent:

            # generate code to display the tag if it's the force_diplay mode.

            if tag_open + tag_close:
                code.append(indent_code("elif force_display:", level))
                code.extend(tag_open + tag_close)

            code.append(indent_code("""else: values.pop('__qweb_attrs__', None)""", level))

        return code

    def _compile_directive_esc(self, el, compile_context, level):
        # deprecated use.
        if compile_context.get('dev_mode'):
            _logger.warning(
                "Found deprecated directive @t-esc=%r in template %r. Replace by @t-out",
                el.get('t-esc'),
                compile_context.get('ref', '<unknown>'),
            )
        return self._compile_directive_out(el, compile_context, level)

    def _compile_directive_raw(self, el, compile_context, level):
        # deprecated use.
        _logger.warning(
            "Found deprecated directive @t-raw=%r in template %r. Replace by "
            "@t-out, and explicitely wrap content in `Markup` if "
            "necessary (which likely is not the case)",
            el.get('t-raw'),
            compile_context.get('ref', '<unknown>'),
        )
        return self._compile_directive_out(el, compile_context, level)

    def _compile_directive_field(self, el, compile_context, level):
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
            "QWeb widgets do not work correctly on %r elements" % tagName
        assert tagName != 't',\
            "t-field can not be used on a t element, provide an actual HTML node"
        assert "." in el.get('t-field'),\
            "t-field must have at least a dot like 'record.field_name'"

        return self._compile_directive_out(el, compile_context, level)

    def _compile_directive_call(self, el, compile_context, level):
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

        nsmap = compile_context.get('nsmap')

        code = self._flush_text(compile_context, level, rstrip=el.tag.lower() == 't')

        # options
        el.attrib.pop('t-consumed-options', None)
        code.append(indent_code("t_call_options = values.pop('__qweb_options__', {})", level))
        if nsmap:
            # update this dict with the current nsmap so that the callee know
            # if he outputting the xmlns attributes is relevenat or not
            nsmap = []
            for key, value in compile_context['nsmap'].items():
                if isinstance(key, str):
                    nsmap.append(f'{key!r}:{value!r}')
                else:
                    nsmap.append(f'None:{value!r}')
            code.append(indent_code(f"t_call_options.update(nsmap={{{', '.join(nsmap)}}})", level))

        # values (t-out="0" from content and variables from t-set)
        def_name = compile_context['make_name']('t_call')

        # values from content (t-out="0" and t-set inside the content)
        code_content = [f"def {def_name}(self, values):"]
        code_content.extend(self._compile_directive(el, compile_context, 'inner-content', 1))
        self._append_text('', compile_context) # To ensure the template function is a generator and doesn't become a regular function
        code_content.extend(self._flush_text(compile_context, 1, rstrip=True))
        compile_context['template_functions'][def_name] = code_content

        code.append(indent_code(f"""
            t_call_values = values.copy()
            t_call_values[{T_CALL_SLOT}] = list({def_name}(self, t_call_values))
            """, level))

        template = self._compile_format(expr)

        # call
        code.append(indent_code(f"""
            irQweb = self.with_context(**t_call_options)
            template = {template}
            if template.isnumeric():
                template = int(template)
            t_call_template_functions, def_name = irQweb._compile(template)
            render_template = t_call_template_functions[def_name]
            yield from render_template(irQweb, t_call_values)
            """, level))

        return code

    def _compile_directive_lang(self, el, compile_context, level):
        if 't-call' not in el.attrib:
            raise SyntaxError("t-lang is an alias of t-options-lang but only available on the same node of t-call")
        el.attrib['t-options-lang'] = el.attrib.pop('t-lang')
        return self._compile_node(el, compile_context, level)

    def _compile_directive_call_assets(self, el, compile_context, level):
        """ This special 't-call-assets' tag can be used in order to aggregate/minify javascript and css assets"""
        if len(el) > 0:
            raise SyntaxError("t-call-assets cannot contain children nodes")

        code = self._flush_text(compile_context, level)
        xmlid = el.attrib.pop('t-call-assets')
        css = self._compile_bool(el.attrib.pop('t-css', True))
        js = self._compile_bool(el.attrib.pop('t-js', True))
        async_load = self._compile_bool(el.attrib.pop('async_load', False))
        defer_load = self._compile_bool(el.attrib.pop('defer_load', False))
        lazy_load = self._compile_bool(el.attrib.pop('lazy_load', False))
        media = el.attrib.pop('media', False)
        code.append(indent_code(f"""
            t_call_assets_nodes = self._get_asset_nodes(
                {xmlid!r},
                css={css},
                js={js},
                debug=values.get("debug"),
                async_load={async_load},
                defer_load={defer_load},
                lazy_load={lazy_load},
                media={media!r},
            )
        """.strip(), level))

        code.append(indent_code("""
            for index, (tagName, asset_attrs, content) in enumerate(t_call_assets_nodes):
                if index:
                    yield '\\n        '
                yield '<'
                yield tagName

                attrs = self._post_processing_att(tagName, asset_attrs)
                for name, value in attrs.items():
                    if value or isinstance(value, str):
                        yield f' {escape(str(name))}="{escape(str(value))}"'

                if not content and tagName in VOID_ELEMENTS:
                    yield '/>'
                else:
                    yield '>'
                    if content:
                      yield content
                    yield '</'
                    yield tagName
                    yield '>'
                """, level))

        return code

    def _compile_directive_cache(self, el, compile_context, level):
        """Compile the `t-cache` tuple expression into a key cache.

        The `t-cache` directive allows you to keep the rendered result
        of a template part. The supplied key must be a tuple. This tuple
        can contain recordset in this case the zone will be invalidated
        each time the write_date of these records changes.
        The values are scoped into the `t-cache` and are not available
        outside.
        see: `t-nocache`
        """
        expr = el.attrib.pop('t-cache')
        code = self._flush_text(compile_context, level)

        def_name = compile_context['make_name']('t_cache')

        # Generate the content function
        def_code = [indent_code(f"""def {def_name}(self, values):""", 0)]
        def_content = self._compile_directives(el, compile_context, 1)
        if def_content and not compile_context['_text_concat']:
            self._append_text('', compile_context) # To ensure the template function is a generator and doesn't become a regular function
        def_code.extend(def_content)
        def_code.extend(self._flush_text(compile_context, 1))
        compile_context['template_functions'][def_name] = def_code

        # Get the dynamic key for the cache and load the content.
        # The t-nocache yield a tuple (ref, function name) instead of a
        # When reading tuple coming from t-nocache, we check if the
        # method is already known otherwise the corresponding template
        # and its functions are loaded.
        code.append(indent_code(f"""
            template_cache_key = {self._compile_expr(expr)} if not self.env.context.get('is_t_cache_disabled') else None
            cache_key = self._get_cache_key(template_cache_key) if template_cache_key else None
            uniq_cache_key = cache_key and ({str(self.env.context['__qweb_base_key_cache'])!r}, '{def_name}_cache', cache_key)
            loaded_values = values['__qweb_loaded_values']
            def {def_name}_cache():
                content = []
                text = []
                for item in {def_name}(self, {{**values, '__qweb_in_cache': True}}):
                    if isinstance(item, str):
                        text.append(item)
                    else:
                        content.append(''.join(text))
                        content.append(item)
                        text = []
                if text:
                    content.append(''.join(text))
                return content
            cache_content = self._load_values(uniq_cache_key, {def_name}_cache, loaded_values)
            if values.get('__qweb_in_cache'):
                yield from cache_content
            else:
                for item in cache_content:
                    if isinstance(item, str):
                        yield item
                    else:
                        ref, function_name, cached_values = item
                        t_nocache_function = loaded_values.get(function_name)
                        if not t_nocache_function:
                            t_call_template_functions, def_name = self._compile(ref)
                            t_nocache_function = t_call_template_functions[function_name]

                        nocache_values = values['__qweb_root_values'].copy()
                        nocache_values.update(cached_values)
                        yield ''.join(t_nocache_function(self, nocache_values))
            """, level))

        return code

    def _compile_directive_nocache(self, el, compile_context, level):
        """
        The `t-nocache` directive makes it possible to force rendering
        of a part even if it is in a `t-cache`. The values available in
        the `t-nocache` are the one provided when calling the template
        (and therefore ignores any t-set that could have been done).

        The `t-nocache-*` are the values whose result of the
        expression will be cached and added to the root's values when
        rendering the no cache part. Only primitive types can be cached.

        see: `t-cache`
        """
        if 't-nocache' not in el.attrib:
            raise SyntaxError("t-nocache-* must be on the same node as t-nocache")

        el.attrib.pop('t-nocache')
        code = self._flush_text(compile_context, level)

        # t-nocache-* will generate the values to put in cache
        # must cosume this attributes before generate the cached content.
        code_cache_values = []
        for key in list(el.attrib):
            if key.startswith('t-nocache-'):
                expr = el.attrib.pop(key)
                varname = key[10:]
                if not VARNAME_REGEXP.match(varname):
                    raise ValueError(f'The varname {varname!r} can only contain alphanumeric characters and underscores.')
                code_cache_values.append(indent_code(f"""
                    cached_value = {self._compile_expr(expr)}
                    if cached_value is not None and not isinstance(cached_value, (str, int, float, bool)):
                        raise ValueError(f'''The value type of {key!r} cannot be cached: {{cached_value!r}}''')
                    cached_values[{varname!r}] = cached_value
                """, level + 1))

        # generate the cached content method
        def_name = compile_context['make_name']('t_nocache')
        def_code = [f"def {def_name}(self, values):"]
        def_code.append(indent_code("try:", 1))
        def_content = self._compile_directives(el, compile_context, 2)
        if def_content and not compile_context['_text_concat']:
            self._append_text('', compile_context) # To ensure the template function is a generator and doesn't become a regular function
        def_code.extend(def_content)
        def_code.extend(self._flush_text(compile_context, 2))
        def_code.append(indent_code(f"""
                except QWebException:
                    raise
                except Exception as e:
                    raise QWebException("Error while render the template",
                        self, template, ref={compile_context['ref']!r}, code=code) from e
            """, 1))
        compile_context['template_functions'][def_name] = def_code

        # if the nocache is inside a cache return a tuple with the method name and the cached values
        code.append(indent_code("""
            if values.get('__qweb_in_cache'):
                cached_values = {}
            """, level))
        code.extend(code_cache_values)
        code.append(indent_code(f"yield ({compile_context['template']!r}, {def_name!r}, cached_values)", level+1))
        # else render the content
        code.append(indent_code(f"""
            else:
                yield from {def_name}(self, values)
            """, level))

        return code

    # methods called by the compiled function at rendering time.

    def _debug_trace(self, debugger, values):
        """Method called at running time to load debugger."""
        if debugger in SUPPORTED_DEBUGGER:
            __import__(debugger).set_trace()
        else:
            raise ValueError(f"unsupported t-debug value: {debugger}")

    def _post_processing_att(self, tagName, atts):
        """ Method called at compile time for the static node and called at
            runing time for the dynamic attributes.

            This method may be overwrited to filter or modify the attributes
            (during compilation for static node or after they compilation in
            the case of dynamic elements).

            @returns dict
        """
        return atts

    def _get_field(self, record, field_name, expression, tagName, field_options, values):
        """Method called at compile time to return the field value.

        :returns: tuple:
            * dict: attributes
            * string or None: content
            * boolean: force_display display the tag if the content and default_content are None
        """
        field = record._fields[field_name]

        # adds generic field options
        field_options['tagName'] = tagName
        field_options['expression'] = expression
        field_options['type'] = field_options.get('widget', field.type)
        inherit_branding = (
                self.env.context['inherit_branding']
                if 'inherit_branding' in self.env.context
                else self.env.context.get('inherit_branding_auto') and record.check_access_rights('write', False))
        field_options['inherit_branding'] = inherit_branding
        translate = self.env.context.get('edit_translations') and values.get('translatable') and field.translate
        field_options['translate'] = translate

        # field converter
        model = 'ir.qweb.field.' + field_options['type']
        converter = self.env[model] if model in self.env else self.env['ir.qweb.field']

        # get content (the return values from fields are considered to be markup safe)
        content = converter.record_to_html(record, field_name, field_options)
        attributes = converter.attributes(record, field_name, field_options, values)

        return (attributes, content, inherit_branding or translate)

    def _get_widget(self, value, expression, tagName, field_options, values):
        """Method called at compile time to return the widget value.

        :returns: tuple:
            * dict: attributes
            * string or None: content
            * boolean: force_display display the tag if the content and default_content are None
        """
        field_options['type'] = field_options['widget']
        field_options['tagName'] = tagName
        field_options['expression'] = expression
        inherit_branding = self.env.context.get('inherit_branding')
        field_options['inherit_branding'] = inherit_branding

        # field converter
        model = 'ir.qweb.field.' + field_options['type']
        converter = self.env[model] if model in self.env else self.env['ir.qweb.field']

        # get content (the return values from widget are considered to be markup safe)
        content = converter.value_to_html(value, field_options)
        attributes = {}
        attributes['data-oe-type'] = field_options['type']
        attributes['data-oe-expression'] = field_options['expression']

        return (attributes, content, inherit_branding)

    def _get_asset_nodes(self, bundle, css=True, js=True, debug=False, async_load=False, defer_load=False, lazy_load=False, media=None):
        """Generates asset nodes.
        If debug=assets, the assets will be regenerated when a file which composes them has been modified.
        Else, the assets will be generated only once and then stored in cache.
        """
        if debug and 'assets' in debug:
            return self._generate_asset_nodes(bundle, css, js, debug, async_load, defer_load, lazy_load, media)
        else:
            return self._generate_asset_nodes_cache(bundle, css, js, debug, async_load, defer_load, lazy_load, media)

    # qweb cache feature

    def _get_cache_key(self, cache_key):
        """
            Convert the template cache key item into a hashable key.
            :param cache_key: tuple
            :returns: tuple of hashable items
        """
        if not isinstance(cache_key, (tuple, list)):
            cache_key = (cache_key,)
        keys = []
        for item in cache_key:
            try:
                # use try catch instead of isinstance to detect lazy values
                keys.append(item._name)
                keys.append(tuple(item.ids))
                dates = item.mapped('write_date')
                if dates:
                    keys.append(max(dates).timestamp())
            except AttributeError:
                keys.append(repr(item))
        return tuple(keys)

    def _load_values(self, cache_key, get_value, loaded_values=None):
        """ generate value from the function if the result is not cached. """
        if not cache_key:
            return get_value()

        value = loaded_values and loaded_values.get(cache_key)
        if not value:
            value = self._get_cached_values(cache_key, get_value)
        if loaded_values is not None:
            loaded_values[cache_key] = value
        return value

    # The cache does not need to be invalidated if the 'base_key_cache'
    # in '_compile' method contains the write_date of all inherited views.
    @tools.conditional(
        'xml' not in tools.config['dev_mode'],
        tools.ormcache('cache_key'),
    )
    def _get_cached_values(self, cache_key, get_value):
        """ generate value from the function if the result is not cached. """
        return get_value()

    # other methods used for the asset bundles
    @tools.conditional(
        # in non-xml-debug mode we want assets to be cached forever, and the admin can force a cache clear
        # by restarting the server after updating the source code (or using the "Clear server cache" in debug tools)
        'xml' not in tools.config['dev_mode'],
        tools.ormcache('bundle', 'css', 'js', 'debug', 'async_load', 'defer_load', 'lazy_load', 'media', 'tuple(self.env.context.get(k) for k in self._get_template_cache_keys())'),
    )
    def _generate_asset_nodes_cache(self, bundle, css=True, js=True, debug=False, async_load=False, defer_load=False, lazy_load=False, media=None):
        return self._generate_asset_nodes(bundle, css, js, debug, async_load, defer_load, lazy_load, media)

    @tools.ormcache('bundle', 'defer_load', 'lazy_load', 'media', 'tuple(self.env.context.get(k) for k in self._get_template_cache_keys())')
    def _get_asset_content(self, bundle, defer_load=False, lazy_load=False, media=None):
        asset_paths = self.env['ir.asset']._get_asset_paths(bundle=bundle, css=True, js=True)

        files = []
        remains = []
        for path, *_ in asset_paths:
            ext = path.split('.')[-1]
            is_js = ext in SCRIPT_EXTENSIONS
            is_xml = ext in TEMPLATE_EXTENSIONS
            is_css = ext in STYLE_EXTENSIONS
            if not is_js and not is_xml and not is_css:
                continue

            if is_xml:
                base = get_module_path(bundle.split('.')[0]).rsplit('/', 1)[0]
                if path.startswith(base):
                    path = path[len(base):]

            mimetype = None
            if is_js:
                mimetype = 'text/javascript'
            elif is_css:
                mimetype = f'text/{ext}'
            elif is_xml:
                mimetype = 'text/xml'

            if can_aggregate(path):
                segments = [segment for segment in path.split('/') if segment]
                files.append({
                    'atype': mimetype,
                    'url': path,
                    'filename': get_resource_path(*segments) if segments else None,
                    'content': '',
                    'media': media,
                })
            else:
                if is_js:
                    tag = 'script'
                    attributes = {
                        "type": mimetype,
                    }
                    attributes["data-src" if lazy_load else "src"] = path
                    if defer_load or lazy_load:
                        attributes["defer"] = "defer"
                elif is_css:
                    tag = 'link'
                    attributes = {
                        "type": mimetype,
                        "rel": "stylesheet",
                        "href": path,
                        'media': media,
                    }
                elif is_xml:
                    tag = 'script'
                    attributes = {
                        "type": mimetype,
                        "async": "async",
                        "rel": "prefetch",
                        "data-src": path,
                    }
                remains.append((tag, attributes, None))

        return (files, remains)

    def _get_asset_bundle(self, bundle_name, files, env=None, css=True, js=True):
        return AssetsBundle(bundle_name, files, env=env, css=css, js=js)

    def _generate_asset_nodes(self, bundle, css=True, js=True, debug=False, async_load=False, defer_load=False, lazy_load=False, media=None):
        files, remains = self._get_asset_content(bundle, defer_load=defer_load, lazy_load=lazy_load, media=css and media or None)
        asset = self._get_asset_bundle(bundle, files, env=self.env, css=css, js=js)
        remains = [node for node in remains if (css and node[0] == 'link') or (js and node[0] == 'script')]
        return remains + asset.to_node(css=css, js=js, debug=debug, async_load=async_load, defer_load=defer_load, lazy_load=lazy_load)

    def _get_asset_link_urls(self, bundle, debug=False):
        asset_nodes = self._get_asset_nodes(bundle, js=False, debug=debug)
        return [node[1]['href'] for node in asset_nodes if node[0] == 'link']

    def _pregenerate_assets_bundles(self):
        """
        Pregenerates all assets that may be used in web pages to speedup first loading.
        This may is mainly usefull for tests.

        The current version is looking for all t-call-assets in view to generate the minimal
        set of bundles to generate.

        Current version only generate assets without extra, not taking care of rtl.
        """
        _logger.runbot('Pregenerating assets bundles')

        views = self.env['ir.ui.view'].search([('type', '=', 'qweb'), ('arch_db', 'like', 't-call-assets')])
        js_bundles = set()
        css_bundles = set()
        for view in views:
            for call_asset in etree.fromstring(view.arch_db).xpath("//*[@t-call-assets]"):
                asset = call_asset.get('t-call-assets')
                js = str2bool(call_asset.get('t-js', 'True'))
                css = str2bool(call_asset.get('t-css', 'True'))
                if js:
                    js_bundles.add(asset)
                if css:
                    css_bundles.add(asset)
        nodes = []
        start = time.time()
        for bundle in sorted(js_bundles):
            nodes += self._generate_asset_nodes(bundle, css=False, js=True)
        _logger.info('JS Assets bundles generated in %s seconds', time.time()-start)
        start = time.time()
        for bundle in sorted(css_bundles):
            nodes += self._generate_asset_nodes(bundle, css=True, js=False)
        _logger.info('CSS Assets bundles generated in %s seconds', time.time()-start)
        return nodes


def render(template_name, values, load, **options):
    """ Rendering of a qweb template without database and outside the registry.
    (Widget, field, or asset rendering is not implemented.)
    :param (string|int) template_name: template identifier
    :param dict values: template values to be used for rendering
    :param def load: function like `load(template_name)` which returns an etree
        from the given template name (from initial rendering or template
        `t-call`).
    :param options: used to compile the template
    :returns: bytes marked as markup-safe (decode to :class:`markupsafe.Markup`
                instead of `str`)
    :rtype: MarkupSafe
    """
    class MockPool:
        db_name = None
        _Registry__cache = {}

    class MockIrQWeb(IrQWeb):
        _register = False               # not visible in real registry

        pool = MockPool()

        def _load(self, ref):
            """
            Load the template referenced by ``ref``.

            :returns: The loaded template (as string or etree) and its
                identifier
            :rtype: Tuple[Union[etree, str], Optional[str, int]]
            """
            return self.env.context['load'](ref)

        def _prepare_environment(self, values):
            values['true'] = True
            values['false'] = False
            return self.with_context(is_t_cache_disabled=True, __qweb_loaded_values={})

        def _get_field(self, *args):
            raise NotImplementedError("Fields are not allowed in this rendering mode. Please use \"env['ir.qweb']._render\" method")

        def _get_widget(self, *args):
            raise NotImplementedError("Widgets are not allowed in this rendering mode. Please use \"env['ir.qweb']._render\" method")

        def _get_asset_nodes(self, *args):
            raise NotImplementedError("Assets are not allowed in this rendering mode. Please use \"env['ir.qweb']._render\" method")

    class MockEnv(dict):
        def __init__(self):
            super().__init__()
            self.context = {}

        def __call__(self, cr=None, user=None, context=None, su=None):
            """ Return an mocked environment based and update the sent context.
                Allow to use `ir_qweb.with_context` with sand boxed qweb.
            """
            env = MockEnv()
            env.context.update(self.context if context is None else context)
            return env

    renderer = MockIrQWeb(MockEnv(), tuple(), tuple())
    return renderer._render(template_name, values, load=load, minimal_qcontext=True, **options)
