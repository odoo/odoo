.. _changelog:

Changelog
=========

`trunk (saas-2)`
----------------

 - added ``_mail_post_access`` attribute that specifies the access right that
   should have the user in order to post a new message on a given model. Values
   are ``read`` (portal documents), ``write`` (default value), ``unlink`` or ``create``.