.. _changelog:

Changelog
=========

`trunk`
-------

- Added support of custom group_by format and display format when using group_by
  on a datetime field, using datetime_format context key
- Improved ``html_email_clean`` in tools: better quote and signature finding,
  added shortening.
- Cleaned and slightly refactored ``ir.actions.server``. The ``loop``, ``sms``
  and ``dummy`` server actions have been removed; ``object_create`` and
  ``object_copy`` have been merged into ``object_create``; ``other`` is now ``multi``
  and raises in case of loops. See :ref:`ir-actions-server` for more details.
- Removed ``sms_send`` method.
- Added checking of recursions in many2many loops using ``_check_m2m_recursion``.
- Added MONTHS attribute on fields.date and fields.datetime, holding the list
  (month_number, month_name)
- Almost removed ``LocalService()``. For reports,
  ``openerp.osv.orm.Model.print_report()`` can be used. For workflows, see
  :ref:`orm-workflows`.
- Removed support for the ``NET-RPC`` protocol.
- Added the :ref:`Long polling <longpolling-worker>` worker type.
- Added :ref:`orm-workflows` to the ORM.
- Added :ref:`routing-decorators` to the RPC and WSGI stack.
- Removed support for ``__terp__.py`` descriptor files.
- Removed support for ``<terp>`` root element in XML files.
- Removed support for the non-openerp namespace (e.g. importing ``tools``
  instead of ``openerp.tools`` in an addons).
- Add a new type of exception that allows redirections:
  ``openerp.exceptions.RedirectWarning``.
- Give a pair of new methods to ``res.config.settings`` and a helper to make
  them easier to use: ``get_config_warning()``.
- Path to webkit report files (field ``report_file``) must be written the
  Unix way (with ``/`` and not ``\``)


`7.0`
-----

- Modules may now include an ``i18n_extra`` directory that will be treated like the
  default ``i18n`` directory. This is typically useful for manual translation files
  that are not managed by Launchpad's translation system. An example is l10n modules
  that depend on ``l10n_multilang``.

