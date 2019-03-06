List View
=========

Style Hooks
-----------

The list view provides a few style hook classes for re-styling of list views in
various situations:

``.oe_list``

    The root element of the list view, styling rules should be rooted
    on that class.

``table.oe_list_content``

    The root table for the listview, accessory components may be
    generated or added outside this section, this is the list view
    "proper".

``.oe_list_buttons``

    The action buttons array for the list view, with its sub-elements

    ``.oe_list_add``

        The default "Create"/"Add" button of the list view

    ``.oe_alternative``

        The "alternative choice" for the list view, by default text
        along the lines of "or import" with a link.

``.oe_list_field_cell``

    The cell (``td``) for a given field of the list view, cells which
    are *not* fields (e.g. name of a group, or number of items in a
    group) will not have this class. The field cell can be further
    specified:

    ``.oe_number``

        Numeric cell types (integer and float)

    ``.oe_button``

        Action button (``button`` tag in the view) inside the cell

    ``.o_readonly_modifier``

        Readonly field cell

    ``.oe_list_field_$type``

        Additional class for the precise type of the cell, ``$type``
        is the field's @widget if there is one, otherwise it's the
        field's type.

``.oe_list_record_selector``

    Selector cells

Editable list view
++++++++++++++++++

The editable list view module adds a few supplementary style hook
classes, for edition situations:

``.o_list_editable``

    Added to the ``.oe_list`` when the list is editable (however that
    was done). The class may be removed on-the-fly if the list becomes
    non-editable.

``.oe_editing``

    Added to both ``.oe_list`` and ``.oe_list_button`` (as the
    buttons may be outside of the list view) when a row of the list is
    currently being edited.

``tr.oe_edition``

    Class set on the row being edited itself. Note that the edition
    form is *not* contained within the row, this allows for styling or
    modifying the row while it's being edited separately. Mostly for
    fields which can not be edited (e.g. read-only fields).

Columns display customization
-----------------------------

The list view provides a registry to
:js:class:`openerp.web.list.Column` objects allowing for the
customization of a column's display (e.g. so that a binary field is
rendered as a link to the binary file directly in the list view).

The registry is ``instance.web.list.columns``, the keys are of the
form ``tag.type`` where ``tag`` can be ``field`` or ``button``, and
``type`` can be either the field's type or the field's ``@widget`` (in
the view).

Most of the time, you'll want to define a ``tag.widget`` key
(e.g. ``field.progressbar``).

.. js:class:: openerp.web.list.Column(id, tag, attrs)

    .. js:function:: openerp.web.list.Column.format(record_data, options)

        Top-level formatting method, returns an empty string if the
        column is invisible (unless the ``process_modifiers=false``
        option is provided); returns ``options.value_if_empty`` or an
        empty string if there is no value in the record for the
        column.

        Otherwise calls :js:func:`~openerp.web.list.Column._format`
        and returns its result.

        This method only needs to be overridden if the column has no
        concept of values (and needs to bypass that check), for a
        button for instance.

        Otherwise, custom columns should generally override
        :js:func:`~openerp.web.list.Column._format` instead.

        :returns: String

    .. js:function:: openerp.web.list.Column._format(record_data, options)

        Never called directly, called if the column is visible and has
        a value.

        The default implementation calls
        :js:func:`~openerp.web.format_value` and htmlescapes the
        result (via ``_.escape``).

        Note that the implementation of
        :js:func:`~openerp.web.list.Column._format` *must* escape the
        data provided to it, its output will *not* be escaped by
        :js:func:`~openerp.web.list.Column.format`.

        :returns: String

Editable list view
------------------

List view edition is an extension to the base listview providing the
capability of inline record edition by delegating to an embedded form
view.

Editability status
++++++++++++++++++

The editability status of a list view can be queried through the
:js:func:`~openerp.web.ListView.editable` method, will return a falsy
value if the listview is not currently editable.

The editability status is based on three flags:

``tree/@editable``

    If present, can be either ``"top"`` or ``"bottom"``. Either will
    make the list view editable, with new records being respectively
    created at the top or at the bottom of the view.

``context.set_editable``

    Boolean flag extracted from a search context (during the
    :js:func:`~openerp.web.ListView.do_search`` handler), ``true``
    will make the view editable (from the top), ``false`` or the
    absence of the flag is a noop.

``defaults.editable``

    Like ``tree/@editable``, one of absent (``null``)), ``"top"`` or
    ``"bottom"``, fallback for the list view if none of the previous
    two flags are set.

These three flags can only *make* a listview editable, they can *not*
override a previously set flag. To do that, a listview user should
instead cancel :ref:`the edit:before event <listview-edit-before>`.

The editable list view module adds a number of methods to the list
view, on top of implementing the :js:class:`EditorDelegate` protocol:

Interaction Methods
+++++++++++++++++++

.. js:function:: openerp.web.ListView.ensure_saved

    Attempts to resolve the pending edition, if any, by saving the
    edited row's current state.

    :returns: delegate resolving to all editions having been saved, or
              rejected if a pending edition could not be saved
              (e.g. validation failure)

.. js:function:: openerp.web.ListView.start_edition([record][, options])

    Starts editing the provided record inline, through an overlay form
    view of editable fields in the record.

    If no record is provided, creates a new one according to the
    editability configuration of the list view.

    This method resolves any pending edition when invoked, before
    starting a new edition.

    :param record: record to edit, or null to create a new record
    :type record: :js:class:`~openerp.web.list.Record`
    :param EditOptions options:
    :returns: delegate to the form used for the edition

.. js:function:: openerp.web.ListView.save_edition

    Resolves the pending edition.

    :returns: delegate to the save being completed, resolves to an
              object with two attributes ``created`` (flag indicating
              whether the saved record was just created or was
              updated) and ``record`` the reloaded record having been
              edited.

.. js:function:: openerp.web.ListView.cancel_edition([force=false])

    Cancels pending edition, cleans up the list view in case of
    creation (removes the empty record being created).

    :param Boolean force: doesn't check if the user has added any
                          data, discards the edition unconditionally

Utility Methods
+++++++++++++++

.. js:function:: openerp.web.ListView.get_cells_for(row)

    Extracts the cells from a listview row, and puts them in a
    {fieldname: cell} mapping for analysis and manipulation.

    :param jQuery row:
    :rtype: Object

.. js:function:: openerp.web.ListView.with_event(event_name, event, action[, args][, trigger_params])

    Executes ``action`` in the context of the view's editor,
    bracketing it with cancellable event signals.

    :param String event_name: base name for the bracketing event, will
                              be postfixed by ``:before`` and
                              ``:after`` before being called
                              (respectively before and after
                              ``action`` is executed)
    :param Object event: object passed to the ``:before`` event
                         handlers.
    :param Function action: function called with the view's editor as
                            its ``this``. May return a deferred.
    :param Array args: arguments passed to ``action``
    :param Array trigger_params: arguments passed to the ``:after``
                                 event handler alongside the results
                                 of ``action``

Behavioral Customizations
+++++++++++++++++++++++++

.. js:function:: openerp.web.ListView.handle_onwrite(record)

    Implements the handling of the ``onwrite`` listview attribute:
    calls the RPC methods specified by ``@onwrite``, and if that
    method returns an array of ids loads or reloads the records
    corresponding to those ids.

    :param record: record being written having triggered the
                   ``onwrite`` callback
    :type record: openerp.web.list.Record
    :returns: deferred to all reloadings being done

Events
++++++

For simpler interactions by/with external users of the listview, the
view provides a number of dedicated events to its lifecycle.

.. note:: if an event is defined as *cancellable*, it means its first
          parameter is an object on which the ``cancel`` attribute can
          be set. If the ``cancel`` attribute is set, the view will
          abort its current behavior as soon as possible, and rollback
          any state modification.

          Generally speaking, an event should only be cancelled (by
          setting the ``cancel`` flag to ``true``), uncancelling an
          event is undefined as event handlers are executed on a
          first-come-first-serve basis and later handlers may
          re-cancel an uncancelled event.

.. _listview-edit-before:

``edit:before`` *cancellable*

    Invoked before the list view starts editing a record.

    Provided with an event object with a single property ``record``,
    holding the attributes of the record being edited (``record`` is
    empty *but not null* for a new record)

``edit:after``

    Invoked after the list view has gone into an edition state,
    provided with the attributes of the record being edited (see
    ``edit:before``) as first parameter and the form used for the
    edition as second parameter.

``save:before`` *cancellable*

    Invoked right before saving a pending edition, provided with an
    event object holding the listview's editor (``editor``) and the
    edition form (``form``)

``save:after``

    Invoked after a save has been completed

``cancel:before`` *cancellable*

    Invoked before cancelling a pending edition, provided with the
    same information as ``save:before``.

``cancel:after``

    Invoked after a pending edition has been cancelled.

DOM events
++++++++++

The list view has grown hooks for the ``keyup`` event on its edition
form (during edition): any such event bubbling out of the edition form
will be forwarded to a method ``keyup_EVENTNAME``, where ``EVENTNAME``
is the name of the key in ``$.ui.keyCode``.

The method will also get the event object (originally passed to the
``keyup`` handler) as its sole parameter.

The base editable list view has handlers for the ``ENTER`` and
``ESCAPE`` keys.

Editor
------

The list-edition modules does not generally interact with the embedded
formview, delegating instead to its
:js:class:`~openerp.web.list.Editor`.

.. js:class:: openerp.web.list.Editor(parent[, options])

    The editor object provides a more convenient interface to form
    views, and simplifies the usage of form views for semi-arbitrary
    edition of stuff.

    However, the editor does *not* task itself with being internally
    consistent at this point: calling
    e.g. :js:func:`~openerp.web.list.Editor.edit` multiple times in a
    row without saving or cancelling each edit is undefined.

    :param parent:
    :type parent: :js:class:`~openerp.web.Widget`
    :param EditorOptions options:

    .. js:function:: openerp.web.list.Editor.is_editing([record_state])

        Indicates whether the editor is currently in the process of
        providing edition for a record.

        Can be filtered by the state of the record being edited
        (whether it's a record being *created* or a record being
        *altered*), in which case it asserts both that an edition is
        underway and that the record being edited respectively does
        not yet exist in the database or already exists there.

        :param record_state: state of the record being edited.
                             Either ``"new"`` or ``"edit"``.
        :type record_state: String
        :rtype: Boolean

    .. js:function:: openerp.web.list.Editor.edit(record, configureField[, options])

        Loads the provided record into the internal form view and
        displays the form view.

        Will also attempt to focus the first visible field of the form
        view.

        :param Object record: record to load into the form view
                              (key:value mapping similar to the result
                              of a ``read``)
        :param configureField: function called with each field of the
                               form view right after the form is
                               displayed, lets whoever called this
                               method do some last-minute
                               configuration of form fields.
        :type configureField: Function<String, openerp.web.form.Field>
        :param EditOptions options:
        :returns: jQuery delegate to the form object

    .. js:function:: openerp.web.list.Editor.save

        Attempts to save the internal form, then hide it

        :returns: delegate to the record under edition (with ``id``
                  added for a creation). The record is not updated
                  from when it was passed in, aside from the ``id``
                  attribute.

    .. js:function:: openerp.web.list.Editor.cancel([force=false])

        Attemps to cancel the edition of the internal form, then hide
        the form

        :param Boolean force: unconditionally cancels the edition of
                              the internal form, even if the user has
                              already entered data in it.
        :returns: delegate to the record under edition

.. js:class:: EditorOptions

    .. js:attribute:: EditorOptions.formView

        Form view (sub)-class to instantiate and delegate edition to.

        By default, :js:class:`~openerp.web.FormView`

    .. js:attribute:: EditorOptions.delegate

        Object used to get various bits of information about how to
        display stuff.

        By default, uses the editor's parent widget. See
        :js:class:`EditorDelegate` for the methods and attributes to
        provide.

.. js:class:: EditorDelegate

    Informal protocol defining the methods and attributes expected of
    the :js:class:`~openerp.web.list.Editor`'s delegate.

    .. js:attribute:: EditorDelegate.dataset

        The dataset passed to the form view to synchronize the form
        view and the outer widget.

    .. js:function:: EditorDelegate.edition_view(editor)

        Called by the :js:class:`~openerp.web.list.Editor` object to
        get a form view (JSON) to pass along to the form view it
        created.

        The result should be a valid form view, see :doc:`Form Notes
        <form_view>` for various peculiarities of the form view
        format.

        :param editor: editor object asking for the view
        :type editor: :js:class:`~openerp.web.list.Editor`
        :returns: form view
        :rtype: Object

    .. js:function:: EditorDelegate.prepends_on_create

        By default, the :js:class:`~openerp.web.list.Editor` will
        append the ids of newly created records to the
        :js:attr:`EditorDelegate.dataset`. If this method returns
        ``true``, it will prepend these ids instead.

        :returns: whether new records should be prepended to the
                  dataset (instead of appended)
        :rtype: Boolean


.. js:class:: EditOptions

    Options object optionally passed into a method starting an edition
    to configure its setup and behavior

    .. js:attribute:: focus_field

        Name of the field to set focus on after setting up the edition
        of the record.

        If this option is not provided, or the requested field can not
        be focused (invisible, readonly or not in the view), the first
        visible non-readonly field is focused.

Changes from 6.1
----------------

* The editable listview behavior has been rewritten pretty much from
  scratch, any code touching on editability will have to be modified

  * The overloading of :js:class:`~openerp.web.ListView.Groups` and
    :js:class:`~openerp.web.ListView.List` for editability has been
    drastically simplified, and most of the behavior has been moved to
    the list view itself. Only
    :js:func:`~openerp.web.ListView.List.row_clicked` is still
    overridden.

  * A new method ``get_row_for(record) -> jQuery(tr) | null`` has been
    added to both ListView.List and ListView.Group, it can be called
    from the list view to get the table row matching a record (if such
    a row exists).

* :js:func:`~openerp.web.ListView.do_button_action`'s core behavior
  has been split away to
  :js:func:`~openerp.web.ListView.handle_button`. This allows bypassing
  overrides of :js:func:`~openerp.web.ListView.do_button_action` in a
  parent class.

  Ideally, :js:func:`~openerp.web.ListView.handle_button` should not be
  overridden.

* Modifiers handling has been improved (all modifiers information
  should now be available through :js:func:`~Column.modifiers_for`,
  not just ``invisible``)

* Changed some handling of the list view's record: a record may now
  have no id, and the listview will handle that correctly (for new
  records being created) as well as correctly handle the ``id`` being
  set.

* Extended the internal collections structure of the list view with
  `#find`_, `#succ`_ and `#pred`_.

.. _#find: http://underscorejs.org/#find

.. _#succ: http://hackage.haskell.org/packages/archive/base/latest/doc/html/Prelude.html#v:succ

.. _#pred: http://hackage.haskell.org/packages/archive/base/latest/doc/html/Prelude.html#v:pred
