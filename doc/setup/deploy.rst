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

Configuration sample
--------------------

* filtering only db with a name beginning with 'mycompany'

in ``/etc/odoo.conf`` set:

.. code-block:: apacheconf

  [options]
  dbfilter = ^mycompany.*$
  
* filtering only db with a name equal to hostname without domain

in ``/etc/odoo.conf`` set:

.. code-block:: apacheconf

  [options]
  dbfilter = %d
  
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

Configuration sample
--------------------

* allow tcp connection on localhost
* allow tcp connection from 192.168.1.x network

in ``/etc/postgresql/9.5/main/pg_hba.conf`` set:

.. code-block:: apacheconf

  # IPv4 local connections:
  host    all             all             127.0.0.1/32            md5
  host    all             all             192.168.1.0/24          md5

in ``/etc/postgresql/9.5/main/postgresql.conf`` set:
  
.. code-block:: apacheconf
  
  listen_addresses = 'localhost,192.168.1.2'
  port = 5432
  max_connections = 80

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
  screen. For the database management screen to work requires that the PostgreSQL user
  have ``createdb`` right.
* users can always drop databases they own. For the database management screen
  to be completely non-functional, the PostgreSQL user needs to be created with
  ``no-createdb`` and the database must be owned by a different PostgreSQL user.

  .. warning:: the PostgreSQL user *must not* be a superuser

Configuration sample
~~~~~~~~~~~~~~~~~~~~

* connect to a PostgreSQL server on 192.168.1.2
* port 5432
* using an 'odoo' user account,
* with 'pwd' as a password
* filtering only db with a name beginning with 'mycompany'

in ``/etc/odoo.conf`` set:

.. code-block:: apacheconf

  [options]
  admin_passwd = mysupersecretpassword
  db_host = 192.168.1.2
  db_port = 5432
  db_user = odoo
  db_password = pwd
  dbfilter = ^mycompany.*$

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


Worker number calculation
-------------------------

* Rule of thumb : (#CPU * 2) + 1
* Cron workers need CPU
* 1 worker ~= 6 concurrent users

memory size calculation
-----------------------

* We consider 20% of the requests are heavy requests, while 80% are simpler ones
* A heavy worker, when all computed field are well designed, SQL requests are well designed, ... is estimated to consume around 1Go of RAM
* A lighter worker, in the same scenario, is estimated to consume around 150MB of RAM

Needed RAM = #worker * ( (light_worker_ratio * light_worker_ram_estimation) + (heavy_worker_ratio * heavy_worker_ram_estimation) )

LiveChat
--------

In multiprocessing, a dedicated LiveChat worker is automatically started and
listening on :option:`the longpolling port <odoo.py --longpolling-port>` but
the client will not connect to it.

Instead you must have a proxy redirecting requests whose URL starts with
``/longpolling/`` to the longpolling port. Other request should be proxied to
the :option:`normal HTTP port <odoo.py --xmlrpc-port>`

.. warning:: The livechat worker requires the ``psycogreen`` Python module,
             which is not always included with all installation packages.
             It can be manually installed with ``pip install psycogreen``.

Configuration sample
--------------------

* Server with 4 CPU, 8 Thread
* 60 concurrent users

* 60 users / 6 = 10 <- theorical number of worker needed
* (4 * 2) + 1 = 9 <- theorical maximal number of worker
* We'll use 8 workers + 1 for cron. We'll also use a monitoring system to measure cpu load, and check if it's between 7 and 7.5 .
* RAM = 9 * ((0.8*150) + (0.2*1024)) ~= 3Go RAM for Odoo

in ``/etc/odoo.conf``:

.. code-block:: apacheconf

  [options]
  limit_memory_hard = 1677721600
  limit_memory_soft = 629145600
  limit_request = 8192
  limit_time_cpu = 600
  limit_time_real = 1200
  max_cron_threads = 1
  workers = 8


HTTPS
=====

Whether it's accessed via website/web client or the webservice, Odoo transmits
authentication information in cleartext. This means a secure deployment of
Odoo must use HTTPS\ [#switching]_. SSL termination can be implemented via
just about any SSL termination proxy, but requires the following setup:

* enable Odoo's :option:`proxy mode <odoo.py --proxy-mode>`. This should only be enabled when Odoo is behind a reverse proxy
* set up the SSL termination proxy (`Nginx termination example`_)
* set up the proxying itself (`Nginx proxying example`_)
* your SSL termination proxy should also automatically redirect non-secure
connections to the secure port

.. warning::

  In case you are using the Point of Sale module in combination with a `POSBox`_,
  you must disable the HTTPS configuration for the route ``/pos/web`` to avoid
  mixed-content errors.

Configuration sample
--------------------

* redirect http requests to https
* proxy requests to odoo

in ``/etc/odoo.conf`` set:

.. code-block:: apacheconf

  proxy_mode = True

in ``/etc/nginx/sites-enabled/odoo.conf`` set:

.. code-block:: apacheconf

  #odoo server
  upstream odoo {
   server 127.0.0.1:8069;
  }
  upstream odoochat {
   server 127.0.0.1:8072;
  }
  
  # http -> https
  server {
     listen 80;
     server_name odoo.mycompany.com;
     rewrite ^(.*) https://$host$1 permanent;
  }
  
  server {
   listen 443;
   server_name odoo.mycompany.com;
   proxy_read_timeout 720s;
   proxy_connect_timeout 720s;
   proxy_send_timeout 720s;
   
   # Add Headers for odoo proxy mode
   proxy_set_header X-Forwarded-Host $host;
   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   proxy_set_header X-Forwarded-Proto $scheme;
   proxy_set_header X-Real-IP $remote_addr;
   
   # SSL parameters
   ssl on;
   ssl_certificate /etc/ssl/nginx/server.crt;
   ssl_certificate_key /etc/ssl/nginx/server.key;
   ssl_session_timeout 30m;
   ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
   ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:CAMELLIA:DES-CBC3-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA';
   ssl_prefer_server_ciphers on;
   
   # log
   access_log /var/log/nginx/odoo.access.log;
   error_log /var/log/nginx/odoo.error.log;
   
   # Redirect requests to odoo backend server
   location / {
     proxy_redirect off;
     proxy_pass http://odoo;
   }
   location /longpolling {
       proxy_pass http://odoochat;
   }
 
   # common gzip
   gzip_types text/css text/less text/plain text/xml application/xml application/json application/javascript;
   gzip on;
  }
 
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
.. _POSBox: https://www.odoo.com/page/point-of-sale-hardware#part_2
