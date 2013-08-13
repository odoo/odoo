.. _changelog:

Changelog
=========

`trunk (saas-2)`
----------------

 - added support of ``active_domain`` form context, coming from the list view.
   When checking the header hook, the mass mailing will be done on all records
   matching the ``active_domain``.
 - added ``mail_server_id`` to mail_message, removing it from mail_mail. This allows
   to set the preferred mail server to use for notifications emails, when using
   templates.
 - added ``_mail_post_access`` attribute that specifies the access right that
   should have the user in order to post a new message on a given model. Values
   are ``read`` (portal documents), ``write`` (default value), ``unlink`` or ``create``.
