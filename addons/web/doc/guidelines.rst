Guidelines and Recommendations
==============================

Web Module Recommendations
--------------------------

Identifiers (``id`` attribute) should be avoided
''''''''''''''''''''''''''''''''''''''''''''''''

In generic applications and modules, ``@id`` limits the reusabily of
components and tends to make code more brittle.

Just about all the time, they can be replaced with nothing, with
classes or with keeping a reference to a DOM node or a jQuery element
around.

.. note::

    If it is *absolutely necessary* to have an ``@id`` (because a
    third-party library requires one and can't take a DOM element), it
    should be generated with `_.uniqueId
    <http://underscorejs.org/#uniqueId>`_ or some other similar
    method.

Avoid predictable/common CSS class names
''''''''''''''''''''''''''''''''''''''''

Class names such as "content" or "navigation" might match the desired
meaning/semantics, but it is likely an other developer will have the
same need, creating a naming conflict and unintended behavior. Generic
class names should be prefixed with e.g. the name of the component
they belong to (creating "informal" namespaces, much as in C or
Objective-C)

Global selectors should be avoided
''''''''''''''''''''''''''''''''''

Because a component may be used several times in a single page (an
example in OpenERP is dashboards), queries should be restricted to a
given component's scope. Unfiltered selections such as ``$(selector)``
or ``document.querySelectorAll(selector)`` will generally lead to
unintended or incorrect behavior.

OpenERP Web's :js:class:`~openerp.web.Widget` has an attribute
providing its DOM root :js:attr:`Widget.$el <openerp.web.Widget.$el>`,
and a shortcut to select nodes directly :js:attr:`Widget.$
<openerp.web.Widget.$>`.

More generally, never assume your components own or controls anything
beyond its own personal DOM.

Understand deferreds
''''''''''''''''''''

Deferreds, promises, futures, …

Known under many names, these objects are essential to and (in OpenERP
Web) widely used for making :doc:`asynchronous javascript operations
<async>` palatable and understandable.

OpenERP Web guidelines
----------------------

* HTML templating/rendering should use :doc:`qweb` unless absolutely
  trivial.

* All interactive components (components displaying information to the
  screen or intercepting DOM events) must inherit from
  :class:`~openerp.web.Widget` and correctly implement and use its API
  and lifecycle.

* All css classes must be prefixed with *oe_* .

* Asynchronous functions (functions which call :ref:`session.rpc
  <rpc_rpc>` directly or indirectly at the very least) *must* return
  deferreds, so that callers of overriders can correctly synchronize
  with them.
