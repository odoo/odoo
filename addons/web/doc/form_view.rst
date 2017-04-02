Notes on the usage of the Form View as a sub-widget
===================================================

Undocumented stuff
------------------

* ``initial_mode`` *option* defines the starting mode of the form
  view, one of ``view`` and ``edit`` (?). Default value is ``view``
  (non-editable form).

* ``embedded_view`` *attribute* has to be set separately when
  providing a view directly, no option available for that usage.

  * View arch **must** contain node with
    ``@class="oe_form_container"``, otherwise everything will break
    without any info

  * Root element of view arch not being ``form`` may or may not work
    correctly, no idea.

  * Freeform views => ``@version="7.0"``

* Form is not entirely loaded (some widgets may not appear) unless
  ``on_record_loaded`` is called (or ``do_show``, which itself calls
  ``on_record_loaded``).

* "Empty" form => ``on_button_new`` (...), or manually call
  ``default_get`` + ``on_record_loaded``

* Form fields default to width: 100%, padding, !important margin, can
  be reached via ``.oe_form_field``

* Form *will* render buttons and a pager, offers options to locate
  both outside of form itself (``$buttons`` and ``$pager``), providing
  empty jquery objects (``$()``) seems to stop displaying both but not
  sure if there are deleterious side-effects.

  Other options:

  * Pass in ``$(document.createDocumentFragment)`` to ensure it's a
    DOM-compatible tree completely outside of the actual DOM.

  * ???

* readonly fields probably don't have a background, beware if need of
  overlay

  * What is the difference between ``readonly`` and
    ``effective_readonly``?

* No facilities for DOM events handling/delegations e.g. handling
  keyup/keydown/keypress from a form fields into the form's user.

  * Also no way to reverse from a DOM node (e.g. DOMEvent#target) back to a
    form view field easily
