:banner: banners/web_service_api.jpg
:types: api


:code-column:

===============
Web Service API
===============

Odoo is usually extended internally via modules, but many of its features and
all of its data are also available from the outside for external analysis or
integration with various tools. Part of the :ref:`reference/orm/model` API is
easily available over XML-RPC_ and accessible from a variety of languages.

.. Odoo XML-RPC idiosyncracies:
   * uses multiple endpoint and a nested call syntax instead of a
     "hierarchical" server structure (e.g. ``openerp.res.partner.read()``)
   * uses its own own manual auth system instead of basic auth or sessions
     (basic is directly supported the Python and Ruby stdlibs as well as
     ws-xmlrpc, not sure about ripcord)
   * own auth is inconvenient as (uid, password) have to be explicitly passed
     into every call. Session would allow db to be stored as well
   These issues are especially visible in Java, somewhat less so in PHP

Connection
==========

.. kinda gross because it duplicates existing bits

.. only:: html

    .. rst-class:: setupcode hidden

        .. code-block:: python

            import xmlrpclib
            info = xmlrpclib.ServerProxy('https://demo.odoo.com/start').start()
            url, db, username, password = \
                info['host'], info['database'], info['user'], info['password']
            common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
            uid = common.authenticate(db, username, password, {})
            models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))

        .. code-block:: ruby

            require "xmlrpc/client"
            info = XMLRPC::Client.new2('https://demo.odoo.com/start').call('start')
            url, db, username, password = \
                info['host'], info['database'], info['user'], info['password']
            common = XMLRPC::Client.new2("#{url}/xmlrpc/2/common")
            uid = common.call('authenticate', db, username, password, {})
            models = XMLRPC::Client.new2("#{url}/xmlrpc/2/object").proxy

        .. code-block:: php

            require_once('ripcord.php');
            $info = ripcord::client('https://demo.odoo.com/start')->start();
            list($url, $db, $username, $password) =
              array($info['host'], $info['database'], $info['user'], $info['password']);
            $common = ripcord::client("$url/xmlrpc/2/common");
            $uid = $common->authenticate($db, $username, $password, array());
            $models = ripcord::client("$url/xmlrpc/2/object");

        .. code-block:: java

            final XmlRpcClient client = new XmlRpcClient();
            final XmlRpcClientConfigImpl start_config = new XmlRpcClientConfigImpl();
            start_config.setServerURL(new URL("https://demo.odoo.com/start"));
            final Map<String, String> info = (Map<String, String>)client.execute(
                start_config, "start", emptyList());

            final String url = info.get("host"),
                          db = info.get("database"),
                    username = info.get("user"),
                    password = info.get("password");

            final XmlRpcClientConfigImpl common_config = new XmlRpcClientConfigImpl();
            common_config.setServerURL(new URL(String.format("%s/xmlrpc/2/common", url)));

            int uid = (int)client.execute(
                common_config, "authenticate", Arrays.asList(
                    db, username, password, emptyMap()));

            final XmlRpcClient models = new XmlRpcClient() {{
                setConfig(new XmlRpcClientConfigImpl() {{
                    setServerURL(new URL(String.format("%s/xmlrpc/2/object", url)));
                }});
            }};

Configuration
-------------

If you already have an Odoo server installed, you can just use its
parameters

.. rst-class:: setup doc-aside

.. switcher::

    .. code-block:: python

        url = <insert server URL>
        db = <insert database name>
        username = 'admin'
        password = <insert password for your admin user (default: admin)>

    .. code-block:: ruby

        url = <insert server URL>
        db = <insert database name>
        username = "admin"
        password = <insert password for your admin user (default: admin)>

    .. code-block:: php

        $url = <insert server URL>;
        $db = <insert database name>;
        $username = "admin";
        $password = <insert password for your admin user (default: admin)>;

    .. code-block:: java

        final String url = <insert server URL>,
                      db = <insert database name>,
                username = "admin",
                password = <insert password for your admin user (default: admin)>;

To make exploration simpler, you can also ask https://demo.odoo.com for a test
database:

.. rst-class:: setup doc-aside

.. switcher::

    .. code-block:: python

        import xmlrpclib
        info = xmlrpclib.ServerProxy('https://demo.odoo.com/start').start()
        url, db, username, password = \
            info['host'], info['database'], info['user'], info['password']

    .. code-block:: ruby

        require "xmlrpc/client"
        info = XMLRPC::Client.new2('https://demo.odoo.com/start').call('start')
        url, db, username, password = \
            info['host'], info['database'], info['user'], info['password']

    .. case:: PHP

        .. code-block:: php

            require_once('ripcord.php');
            $info = ripcord::client('https://demo.odoo.com/start')->start();
            list($url, $db, $username, $password) =
              array($info['host'], $info['database'], $info['user'], $info['password']);

        .. note::

            These examples use the `Ripcord <https://code.google.com/p/ripcord/>`_
            library, which provides a simple XML-RPC API. Ripcord requires that
            `XML-RPC support be enabled
            <http://php.net/manual/en/xmlrpc.installation.php>`_ in your PHP
            installation.

            Since calls are performed over
            `HTTPS <http://en.wikipedia.org/wiki/HTTP_Secure>`_, it also requires that
            the `OpenSSL extension
            <http://php.net/manual/en/openssl.installation.php>`_ be enabled.

    .. case:: Java

        .. code-block:: java

            final XmlRpcClient client = new XmlRpcClient();

            final XmlRpcClientConfigImpl start_config = new XmlRpcClientConfigImpl();
            start_config.setServerURL(new URL("https://demo.odoo.com/start"));
            final Map<String, String> info = (Map<String, String>)client.execute(
                start_config, "start", emptyList());

            final String url = info.get("host"),
                          db = info.get("database"),
                    username = info.get("user"),
                    password = info.get("password");

        .. note::

            These examples use the `Apache XML-RPC library
            <https://ws.apache.org/xmlrpc/>`_

            The examples do not include imports as these imports couldn't be
            pasted in the code.

Logging in
----------

Odoo requires users of the API to be authenticated before they can query most 
data.

The ``xmlrpc/2/common`` endpoint provides meta-calls which don't require
authentication, such as the authentication itself or fetching version
information. To verify if the connection information is correct before trying
to authenticate, the simplest call is to ask for the server's version. The
authentication itself is done through the ``authenticate`` function and
returns a user identifier (``uid``) used in authenticated calls instead of
the login.

.. rst-class:: setup doc-aside

.. switcher::

    .. code-block:: python

        common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
        common.version()

    .. code-block:: ruby

        common = XMLRPC::Client.new2("#{url}/xmlrpc/2/common")
        common.call('version')

    .. code-block:: php

        $common = ripcord::client("$url/xmlrpc/2/common");
        $common->version();

    .. code-block:: java

        final XmlRpcClientConfigImpl common_config = new XmlRpcClientConfigImpl();
        common_config.setServerURL(
            new URL(String.format("%s/xmlrpc/2/common", url)));
        client.execute(common_config, "version", emptyList());

.. rst-class:: doc-aside

.. code-block:: json

    {
        "server_version": "8.0",
        "server_version_info": [8, 0, 0, "final", 0],
        "server_serie": "8.0",
        "protocol_version": 1,
    }

.. rst-class:: setup doc-aside

.. switcher::

    .. code-block:: python

        uid = common.authenticate(db, username, password, {})

    .. code-block:: ruby

        uid = common.call('authenticate', db, username, password, {})

    .. code-block:: php

        $uid = $common->authenticate($db, $username, $password, array());

    .. code-block:: java

        int uid = (int)client.execute(
            common_config, "authenticate", asList(
                db, username, password, emptyMap()));

Calling methods
===============

The second endpoint is ``xmlrpc/2/object``, is used to call methods of odoo
models via the ``execute_kw`` RPC function.

Each call to ``execute_kw`` takes the following parameters:

* the database to use, a string
* the user id (retrieved through ``authenticate``), an integer
* the user's password, a string
* the model name, a string
* the method name, a string
* an array/list of parameters passed by position
* a mapping/dict of parameters to pass by keyword (optional)

.. container:: doc-aside

    For instance to see if we can read the ``res.partner`` model we can call
    ``check_access_rights`` with ``operation`` passed by position and
    ``raise_exception`` passed by keyword (in order to get a true/false result
    rather than true/error):

    .. rst-class:: setup

    .. switcher::

        .. code-block:: python

            models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))
            models.execute_kw(db, uid, password,
                'res.partner', 'check_access_rights',
                ['read'], {'raise_exception': False})

        .. code-block:: ruby

            models = XMLRPC::Client.new2("#{url}/xmlrpc/2/object").proxy
            models.execute_kw(db, uid, password,
                'res.partner', 'check_access_rights',
                ['read'], {raise_exception: false})

        .. code-block:: php

            $models = ripcord::client("$url/xmlrpc/2/object");
            $models->execute_kw($db, $uid, $password,
                'res.partner', 'check_access_rights',
                array('read'), array('raise_exception' => false));

        .. code-block:: java

            final XmlRpcClient models = new XmlRpcClient() {{
                setConfig(new XmlRpcClientConfigImpl() {{
                    setServerURL(new URL(String.format("%s/xmlrpc/2/object", url)));
                }});
            }};
            models.execute("execute_kw", asList(
                db, uid, password,
                "res.partner", "check_access_rights",
                asList("read"),
                new HashMap() {{ put("raise_exception", false); }}
            ));

    .. code-block:: json

        true

    .. todo:: this should be runnable and checked

List records
------------

Records can be listed and filtered via :meth:`~openerp.models.Model.search`.

:meth:`~openerp.models.Model.search` takes a mandatory
:ref:`domain <reference/orm/domains>` filter (possibly empty), and returns the
database identifiers of all records matching the filter. To list customer
companies for instance:

.. container:: doc-aside

    .. switcher::

        .. code-block:: python

            models.execute_kw(db, uid, password,
                'res.partner', 'search',
                [[['is_company', '=', True], ['customer', '=', True]]])

        .. code-block:: ruby

            models.execute_kw(db, uid, password,
                'res.partner', 'search',
                [[['is_company', '=', true], ['customer', '=', true]]])

        .. code-block:: php

            $models->execute_kw($db, $uid, $password,
                'res.partner', 'search', array(
                    array(array('is_company', '=', true),
                          array('customer', '=', true))));

        .. code-block:: java

            asList((Object[])models.execute("execute_kw", asList(
                db, uid, password,
                "res.partner", "search",
                asList(asList(
                    asList("is_company", "=", true),
                    asList("customer", "=", true)))
            )));

    .. code-block:: json

        [7, 18, 12, 14, 17, 19, 8, 31, 26, 16, 13, 20, 30, 22, 29, 15, 23, 28, 74]

Pagination
''''''''''

By default a search will return the ids of all records matching the
condition, which may be a huge number. ``offset`` and ``limit`` parameters are
available to only retrieve a subset of all matched records.

.. container:: doc-aside

    .. switcher::
    
        .. code-block:: python
    
            models.execute_kw(db, uid, password,
                'res.partner', 'search',
                [[['is_company', '=', True], ['customer', '=', True]]],
                {'offset': 10, 'limit': 5})
    
        .. code-block:: ruby
    
            models.execute_kw(db, uid, password,
                'res.partner', 'search',
                [[['is_company', '=', true], ['customer', '=', true]]],
                {offset: 10, limit: 5})
    
        .. code-block:: php
    
            $models->execute_kw($db, $uid, $password,
                'res.partner', 'search',
                array(array(array('is_company', '=', true),
                            array('customer', '=', true))),
                array('offset'=>10, 'limit'=>5));
    
        .. code-block:: java
    
            asList((Object[])models.execute("execute_kw", asList(
                db, uid, password,
                "res.partner", "search",
                asList(asList(
                    asList("is_company", "=", true),
                    asList("customer", "=", true))),
                new HashMap() {{ put("offset", 10); put("limit", 5); }}
            )));
    
    .. code-block:: json
    
        [13, 20, 30, 22, 29]

Count records
-------------

Rather than retrieve a possibly gigantic list of records and count them,
:meth:`~openerp.models.Model.search_count` can be used to retrieve
only the number of records matching the query. It takes the same
:ref:`domain <reference/orm/domains>` filter as
:meth:`~openerp.models.Model.search` and no other parameter.

.. container:: doc-aside

    .. switcher::
    
        .. code-block:: python
    
            models.execute_kw(db, uid, password,
                'res.partner', 'search_count',
                [[['is_company', '=', True], ['customer', '=', True]]])
    
        .. code-block:: ruby
    
            models.execute_kw(db, uid, password,
                'res.partner', 'search_count',
                [[['is_company', '=', true], ['customer', '=', true]]])
    
        .. code-block:: php
    
            $models->execute_kw($db, $uid, $password,
                'res.partner', 'search_count',
                array(array(array('is_company', '=', true),
                            array('customer', '=', true))));
    
        .. code-block:: java
    
            (Integer)models.execute("execute_kw", asList(
                db, uid, password,
                "res.partner", "search_count",
                asList(asList(
                    asList("is_company", "=", true),
                    asList("customer", "=", true)))
            ));
    
    .. code-block:: json
    
        19

.. warning::

    calling ``search`` then ``search_count`` (or the other way around) may not
    yield coherent results if other users are using the server: stored data
    could have changed between the calls

Read records
------------

Record data is accessible via the :meth:`~openerp.models.Model.read` method,
which takes a list of ids (as returned by
:meth:`~openerp.models.Model.search`) and optionally a list of fields to
fetch. By default, it will fetch all the fields the current user can read,
which tends to be a huge amount.

.. container:: doc-aside
    
    .. switcher::
    
        .. code-block:: python
    
            ids = models.execute_kw(db, uid, password,
                'res.partner', 'search',
                [[['is_company', '=', True], ['customer', '=', True]]],
                {'limit': 1})
            [record] = models.execute_kw(db, uid, password,
                'res.partner', 'read', [ids])
            # count the number of fields fetched by default
            len(record)
    
        .. code-block:: ruby
    
            ids = models.execute_kw(db, uid, password,
                'res.partner', 'search',
                [[['is_company', '=', true], ['customer', '=', true]]],
                {limit: 1})
            record = models.execute_kw(db, uid, password,
                'res.partner', 'read', [ids]).first
            # count the number of fields fetched by default
            record.length
    
        .. code-block:: php
    
            $ids = $models->execute_kw($db, $uid, $password,
                'res.partner', 'search',
                array(array(array('is_company', '=', true),
                            array('customer', '=', true))),
                array('limit'=>1));
            $records = $models->execute_kw($db, $uid, $password,
                'res.partner', 'read', array($ids));
            // count the number of fields fetched by default
            count($records[0]);
    
        .. code-block:: java
    
            final List ids = asList((Object[])models.execute(
                "execute_kw", asList(
                    db, uid, password,
                    "res.partner", "search",
                    asList(asList(
                        asList("is_company", "=", true),
                        asList("customer", "=", true))),
                    new HashMap() {{ put("limit", 1); }})));
            final Map record = (Map)((Object[])models.execute(
                "execute_kw", asList(
                    db, uid, password,
                    "res.partner", "read",
                    asList(ids)
                )
            ))[0];
            // count the number of fields fetched by default
            record.size();
    
    .. code-block:: json
    
        121

Conversedly, picking only three fields deemed interesting.

.. container:: doc-aside

    .. switcher::

        .. code-block:: python

            models.execute_kw(db, uid, password,
                'res.partner', 'read',
                [ids], {'fields': ['name', 'country_id', 'comment']})

        .. code-block:: ruby

            models.execute_kw(db, uid, password,
                'res.partner', 'read',
                [ids], {fields: %w(name country_id comment)})

        .. code-block:: php

            $models->execute_kw($db, $uid, $password,
                'res.partner', 'read',
                array($ids),
                array('fields'=>array('name', 'country_id', 'comment')));

        .. code-block:: java

            asList((Object[])models.execute("execute_kw", asList(
                db, uid, password,
                "res.partner", "read",
                asList(ids),
                new HashMap() {{
                    put("fields", asList("name", "country_id", "comment"));
                }}
            )));

    .. code-block:: json

        [{"comment": false, "country_id": [21, "Belgium"], "id": 7, "name": "Agrolait"}]

.. note:: even if the ``id`` field is not requested, it is always returned

Listing record fields
---------------------

:meth:`~openerp.models.Model.fields_get` can be used to inspect
a model's fields and check which ones seem to be of interest.

Because it returns a large amount of meta-information (it is also used by client
programs) it should be filtered before printing, the most interesting items
for a human user are ``string`` (the field's label), ``help`` (a help text if
available) and ``type`` (to know which values to expect, or to send when
updating a record):

.. container:: doc-aside

    .. switcher::

        .. code-block:: python

            models.execute_kw(
                db, uid, password, 'res.partner', 'fields_get',
                [], {'attributes': ['string', 'help', 'type']})

        .. code-block:: ruby

            models.execute_kw(
                db, uid, password, 'res.partner', 'fields_get',
                [], {attributes: %w(string help type)})

        .. code-block:: php

            $models->execute_kw($db, $uid, $password,
                'res.partner', 'fields_get',
                array(), array('attributes' => array('string', 'help', 'type')));

        .. code-block:: java

            (Map<String, Map<String, Object>>)models.execute("execute_kw", asList(
                db, uid, password,
                "res.partner", "fields_get",
                emptyList(),
                new HashMap() {{
                    put("attributes", asList("string", "help", "type"));
                }}
            ));

    .. code-block:: json

        {
            "ean13": {
                "type": "char",
                "help": "BarCode",
                "string": "EAN13"
            },
            "property_account_position": {
                "type": "many2one",
                "help": "The fiscal position will determine taxes and accounts used for the partner.",
                "string": "Fiscal Position"
            },
            "signup_valid": {
                "type": "boolean",
                "help": "",
                "string": "Signup Token is Valid"
            },
            "date_localization": {
                "type": "date",
                "help": "",
                "string": "Geo Localization Date"
            },
            "ref_companies": {
                "type": "one2many",
                "help": "",
                "string": "Companies that refers to partner"
            },
            "sale_order_count": {
                "type": "integer",
                "help": "",
                "string": "# of Sales Order"
            },
            "purchase_order_count": {
                "type": "integer",
                "help": "",
                "string": "# of Purchase Order"
            },

Search and read
---------------

Because it is a very common task, Odoo provides a
:meth:`~openerp.models.Model.search_read` shortcut which as its name notes is
equivalent to a :meth:`~openerp.models.Model.search` followed by a
:meth:`~openerp.models.Model.read`, but avoids having to perform two requests
and keep ids around.

Its arguments are similar to :meth:`~openerp.models.Model.search`'s, but it
can also take a list of ``fields`` (like :meth:`~openerp.models.Model.read`,
if that list is not provided it will fetch all fields of matched records):

.. container:: doc-aside

    .. switcher::

        .. code-block:: python

            models.execute_kw(db, uid, password,
                'res.partner', 'search_read',
                [[['is_company', '=', True], ['customer', '=', True]]],
                {'fields': ['name', 'country_id', 'comment'], 'limit': 5})

        .. code-block:: ruby

            models.execute_kw(db, uid, password,
                'res.partner', 'search_read',
                [[['is_company', '=', true], ['customer', '=', true]]],
                {fields: %w(name country_id comment), limit: 5})

        .. code-block:: php

            $models->execute_kw($db, $uid, $password,
                'res.partner', 'search_read',
                array(array(array('is_company', '=', true),
                            array('customer', '=', true))),
                array('fields'=>array('name', 'country_id', 'comment'), 'limit'=>5));

        .. code-block:: java

            asList((Object[])models.execute("execute_kw", asList(
                db, uid, password,
                "res.partner", "search_read",
                asList(asList(
                    asList("is_company", "=", true),
                    asList("customer", "=", true))),
                new HashMap() {{
                    put("fields", asList("name", "country_id", "comment"));
                    put("limit", 5);
                }}
            )));

    .. code-block:: json

        [
            {
                "comment": false,
                "country_id": [ 21, "Belgium" ],
                "id": 7,
                "name": "Agrolait"
            },
            {
                "comment": false,
                "country_id": [ 76, "France" ],
                "id": 18,
                "name": "Axelor"
            },
            {
                "comment": false,
                "country_id": [ 233, "United Kingdom" ],
                "id": 12,
                "name": "Bank Wealthy and sons"
            },
            {
                "comment": false,
                "country_id": [ 105, "India" ],
                "id": 14,
                "name": "Best Designers"
            },
            {
                "comment": false,
                "country_id": [ 76, "France" ],
                "id": 17,
                "name": "Camptocamp"
            }
        ]


Create records
--------------

Records of a model are created using :meth:`~openerp.models.Model.create`. The
method will create a single record and return its database identifier.

:meth:`~openerp.models.Model.create` takes a mapping of fields to values, used
to initialize the record. For any field which has a default value and is not
set through the mapping argument, the default value will be used.

.. container:: doc-aside

    .. switcher::

        .. code-block:: python

            id = models.execute_kw(db, uid, password, 'res.partner', 'create', [{
                'name': "New Partner",
            }])

        .. code-block:: ruby

            id = models.execute_kw(db, uid, password, 'res.partner', 'create', [{
                name: "New Partner",
            }])

        .. code-block:: php

            $id = $models->execute_kw($db, $uid, $password,
                'res.partner', 'create',
                array(array('name'=>"New Partner")));

        .. code-block:: java

            final Integer id = (Integer)models.execute("execute_kw", asList(
                db, uid, password,
                "res.partner", "create",
                asList(new HashMap() {{ put("name", "New Partner"); }})
            ));

    .. code-block:: json

        78

.. warning::

    while most value types are what would be expected (integer for
    :class:`~openerp.fields.Integer`, string for :class:`~openerp.fields.Char`
    or :class:`~openerp.fields.Text`),

    * :class:`~openerp.fields.Date`, :class:`~openerp.fields.Datetime` and
      :class:`~openerp.fields.Binary` fields use string values
    * :class:`~openerp.fields.One2many` and :class:`~openerp.fields.Many2many`
      use a special command protocol detailed in :meth:`the documentation to
      the write method <openerp.models.Model.write>`.

Update records
--------------

Records can be updated using :meth:`~openerp.models.Model.write`, it takes
a list of records to update and a mapping of updated fields to values similar
to :meth:`~openerp.models.Model.create`.

Multiple records can be updated simultanously, but they will all get the same
values for the fields being set. It is not currently possible to perform
"computed" updates (where the value being set depends on an existing value of
a record).

.. container:: doc-aside

    .. switcher::

        .. code-block:: python

            models.execute_kw(db, uid, password, 'res.partner', 'write', [[id], {
                'name': "Newer partner"
            }])
            # get record name after having changed it
            models.execute_kw(db, uid, password, 'res.partner', 'name_get', [[id]])

        .. code-block:: ruby

            models.execute_kw(db, uid, password, 'res.partner', 'write', [[id], {
                name: "Newer partner"
            }])
            # get record name after having changed it
            models.execute_kw(db, uid, password, 'res.partner', 'name_get', [[id]])

        .. code-block:: php

            $models->execute_kw($db, $uid, $password, 'res.partner', 'write',
                array(array($id), array('name'=>"Newer partner")));
            // get record name after having changed it
            $models->execute_kw($db, $uid, $password,
                'res.partner', 'name_get', array(array($id)));

        .. code-block:: java

            models.execute("execute_kw", asList(
                db, uid, password,
                "res.partner", "write",
                asList(
                    asList(id),
                    new HashMap() {{ put("name", "Newer Partner"); }}
                )
            ));
            // get record name after having changed it
            asList((Object[])models.execute("execute_kw", asList(
                db, uid, password,
                "res.partner", "name_get",
                asList(asList(id))
            )));

    .. code-block:: json

        [[78, "Newer partner"]]

Delete records
--------------

Records can be deleted in bulk by providing their ids to 
:meth:`~openerp.models.Model.unlink`.

.. container:: doc-aside

    .. switcher::

        .. code-block:: python

            models.execute_kw(db, uid, password, 'res.partner', 'unlink', [[id]])
            # check if the deleted record is still in the database
            models.execute_kw(db, uid, password,
                'res.partner', 'search', [[['id', '=', id]]])

        .. code-block:: ruby

            models.execute_kw(db, uid, password, 'res.partner', 'unlink', [[id]])
            # check if the deleted record is still in the database
            models.execute_kw(db, uid, password,
                'res.partner', 'search', [[['id', '=', id]]])

        .. code-block:: php

            $models->execute_kw($db, $uid, $password,
                'res.partner', 'unlink',
                array(array($id)));
            // check if the deleted record is still in the database
            $models->execute_kw($db, $uid, $password,
                'res.partner', 'search',
                array(array(array('id', '=', $id))));

        .. code-block:: java

            models.execute("execute_kw", asList(
                db, uid, password,
                "res.partner", "unlink",
                asList(asList(id))));
            // check if the deleted record is still in the database
            asList((Object[])models.execute("execute_kw", asList(
                db, uid, password,
                "res.partner", "search",
                asList(asList(asList("id", "=", 78)))
            )));

    .. code-block:: json

        []

Inspection and introspection
----------------------------

.. todo:: ``get_external_id`` is kinda crap and may not return an id: it just
          gets a random existing xid but won't generate one if there is no
          xid currently associated with the record. And operating with xids
          isn't exactly fun in RPC.

While we previously used :meth:`~openerp.models.Model.fields_get` to query a
model and have been using an arbitrary model from the start, Odoo stores
most model metadata inside a few meta-models which allow both querying the
system and altering models and fields (with some limitations) on the fly over
XML-RPC.

.. _reference/webservice/inspection/models:

``ir.model``
''''''''''''

Provides information about Odoo models via its various fields

``name``
    a human-readable description of the model
``model``
    the name of each model in the system
``state``
    whether the model was generated in Python code (``base``) or by creating
    an ``ir.model`` record (``manual``)
``field_id``
    list of the model's fields through a :class:`~openerp.fields.One2many` to
    :ref:`reference/webservice/inspection/fields`
``view_ids``
    :class:`~openerp.fields.One2many` to the :ref:`reference/views` defined
    for the model
``access_ids``
    :class:`~openerp.fields.One2many` relation to the
    :ref:`reference/security/acl` set on the model

``ir.model`` can be used to

* query the system for installed models (as a precondition to operations
  on the model or to explore the system's content)
* get information about a specific model (generally by listing the fields
  associated with it)
* create new models dynamically over RPC

.. warning::

    * "custom" model names must start with ``x_``
    * the ``state`` must be provided and ``manual``, otherwise the model will
      not be loaded
    * it is not possible to add new *methods* to a custom model, only fields

.. container:: doc-aside

    a custom model will initially contain only the "built-in" fields available
    on all models:

    .. switcher::

        .. code-block:: python

            models.execute_kw(db, uid, password, 'ir.model', 'create', [{
                'name': "Custom Model",
                'model': "x_custom_model",
                'state': 'manual',
            }])
            models.execute_kw(
                db, uid, password, 'x_custom_model', 'fields_get',
                [], {'attributes': ['string', 'help', 'type']})

        .. code-block:: php

            $models->execute_kw(
                $db, $uid, $password,
                'ir.model', 'create', array(array(
                    'name' => "Custom Model",
                    'model' => 'x_custom_model',
                    'state' => 'manual'
                ))
            );
            $models->execute_kw(
                $db, $uid, $password,
                'x_custom_model', 'fields_get',
                array(),
                array('attributes' => array('string', 'help', 'type'))
            );

        .. code-block:: ruby

            models.execute_kw(
                db, uid, password,
                'ir.model', 'create', [{
                    name: "Custom Model",
                    model: 'x_custom_model',
                    state: 'manual'
                }])
            fields = models.execute_kw(
                db, uid, password, 'x_custom_model', 'fields_get',
                [], {attributes: %w(string help type)})

        .. code-block:: java

            models.execute(
                "execute_kw", asList(
                    db, uid, password,
                    "ir.model", "create",
                    asList(new HashMap<String, Object>() {{
                        put("name", "Custom Model");
                        put("model", "x_custom_model");
                        put("state", "manual");
                    }})
            ));
            final Object fields = models.execute(
                "execute_kw", asList(
                    db, uid, password,
                    "x_custom_model", "fields_get",
                    emptyList(),
                    new HashMap<String, Object> () {{
                        put("attributes", asList(
                                "string",
                                "help",
                                "type"));
                    }}
            ));

    .. code-block:: json

        {
            "create_uid": {
                "type": "many2one",
                "string": "Created by"
            },
            "create_date": {
                "type": "datetime",
                "string": "Created on"
            },
            "__last_update": {
                "type": "datetime",
                "string": "Last Modified on"
            },
            "write_uid": {
                "type": "many2one",
                "string": "Last Updated by"
            },
            "write_date": {
                "type": "datetime",
                "string": "Last Updated on"
            },
            "display_name": {
                "type": "char",
                "string": "Display Name"
            },
            "id": {
                "type": "integer",
                "string": "Id"
            }
        }

.. _reference/webservice/inspection/fields:

``ir.model.fields``
'''''''''''''''''''

Provides information about the fields of Odoo models and allows adding
custom fields without using Python code

``model_id``
    :class:`~openerp.fields.Many2one` to
    :ref:`reference/webservice/inspection/models` to which the field belongs
``name``
    the field's technical name (used in ``read`` or ``write``)
``field_description``
    the field's user-readable label (e.g. ``string`` in ``fields_get``)
``ttype``
    the :ref:`type <reference/orm/fields>` of field to create
``state``
    whether the field was created via Python code (``base``) or via
    ``ir.model.fields`` (``manual``)
``required``, ``readonly``, ``translate``
    enables the corresponding flag on the field
``groups``
    :ref:`field-level access control <reference/security/fields>`, a
    :class:`~openerp.fields.Many2many` to ``res.groups``
``selection``, ``size``, ``on_delete``, ``relation``, ``relation_field``, ``domain``
    type-specific properties and customizations, see :ref:`the fields
    documentation <reference/orm/fields>` for details

Like custom models, only new fields created with ``state="manual"`` are
activated as actual fields on the model.

.. warning:: computed fields can not be added via ``ir.model.fields``, some
             field meta-information (defaults, onchange) can not be set either

.. todo:: maybe new-API fields could store constant ``default`` in a new
          column, maybe JSON-encoded?

.. container:: doc-aside

    .. switcher::

        .. code-block:: python

            id = models.execute_kw(db, uid, password, 'ir.model', 'create', [{
                'name': "Custom Model",
                'model': "x_custom",
                'state': 'manual',
            }])
            models.execute_kw(
                db, uid, password,
                'ir.model.fields', 'create', [{
                    'model_id': id,
                    'name': 'x_name',
                    'ttype': 'char',
                    'state': 'manual',
                    'required': True,
                }])
            record_id = models.execute_kw(
                db, uid, password,
                'x_custom', 'create', [{
                    'x_name': "test record",
                }])
            models.execute_kw(db, uid, password, 'x_custom', 'read', [[record_id]])

        .. code-block:: php

            $id = $models->execute_kw(
                $db, $uid, $password,
                'ir.model', 'create', array(array(
                    'name' => "Custom Model",
                    'model' => 'x_custom',
                    'state' => 'manual'
                ))
            );
            $models->execute_kw(
                $db, $uid, $password,
                'ir.model.fields', 'create', array(array(
                    'model_id' => $id,
                    'name' => 'x_name',
                    'ttype' => 'char',
                    'state' => 'manual',
                    'required' => true
                ))
            );
            $record_id = $models->execute_kw(
                $db, $uid, $password,
                'x_custom', 'create', array(array(
                    'x_name' => "test record"
                ))
            );
            $models->execute_kw(
                $db, $uid, $password,
                'x_custom', 'read',
                array(array($record_id)));

        .. code-block:: ruby

            id = models.execute_kw(
                db, uid, password,
                'ir.model', 'create', [{
                    name: "Custom Model",
                    model: "x_custom",
                    state: 'manual'
                }])
            models.execute_kw(
                db, uid, password,
                'ir.model.fields', 'create', [{
                    model_id: id,
                    name: "x_name",
                    ttype: "char",
                    state: "manual",
                    required: true
                }])
            record_id = models.execute_kw(
                db, uid, password,
                'x_custom', 'create', [{
                    x_name: "test record"
                }])
            models.execute_kw(
                db, uid, password,
                'x_custom', 'read', [[record_id]])

        .. code-block:: java

            final Integer id = (Integer)models.execute(
                "execute_kw", asList(
                    db, uid, password,
                    "ir.model", "create",
                    asList(new HashMap<String, Object>() {{
                        put("name", "Custom Model");
                        put("model", "x_custom");
                        put("state", "manual");
                    }})
            ));
            models.execute(
                "execute_kw", asList(
                    db, uid, password,
                    "ir.model.fields", "create",
                    asList(new HashMap<String, Object>() {{
                        put("model_id", id);
                        put("name", "x_name");
                        put("ttype", "char");
                        put("state", "manual");
                        put("required", true);
                    }})
            ));
            final Integer record_id = (Integer)models.execute(
                "execute_kw", asList(
                    db, uid, password,
                    "x_custom", "create",
                    asList(new HashMap<String, Object>() {{
                        put("x_name", "test record");
                    }})
            ));

            client.execute(
                "execute_kw", asList(
                    db, uid, password,
                    "x_custom", "read",
                    asList(asList(record_id))
            ));

    .. code-block:: json

        [
            {
                "create_uid": [1, "Administrator"],
                "x_name": "test record",
                "__last_update": "2014-11-12 16:32:13",
                "write_uid": [1, "Administrator"],
                "write_date": "2014-11-12 16:32:13",
                "create_date": "2014-11-12 16:32:13",
                "id": 1,
                "display_name": "test record"
            }
        ]

Workflow manipulations
----------------------

:ref:`reference/workflows` can be moved along by sending them *signals*.
Instead of using the top-level ``execute_kw``, signals are sent using
``exec_workflow``.

Signals are sent to a specific record, and possibly trigger a transition on
the workflow instance associated with the record.

.. container:: doc-aside

    .. warning:: this example needs ``account`` module installed

    .. switcher::

        .. code-block:: python

            client = models.execute_kw(
                db, uid, password,
                'res.partner', 'search_read',
                [[('customer', '=', True)]],
                {'limit': 1, 'fields': [
                    'property_account_receivable',
                    'property_payment_term',
                    'property_account_position']
                })[0]
            invoice_id = models.execute_kw(
                db, uid, password,
                'account.invoice', 'create', [{
                    'partner_id': client['id'],
                    'account_id': client['property_account_receivable'][0],
                    'invoice_line': [(0, False, {'name': "AAA"})]
                }])

            models.exec_workflow(
                db, uid, password, 'account.invoice', 'invoice_open', invoice_id)

        .. code-block:: php

            $client = $models->execute_kw(
                $db, $uid, $password,
                'res.partner', 'search_read',
                array(array(array('customer', '=', true))),
                array(
                    'limit' => 1,
                    'fields' => array(
                        'property_account_receivable',
                        'property_payment_term',
                        'property_account_position'
                    )))[0];
            $invoice_id = $models->execute_kw(
                $db, $uid, $password,
                'account.invoice', 'create', array(array(
                    'partner_id' => $client['id'],
                    'account_id' => $client['property_account_receivable'][0],
                    'invoice_line' => array(array(0, false, array('name' => "AAA")))
                )));

            $models->exec_workflow(
                $db, $uid, $password,
                'account.invoice', 'invoice_open',
                 $invoice_id);

        .. code-block:: ruby

            client = models.execute_kw(
                db, uid, password,
                'res.partner', 'search_read',
                [[['customer', '=', true]]],
                {limit: 1, fields: %w(property_account_receivable property_payment_term property_account_position)}
            )[0]
            invoice_id = models.execute_kw(
                db, uid, password,
                'account.invoice', 'create', [{
                    partner_id: client['id'],
                    account_id: client['property_account_receivable'][0],
                    invoice_line: [[0, false, {name: "AAA"}]]
                }])

            models.exec_workflow(
                db, uid, password,
                'account.invoice', 'invoice_open', invoice_id)

        .. code-block:: java

            final Map<String, Object> c = (Map<String, Object>)
                ((Object[])models.execute("execute_kw", asList(
                        db, uid, password,
                        "res.partner", "search_read",
                        asList(
                            asList(
                                asList("customer", "=", true))),
                        new HashMap<String, Object>() {{
                                put("limit", 1);
                                put("fields", asList(
                                    "property_account_receivable",
                                    "property_payment_term",
                                    "property_account_position"
                                ));
                            }}
                )))[0];
            final Integer invoice_id = (Integer)models.execute(
                "execute_kw", asList(
                    db, uid, password,
                    "account.invoice", "create",
                    asList(new HashMap<String, Object>() {{
                        put("partner_id", c.get("id"));
                        put("account_id", ((Object[])c.get("property_account_receivable"))[0]);
                        put("invoice_line", asList(
                            asList(0, false, new HashMap<String, Object>() {{
                                put("name", "AAA");
                            }})
                        ));
                    }})
            ));

            models.execute(
                "exec_workflow", asList(
                    db, uid, password,
                    "account.invoice", "invoice_open", invoice_id));

Report printing
---------------

Available reports can be listed by searching the ``ir.actions.report.xml``
model, fields of interest being

``model``
    the model on which the report applies, can be used to look for available
    reports on a specific model
``name``
    human-readable report name
``report_name``
    the technical name of the report, used to print it

Reports can be printed over RPC with the following information:

* the name of the report (``report_name``)
* the ids of the records to include in the report

.. container:: doc-aside

    .. switcher::

        .. code-block:: python

            invoice_ids = models.execute_kw(
                db, uid, password, 'account.invoice', 'search',
                [[('type', '=', 'out_invoice'), ('state', '=', 'open')]])
            report = xmlrpclib.ServerProxy('{}/xmlrpc/2/report'.format(url))
            result = report.render_report(
                db, uid, password, 'account.report_invoice', invoice_ids)
            report_data = result['result'].decode('base64')

        .. code-block:: php

            $invoice_ids = $models->execute_kw(
                $db, $uid, $password,
                'account.invoice', 'search',
                array(array(array('type', '=', 'out_invoice'),
                            array('state', '=', 'open'))));
            $report = ripcord::client("$url/xmlrpc/2/report");
            $result = $report->render_report(
                $db, $uid, $password,
                'account.report_invoice', $invoice_ids);
            $report_data = base64_decode($result['result']);

        .. code-block:: ruby

            require 'base64'
            invoice_ids = models.execute_kw(
                db, uid, password,
                'account.invoice', 'search',
                [[['type', '=', 'out_invoice'], ['state', '=', 'open']]])
            report = XMLRPC::Client.new2("#{url}/xmlrpc/2/report").proxy
            result = report.render_report(
                db, uid, password,
                'account.report_invoice', invoice_ids)
            report_data = Base64.decode64(result['result'])

        .. code-block:: java

            final Object[] invoice_ids = (Object[])models.execute(
                "execute_kw", asList(
                    db, uid, password,
                    "account.invoice", "search",
                    asList(asList(
                        asList("type", "=", "out_invoice"),
                        asList("state", "=", "open")))
            ));
            final XmlRpcClientConfigImpl report_config = new XmlRpcClientConfigImpl();
            report_config.setServerURL(
                new URL(String.format("%s/xmlrpc/2/report", url)));
            final Map<String, Object> result = (Map<String, Object>)client.execute(
                report_config, "render_report", asList(
                    db, uid, password,
                    "account.report_invoice",
                    invoice_ids));
            final byte[] report_data = DatatypeConverter.parseBase64Binary(
                (String)result.get("result"));

    .. note::

        the report is sent as PDF binary data encoded in base64_, it must be
        decoded and may need to be saved to disk before use

.. _PostgreSQL: http://www.postgresql.org
.. _XML-RPC: http://en.wikipedia.org/wiki/XML-RPC
.. _base64: http://en.wikipedia.org/wiki/Base64
