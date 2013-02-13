.. _changelog:

Changelog
=========

`trunk`
-------

- Removed support for `__terp__.py` descriptor files.
- Removed support for `<terp>` root element in XML files.
- Removed support for the non-openerp namespace (e.g. importing `tools` instead
  of `openerp.tools` in an addons).
- Add a new type of exception that allows redirections:
  openerp.exceptions.RedirectWarning.
- Give a pair of new methods to res.config.settings and a helper to make them
  easier to use: get_config_warning()
