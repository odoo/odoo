- **No database separation** -- This module functions by intercepting
  all Odoo logging records in a running Odoo process. This means that
  once installed in one database, it will intercept and report errors
  for all Odoo databases, which are used on that Odoo server.
- **Frontend integration** -- In the future, it would be nice to add
  Odoo client-side error reporting to this module as well, by
  integrating [raven-js](https://github.com/getsentry/raven-js).
  Additionally, [Sentry user feedback
  form](https://docs.sentry.io/learn/user-feedback/) could be integrated
  into the Odoo client error dialog window to allow users shortly
  describe what they were doing when things went wrong.
