:banner: banners/deploying_odoo.jpg

==============
Deploying Odoo
==============

This document describes basic steps to set up Odoo in production. It follows
:ref:`installation <setup/install>`, but should not be used for development
systems.

dbfilter
========

Odoo is a multi-tenant system: a single Odoo system may run and serve a number
of database instances. It is also highly customizable, with customizations
(starting from the modules being loaded) depending on the "current database".

This is not an issue when working with the backend (web client) as a logged-in
company user: the database can be selected when logging in, and customizations
loaded afterwards.

However it is an issue for non-logged users (portal, website) which aren't
bound to a database: Odoo need to know which database should be used for the
operations or to get the data. If multi-tenancy is not used that is not an
issue, there's only one database to use, but if there are multiple databases
accessible Odoo needs a rule to know which one it should use.

That is one of the purposes of :option:`--db-filter <odoo.py --db-filter>`:
it specifies the default database for the Odoo system. The value is a
`regular expression`_, possibly including the dynamically injected hostname
or subdomain through which the Odoo system is accessed.

If an Odoo hosts multiple databases in production, especially if ``website``
is used, it **must** use a dbfilter or a number of features will not work
correctly or not use at all.

PostgreSQL
==========

By default, PostgreSQL only allows connection over UNIX sockets and loopback
connections (from "localhost", the same machine the PostgreSQL server is
installed on).

UNIX socket is fine if you want Odoo and PostgreSQL to execute on the same
machine, and is the default when no host is provided, but if you want Odoo and
PostgreSQL to execute on different machines [#different-machines]_ it will
need to `listen to network interfaces`_ [#remote-socket]_, either:

* only accept loopback connections and `use an SSH tunnel`_ between the
  machine on which Odoo runs and the one on which PostgreSQL runs, then
  configure Odoo to connect to its end of the tunnel
* accept connections to the machine on which Odoo is installed, possibly
  over ssl (see `PostgreSQL connection settings`_ for details), then configure
  Odoo to connect over the network

.. _setup/deploy/odoo:

Configuring Odoo
----------------

Out of the box, Odoo connects to a local postgres over UNIX socket via port
5432. This can be overridden using :ref:`the database options
<reference/cmdline/server/database>` when your Postgres deployment is not
local and/or does not use the installation defaults.

The :ref:`packaged installers <setup/install/packaged>` will automatically
create a new user (``odoo``) and set it as the database user.

* The database management screens are protected by the ``admin_passwd``
  setting. This setting can only be set using configuration files, and is
  simply checked before performing database alterations. It should be set to
  a randomly generated value to ensure third parties can not use this
  interface.
* all database operations use the :ref:`database options
  <reference/cmdline/server/database>`, including the database management
  screen. For the database management screen to work requires that the user
  have ``createdb`` right.
* users can always drop databases they own. For the database management screen
  to be completely non-functional, the user needs to be created with
  ``no-createdb`` and the database must be owned by a different user.

  .. warning:: the user *must not* be a superuser

HTTPS
=====

Whether it's accessed via website/web client or the webservice, Odoo transmits
authentication information in cleatext. This means a secure deployment of
Odoo must use HTTPS\ [#switching]_. SSL termination can be implemented via
just about any SSL termination proxy, but requires the following setup:

* enable Odoo's :option:`proxy mode <odoo.py --proxy-mode>`. This should only
  be enabled when Odoo is behind a reverse proxy
* set up the SSL termination proxy (`Nginx termination example`_)
* set up the proxying itself (`Nginx proxying example`_)
* your SSL termination proxy should also automatically redirect non-secure
  connections to the secure port

Builtin server
==============

Odoo includes built-in HTTP servers, using either multithreading or
multiprocessing.

For production use, it is recommended to use the multiprocessing server as it
increases stability, makes somewhat better use of computing resources and can
be better monitored and resource-restricted.

* Multiprocessing is enabled by configuring :option:`a non-zero number of
  worker processes <odoo.py --workers>`, the number of workers should be based
  on the number of cores in the machine (possibly with some room for cron
  workers depending on how much cron work is predicted)
* Worker limits can be configured based on the hardware configuration to avoid
  resources exhaustion

.. warning:: multiprocessing mode currently isn't available on Windows

LiveChat
--------

In multiprocessing, a dedicated LiveChat worker is automatically started and
listening on :option:`the longpolling port <odoo.py --longpolling-port>` but
the client will not connect to it.

Instead you must have a proxy redirecting requests whose URL starts with
``/longpolling/`` to the longpolling port. Other request should be proxied to
the :option:`normal HTTP port <odoo.py --xmlrpc-port>`

Odoo as a WSGI Application
==========================

It is also possible to mount Odoo as a standard WSGI_ application. Odoo
provides the base for a WSGI launcher script as ``openerp-wsgi.py``. That
script should be customized (possibly after copying it) to correctly set the
configuration directly in :mod:`openerp.tools.config` rather than through the
command-line or a configuration file.

However the WSGI server will only expose the main HTTP endpoint for the web
client, website and webservice API. Because Odoo does not control the creation
of workers anymore it can not setup cron or livechat workers

Cron Workers
------------

To run cron jobs for an Odoo deployment as a WSGI application requires

* a classical Odoo (run via ``odoo.py``)
* connected to the database in which cron jobs have to be run (via
  :option:`odoo.py -d`)
* which should not be exposed to the network. To ensure cron runners are not
  network-accessible, it is possible to disable the built-in HTTP server
  entirely with :option:`odoo.py --no-xmlrpc` or setting ``xmlrpc = False``
  in the configuration file

LiveChat
--------

The second problematic subsystem for WSGI deployments is the LiveChat: where
most HTTP connections are relatively short and quickly free up their worker
process for the next request, LiveChat require a long-lived connection for
each client in order to implement near-real-time notifications.

This is in conflict with the process-based worker model, as it will tie
up worker processes and prevent new users from accessing the system. However,
those long-lived connections do very little and mostly stay parked waiting for
notifications.

The solutions to support livechat/motifications in a WSGI application are:

* deploy a threaded version of Odoo (instread of a process-based preforking
  one) and redirect only requests to URLs starting with ``/longpolling/`` to
  that Odoo, this is the simplest and the longpolling URL can double up as
  the cron instance.
* deploy an evented Odoo via ``openerp-gevent`` and proxy requests starting
  with ``/longpolling/`` to
  :option:`the longpolling port <odoo.py --longpolling-port>`.

Serving Static Files
====================

For development convenience, Odoo directly serves all static files in its
modules. This may not be ideal when it comes to performances, and static
files should generally be served by a static HTTP server.

Odoo static files live in each module's ``static/`` folder, so static files
can be served by intercepting all requests to :samp:`/{MODULE}/static/{FILE}`,
and looking up the right module (and file) in the various addons paths.

.. todo:: test whether it would be interesting to serve filestored attachments
          via this, and how (e.g. possibility of mapping ir.attachment id to
          filestore hash in the database?)

Security
========

"Super-admin" password
----------------------

:ref:`setup/deploy/odoo` mentioned ``admin_passwd`` in passing.

This setting is used on all database management screens (to create, delete,
dump or restore databases).

If the management screens must not be accessible, or must only be accessible
from a selected set of machines, use the proxy server's features to block
access to all routes starting with ``/web/database`` except (maybe)
``/web/database/selector`` which displays the database-selection screen.

If the database-management screen should be left accessible, the
``admin_passwd`` setting must be changed from its ``admin`` default: this
password is checked before allowing database-alteration operations.

It should be stored securely, and should be generated randomly e.g.

.. code-block:: console

    $ python -c 'import base64, os; print(base64.b64encode(os.urandom(24)))'

which will generate a 32 characters pseudorandom printable string.

.. [#different-machines]
    to have multiple Odoo installations use the same PostgreSQL database,
    or to provide more computing resources to both software.
.. [#remote-socket]
    technically a tool like socat_ can be used to proxy UNIX sockets across
    networks, but that is mostly for software which can only be used over
    UNIX sockets
.. [#switching]
    or be accessible only over an internal packet-switched network, but that
    requires secured switches, protections against `ARP spoofing`_ and
    precludes usage of WiFi. Even over secure packet-switched networks,
    deployment over HTTPS is recommended, and possible costs are lowered as
    "self-signed" certificates are easier to deploy on a controlled
    environment than over the internet.

.. _regular expression: https://docs.python.org/2/library/re.html
.. _ARP spoofing: http://en.wikipedia.org/wiki/ARP_spoofing
.. _Nginx termination example:
    http://nginx.com/resources/admin-guide/nginx-ssl-termination/
.. _Nginx proxying example:
    http://nginx.com/resources/admin-guide/reverse-proxy/
.. _socat: http://www.dest-unreach.org/socat/
.. _PostgreSQL connection settings:
.. _listen to network interfaces:
    http://www.postgresql.org/docs/9.3/static/runtime-config-connection.html
.. _use an SSH tunnel:
    http://www.postgresql.org/docs/9.3/static/ssh-tunnels.html
.. _WSGI: http://wsgi.readthedocs.org/
