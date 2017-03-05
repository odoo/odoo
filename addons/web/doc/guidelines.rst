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

New Javascript guidelines
-------------------------

From v11, we introduce a new coding standard for Odoo Javascript code.  Here it
is:

* add "use strict"; on top of every odoo JS module

* name all entities exported by a JS module. So, instead of 

  .. code-block:: javascript

      return Widget.extend({
        ...
      });

you should use:

  .. code-block:: javascript

      var MyWidget = Widget.extend({
        ...
      });

      return MyWidget

* there should be one space between function and the left parenthesis:

  .. code-block:: javascript

    function (a, b) {}

* JS files should have a (soft) limit of 80 chars width, and a hard limit of 100

* document every functions and every files, with the style JSDoc.

* for function overriding other functions, consider adding the tag @override in
  the JS Doc.  Also, you can mention which method is overridden:

  .. code-block:: javascript

    /**
     * When a save operation has been confirmed from the model, this method is
     * called.
     *
     * @override method from field manager mixin
     * @param {string} id
     */
    _confirmSave: function (id) {

* there should be an empty line between the main function comments and the tags,
  or parameter descriptions

* avoid introspection: don't build dynamically a method name and call it.  It is
  more fragile and more difficult to refactor

* methods should be private if possible

* never read an attribute of an attribute on somethig that you have a reference.
  So, this is not good:

  .. code-block:: javascript

    this.myObject.propA.propB

* never use a reference to the parent widget

* avoid using the 'include' functionality: extending a class is fine and does
  not cause issue, including a class is much more fragile, and may not work.

* For the widgets, here is how the various attributes/functions should be
  ordered:

  1. all static attributes, such as template, events, custom_events, ...

  2. all methods from the lifecycle of a widget, in this order: init, willStart,
     start, destroy

  3. If there are public methods, a section titled "Public", with an empty line
    before and after

  4. all public methods, camelcased, in alphabetic order

  5. If there are private methods, a section titled "Private", with an empty line
    before and after

  6. all private methods, camelcased and prefixed with _, in alphabetic order

  7. If there are event handlers, a section titled "Handlers", with an empty line
    before and after

  8. all handlers, camelcased and prefixed with _on, in alphabetic order

  9. If there are static methods, they should be in a section titled "Static".
     All static methods are considered public, camelcased with no _.

* write unit tests

* for the event handlers defined by the key 'event' or 'custom_events', don't
  inline the function.  Always add a string name, and add the definition in the
  handler section

* one space after if and for

* never call private methods on another object

* object definition on more than one line: each element should have a trailing
  comma.

* strings: double quotes for all textual strings (such as "Hello"), and single
  quotes for all other strings, such as a css selector '.o_form_view'

* always use this._super.apply(this, arguments);

* keys in an object: ordered by alphabetic order