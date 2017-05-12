:banner: banners/translate.jpg

.. _reference/translations:


===================
Translating Modules
===================

Exporting translatable term
===========================

A number of terms in your modules are "implicitly translatable" as a result,
even if you haven't done any specific work towards translation you can export
your module's translatable terms and may find content to work with.

.. todo:: needs technical features

Translations export is performed via the administration interface by logging into
the backend interface and opening :menuselection:`Settings --> Translations
--> Import / Export --> Export Translations`

* leave the language to the default (new language/empty template)
* select the `PO File`_ format
* select your module
* click :guilabel:`Export` and download the file

.. image:: translations/po-export.*
    :align: center
    :width: 75%

This gives you a file called :file:`{yourmodule}.pot` which should be moved to
the :file:`{yourmodule}/i18n/` directory. The file is a *PO Template* which
simply lists translatable strings and from which actual translations (PO files)
can be created. PO files can be created using msginit_, with a dedicated
translation tool like POEdit_ or by simply copying the template to a new file
called :file:`{language}.po`. Translation files should be put in
:file:`{yourmodule}/i18n/`, next to :file:`{yourmodule}.pot`, and will be
automatically loaded by Odoo when the corresponding language is installed (via
:menuselection:`Settings --> Translations --> Load a Translation`)

.. note:: translations for all loaded languages are also installed or updated
          when installing or updating a module

Implicit exports
================

Odoo automatically exports translatable strings from "data"-type content:

* in non-QWeb views, all text nodes are exported as well as the content of
  the ``string``, ``help``, ``sum``, ``confirm`` and ``placeholder``
  attributes
* QWeb templates (both server-side and client-side), all text nodes are
  exported except inside ``t-translation="off"`` blocks, the content of the
  ``title``, ``alt``, ``label`` and ``placeholder`` attributes are also
  exported
* for :class:`~odoo.fields.Field`, unless their model is marked with
  ``_translate = False``:

  * their ``string`` and ``help`` attributes are exported
  * if ``selection`` is present and a list (or tuple), it's exported
  * if their ``translate`` attribute is set to ``True``, all of their existing
    values (across all records) are exported
* help/error messages of :attr:`~odoo.models.Model._constraints` and
  :attr:`~odoo.models.Model._sql_constraints` are exported

Explicit exports
================

When it comes to more "imperative" situations in Python code or Javascript
code, Odoo cannot automatically export translatable terms so they
must be marked explicitly for export. This is done by wrapping a literal
string in a function call.

In Python, the wrapping function is :func:`odoo._`::

    title = _("Bank Accounts")

In JavaScript, the wrapping function is generally :js:func:`odoo.web._t`:

.. code-block:: javascript

    title = _t("Bank Accounts")

.. warning::

    Only literal strings can be marked for exports, not expressions or
    variables. For situations where strings are formatted, this means the
    format string must be marked, not the formatted string::

        # bad, the extract may work but it will not translate the text correctly
        _("Scheduled meeting with %s" % invitee.name)

        # good
        _("Scheduled meeting with %s") % invitee.name

.. _PO File: http://en.wikipedia.org/wiki/Gettext#Translating
.. _msginit: http://www.gnu.org/software/gettext/manual/gettext.html#Creating
.. _POEdit: http://poedit.net/
