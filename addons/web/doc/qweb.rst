QWeb
====

QWeb is the template engine used by the OpenERP Web Client. It is an
XML-based templating language, similar to `Genshi
<http://en.wikipedia.org/wiki/Genshi_(templating_language)>`_,
`Thymeleaf <http://en.wikipedia.org/wiki/Thymeleaf>`_ or `Facelets
<http://en.wikipedia.org/wiki/Facelets>`_ with a few peculiarities:

* It's implemented fully in javascript and rendered in the browser.
* Each template file (XML files) contains multiple templates, where
  template engine usually have a 1:1 mapping between template files
  and templates.
* It has special support in OpenERP Web's
  :class:`~instance.web.Widget`, though it can be used outside of
  OpenERP Web (and it's possible to use :class:`~instance.web.Widget`
  without relying on the QWeb integration).

The rationale behind using QWeb instead of a more popular template syntax is
that its extension mechanism is very similar to the openerp view inheritance
mechanism. Like openerp views a QWeb template is an xml tree and therefore
xpath or dom manipulations are easy to performs on it.

Here's an example demonstrating most of the basic QWeb features:

.. code-block:: xml

    <templates>
      <div t-name="example_template" t-attf-class="base #{cls}">
        <h4 t-if="title"><t t-esc="title"/></h4>
        <ul>
          <li t-foreach="items" t-as="item" t-att-class="item_parity">
            <t t-call="example_template.sub">
              <t t-set="arg" t-value="item_value"/>
            </t>
          </li>
        </ul>
      </div>
      <t t-name="example_template.sub">
        <t t-esc="arg.name"/>
        <dl>
          <t t-foreach="arg.tags" t-as="tag" t-if="tag_index lt 5">
            <dt><t t-esc="tag"/></dt>
            <dd><t t-esc="tag_value"/></dd>
          </t>
        </dl>
      </t>
    </templates>

rendered with the following context:

.. code-block:: json

    {
        "class1": "foo",
        "title": "Random Title",
        "items": [
            { "name": "foo", "tags": {"bar": "baz", "qux": "quux"} },
            { "name": "Lorem", "tags": {
                    "ipsum": "dolor",
                    "sit": "amet",
                    "consectetur": "adipiscing",
                    "elit": "Sed",
                    "hendrerit": "ullamcorper",
                    "ante": "id",
                    "vestibulum": "Lorem",
                    "ipsum": "dolor",
                    "sit": "amet"
                }
            }
        ]
    }

will yield this section of HTML document (reformated for readability):

.. code-block:: html

    <div class="base foo">
        <h4>Random Title</h4>
        <ul>
            <li class="even">
                foo
                <dl>
                    <dt>bar</dt>
                    <dd>baz</dd>
                    <dt>qux</dt>
                    <dd>quux</dd>
                </dl>
            </li>
            <li class="odd">
                Lorem
                <dl>
                    <dt>ipsum</dt>
                    <dd>dolor</dd>
                    <dt>sit</dt>
                    <dd>amet</dd>
                    <dt>consectetur</dt>
                    <dd>adipiscing</dd>
                    <dt>elit</dt>
                    <dd>Sed</dd>
                    <dt>hendrerit</dt>
                    <dd>ullamcorper</dd>
                </dl>
            </li>
        </ul>
    </div>

API
---

While QWeb implements a number of attributes and methods for
customization and configuration, only two things are really important
to the user:

.. js:class:: QWeb2.Engine

    The QWeb "renderer", handles most of QWeb's logic (loading,
    parsing, compiling and rendering templates).

    OpenERP Web instantiates one for the user, and sets it to
    ``instance.web.qweb``. It also loads all the template files of the
    various modules into that QWeb instance.

    A :js:class:`QWeb2.Engine` also serves as a "template namespace".

    .. js:function:: QWeb2.Engine.render(template[, context])

        Renders a previously loaded template to a String, using
        ``context`` (if provided) to find the variables accessed
        during template rendering (e.g. strings to display).

        :param String template: the name of the template to render
        :param Object context: the basic namespace to use for template
                               rendering
        :returns: String

    The engine exposes an other method which may be useful in some
    cases (e.g. if you need a separate template namespace with, in
    OpenERP Web, Kanban views get their own :js:class:`QWeb2.Engine`
    instance so their templates don't collide with more general
    "module" templates):

    .. js:function:: QWeb2.Engine.add_template(templates)

        Loads a template file (a collection of templates) in the QWeb
        instance. The templates can be specified as:

        An XML string
            QWeb will attempt to parse it to an XML document then load
            it.

        A URL
            QWeb will attempt to download the URL content, then load
            the resulting XML string.

        A ``Document`` or ``Node``
            QWeb will traverse the first level of the document (the
            child nodes of the provided root) and load any named
            template or template override.

        :type templates: String | Document | Node

    A :js:class:`QWeb2.Engine` also exposes various attributes for
    behavior customization:

    .. js:attribute:: QWeb2.Engine.prefix

        Prefix used to recognize :ref:`directives <qweb-directives>`
        during parsing. A string. By default, ``t``.

    .. js:attribute:: QWeb2.Engine.debug

        Boolean flag putting the engine in "debug mode". Normally,
        QWeb intercepts any error raised during template execution. In
        debug mode, it leaves all exceptions go through without
        intercepting them.

    .. js:attribute:: QWeb2.Engine.jQuery

        The jQuery instance used during :ref:`template inheritance
        <qweb-directives-inheritance>` processing. Defaults to
        ``window.jQuery``.

    .. js:attribute:: QWeb2.Engine.preprocess_node

        A ``Function``. If present, called before compiling each DOM
        node to template code. In OpenERP Web, this is used to
        automatically translate text content and some attributes in
        templates. Defaults to ``null``.

.. _qweb-directives:

Directives
----------

A basic QWeb template is nothing more than an XHTML document (as it
must be valid XML), which will be output as-is. But the rendering can
be customized with bits of logic called "directives". Directives are
attributes elements prefixed by :js:attr:`~QWeb2.Engine.prefix` (this
document will use the default prefix ``t``, as does OpenERP Web).

A directive will usually control or alter the output of the element it
is set on. If no suitable element is available, the prefix itself can
be used as a "no-operation" element solely for supporting directives
(or internal content, which will be rendered). This means:

.. code-block:: xml

    <t>Something something</t>

will simply output the string "Something something" (the element
itself will be skipped and "unwrapped"):

.. code-block:: javascript

    var e = new QWeb2.Engine();
    e.add_template('<templates>\
        <t t-name="test1"><t>Test 1</t></t>\
        <t t-name="test2"><span>Test 2</span></t>\
    </templates>');
    e.render('test1'); // Test 1
    e.render('test2'); // <span>Test 2</span>

.. note::

    The conventions used in directive descriptions are the following:

    * directives are described as compound functions, potentially with
      optional sections. Each section of the function name is an
      attribute of the element bearing the directive.

    * a special parameter is ``BODY``, which does not have a name and
      designates the content of the element.

    * special parameter types (aside from ``BODY`` which remains
      untyped) are ``Name``, which designates a valid javascript
      variable name, ``Expression`` which designates a valid
      javascript expression, and ``Format`` which designates a
      Ruby-style format string (a literal string with
      ``#{Expression}`` inclusions executed and replaced by their
      result)

.. note::

    ``Expression`` actually supports a few extensions on the
    javascript syntax: because some syntactic elements of javascript
    are not compatible with XML and must be escaped, text
    substitutions are performed from forms which don't need to be
    escaped. Thus the following "keyword operators" are available in
    an ``Expression``: ``and`` (maps to ``&&``), ``or`` (maps to
    ``||``), ``gt`` (maps to ``>``), ``gte`` (maps to ``>=``), ``lt``
    (maps to ``<``) and ``lte`` (maps to ``<=``).

.. _qweb-directives-templates:

Defining Templates
++++++++++++++++++

.. _qweb-directive-name:

.. function:: t-name=name

    :param String name: an arbitrary javascript string. Each template
                        name is unique in a given
                        :js:class:`QWeb2.Engine` instance, defining a
                        new template with an existing name will
                        overwrite the previous one without warning.

                        When multiple templates are related, it is
                        customary to use dotted names as a kind of
                        "namespace" e.g. ``foo`` and ``foo.bar`` which
                        will be used either by ``foo`` or by a
                        sub-widget of the widget used by ``foo``.

    Templates can only be defined as the children of the document
    root. The document root's name is irrelevant (it's not checked)
    but is usually ``<templates>`` for simplicity.

    .. code-block:: xml

        <templates>
            <t t-name="template1">
                <!-- template code -->
            </t>
        </templates>

    :ref:`t-name <qweb-directive-name>` can be used on an element with
    an output as well:

    .. code-block:: xml

        <templates>
            <div t-name="template2">
                <!-- template code -->
            </div>
        </templates>

    which ensures the template has a single root (if a template has
    multiple roots and is then passed directly to jQuery, odd things
    occur).

.. _qweb-directives-output:

Output
++++++

.. _qweb-directive-esc:

.. function:: t-esc=content

    :param Expression content:

    Evaluates, html-escapes and outputs ``content``.

.. _qweb-directive-escf:

.. function:: t-escf=content

    :param Format content:

    Similar to :ref:`t-esc <qweb-directive-esc>` but evaluates a
    ``Format`` instead of just an expression.

.. _qweb-directive-raw:

.. function:: t-raw=content

    :param Expression content:

    Similar to :ref:`t-esc <qweb-directive-esc>` but does *not*
    html-escape the result of evaluating ``content``. Should only ever
    be used for known-secure content, or will be an XSS attack vector.

.. _qweb-directive-rawf:

.. function:: t-rawf=content

    :param Format content:

    ``Format``-based version of :ref:`t-raw <qweb-directive-raw>`.

.. _qweb-directive-att:

.. function:: t-att=map

    :param Expression map:

    Evaluates ``map`` expecting an ``Object`` result, sets each
    key:value pair as an attribute (and its value) on the holder
    element:

    .. code-block:: xml

        <span t-att="{foo: 3, bar: 42}"/>

    will yield

    .. code-block:: html

        <span foo="3" bar="42"/>

.. function:: t-att-ATTNAME=value

    :param Name ATTNAME:
    :param Expression value:

    Evaluates ``value`` and sets it on the attribute ``ATTNAME`` on
    the holder element.

    If ``value``'s result is ``undefined``, suppresses the creation of
    the attribute.

.. _qweb-directive-attf:

.. function:: t-attf-ATTNAME=value

    :param Name ATTNAME:
    :param Format value:

    Similar to :ref:`t-att-* <qweb-directive-att>` but the value of
    the attribute is specified via a ``Format`` instead of an
    expression. Useful for specifying e.g. classes mixing literal
    classes and computed ones.

.. _qweb-directives-flow:

Flow Control
++++++++++++

.. _qweb-directive-set:

.. function:: t-set=name (t-value=value | BODY)

    :param Name name:
    :param Expression value:
    :param BODY:

    Creates a new binding in the template context. If ``value`` is
    specified, evaluates it and sets it to the specified
    ``name``. Otherwise, processes ``BODY`` and uses that instead.

.. _qweb-directive-if:

.. function:: t-if=condition

    :param Expression condition:

    Evaluates ``condition``, suppresses the output of the holder
    element and its content of the result is falsy.

.. _qweb-directive-foreach:

.. function:: t-foreach=iterable [t-as=name]

    :param Expression iterable:
    :param Name name:

    Evaluates ``iterable``, iterates on it and evaluates the holder
    element and its body once per iteration round.

    If ``name`` is not specified, computes a ``name`` based on
    ``iterable`` (by replacing non-``Name`` characters by ``_``).

    If ``iterable`` yields a ``Number``, treats it as a range from 0
    to that number (excluded).

    While iterating, :ref:`t-foreach <qweb-directive-foreach>` adds a
    number of variables in the context:

    ``#{name}``
        If iterating on an array (or a range), the current value in
        the iteration. If iterating on an *object*, the current key.
    ``#{name}_all``
        The collection being iterated (the array generated for a
        ``Number``)
    ``#{name}_value``
        The current iteration value (current item for an array, value
        for the current item for an object)
    ``#{name}_index``
        The 0-based index of the current iteration round.
    ``#{name}_first``
        Whether the current iteration round is the first one.
    ``#{name}_parity``
        ``"odd"`` if the current iteration round is odd, ``"even"``
        otherwise. ``0`` is considered even.

.. _qweb-directive-call:

.. function:: t-call=template [BODY]

    :param String template:
    :param BODY:

    Calls the specified ``template`` and returns its result. If
    ``BODY`` is specified, it is evaluated *before* calling
    ``template`` and can be used to specify e.g. parameters. This
    usage is similar to `call-template with with-param in XSLT
    <http://zvon.org/xxl/XSLTreference/OutputOverview/xslt_with-param_frame.html>`_.

.. _qweb-directives-inheritance:

Template Inheritance and Extension
++++++++++++++++++++++++++++++++++

.. _qweb-directive-extend:

.. function:: t-extend=template BODY

    :param String template: name of the template to extend

    Works similarly to OpenERP models: if used on its own, will alter
    the specified template in-place; if used in conjunction with
    :ref:`t-name <qweb-directive-name>` will create a new template
    using the old one as a base.

    ``BODY`` should be a sequence of :ref:`t-jquery
    <qweb-directive-jquery>` alteration directives.

    .. note::

        The inheritance in the second form is *static*: the parent
        template is copied and transformed when :ref:`t-extend
        <qweb-directive-extend>` is called. If it is altered later (by
        a :ref:`t-extend <qweb-directive-extend>` without a
        :ref:`t-name <qweb-directive-name>`), these changes will *not*
        appear in the "child" templates.

.. _qweb-directive-jquery:

.. function:: t-jquery=selector [t-operation=operation] BODY

    :param String selector: a CSS selector into the parent template
    :param operation: one of ``append``, ``prepend``, ``before``,
                      ``after``, ``inner`` or ``replace``.
    :param BODY: ``operation`` argument, or alterations to perform

    * If ``operation`` is specified, applies the selector to the
      parent template to find a *context node*, then applies
      ``operation`` (as a jQuery operation) to the *context node*,
      passing ``BODY`` as parameter.

      .. note::

          ``replace`` maps to jQuery's `replaceWith(newContent)
          <http://api.jquery.com/replaceWith/>`_, ``inner`` maps to
          `html(htmlString) <http://api.jquery.com/html/>`_.

    * If ``operation`` is not provided, ``BODY`` is evaluated as
      javascript code, with the *context node* as ``this``.

      .. warning::

          While this second form is much more powerful than the first,
          it is also much harder to read and maintain and should be
          avoided. It is usually possible to either avoid it or
          replace it with a sequence of ``t-jquery:t-operation:``.

Escape Hatches / debugging
++++++++++++++++++++++++++

.. _qweb-directive-log:

.. function:: t-log=expression

    :param Expression expression:

    Evaluates the provided expression (in the current template
    context) and logs its result via ``console.log``.

.. _qweb-directive-debug:

.. function:: t-debug

    Injects a debugger breakpoint (via the ``debugger;`` statement) in
    the compiled template output.

.. _qweb-directive-js:

.. function:: t-js=context BODY

    :param Name context:
    :param BODY: javascript code

    Injects the provided ``BODY`` javascript code into the compiled
    template, passing it the current template context using the name
    specified by ``context``.
