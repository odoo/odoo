Sessions in Redis
=================

This addon allows to store the web sessions in Redis.

Configuration
-------------

The storage of sessions in Redis is activated using environment variables.

* ``ODOO_SESSION_REDIS`` has to be ``1`` or ``true``
* ``ODOO_SESSION_REDIS_HOST`` is the redis hostname (default is ``localhost``)
* ``ODOO_SESSION_REDIS_PORT`` is the redis port (default is ``6379``)
* ``ODOO_SESSION_REDIS_PASSWORD`` is the password for the AUTH command
  (optional)
* ``ODOO_SESSION_REDIS_SSL`` is the SSL connection (default is ``true``)
  (optional)
* ``ODOO_SESSION_REDIS_SSL_CERT_REQS`` is the SSL certificate requirements (default is
  ``required``), needed to be disabled when using self-signed certificates
  (optional)
* ``ODOO_SESSION_REDIS_CLUSTER`` the redis in cluster mode (default is ``false``)
  (optional)

* ``ODOO_SESSION_REDIS_URL`` is an alternative way to define the Redis server
  address. It's the preferred way when you're using the ``rediss://`` protocol.
* ``ODOO_SESSION_REDIS_PREFIX`` is the prefix for the session keys (optional)
* ``ODOO_SESSION_REDIS_EXPIRATION`` is the time in seconds before expiration of
  the sessions (default is 7 days)
* ``ODOO_SESSION_REDIS_EXPIRATION_ANONYMOUS`` is the time in seconds before expiration of
  the anonymous sessions (default is 3 hours)


The keys are set to ``session:<session id>``.
When a prefix is defined, the keys are ``session:<prefix>:<session id>``

This addon must be added in the server wide addons with (``--load`` option):

``--load=web,session_redis``

Limitations
-----------

* The server has to be restarted in order for the sessions to be stored in
  Redis.
* All the users will have to login again as their previous session will be
  dropped.
* The addon monkey-patch ``odoo.http.Root.session_store`` with a custom
  method when the Redis mode is active, so incompatibilities with other addons
  is possible if they do the same.
