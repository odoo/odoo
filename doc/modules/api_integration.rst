:classes: stripe

===========
Odoo as API
===========

Odoo is mostly extended internally via modules, but much of its features and
all of its data is also available from the outside for external analysis or
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

Connection and authentication
=============================

.. kinda gross because it duplicates existing bits

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
            start_config, "start", Collections.emptyList());

        final String url = info.get("host"),
                      db = info.get("database"),
                username = info.get("user"),
                password = info.get("password");

        final XmlRpcClientConfigImpl common_config = new XmlRpcClientConfigImpl();
        common_config.setServerURL(new URL(String.format("%s/xmlrpc/2/common", url)));

        int uid = (int)client.execute(
            common_config, "authenticate", Arrays.asList(
                db, username, password, Collections.emptyMap()));

        final XmlRpcClient models = new XmlRpcClient() {{
            setConfig(new XmlRpcClientConfigImpl() {{
                setServerURL(new URL(String.format("%s/xmlrpc/2/object", url)));
            }});
        }};

Configuration
-------------

If you already have an Odoo server installed, you can just use its
parameters

.. rst-class:: switchable setup

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

.. rst-class:: switchable setup

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

    .. code-block:: php

        require_once('ripcord.php');
        $info = ripcord::client('https://demo.odoo.com/start')->start();
        list($url, $db, $username, $password) =
          array($info['host'], $info['database'], $info['user'], $info['password']);

    .. code-block:: java

        final XmlRpcClient client = new XmlRpcClient();

        final XmlRpcClientConfigImpl start_config = new XmlRpcClientConfigImpl();
        start_config.setServerURL(new URL("https://demo.odoo.com/start"));
        final Map<String, String> info = (Map<String, String>)client.execute(
            start_config, "start", Collections.emptyList());

        final String url = info.get("host"),
                      db = info.get("database"),
                username = info.get("user"),
                password = info.get("password");

.. rst-class:: force-right

    .. note::
        :class: only-php

        These examples use the `Ripcord <https://code.google.com/p/ripcord/>`_
        library, which provides a simple XML-RPC API. Ripcord requires that
        `XML-RPC support be enabled
        <http://php.net/manual/en/xmlrpc.installation.php>`_ in your PHP
        installation.

        Since calls are performed over
        `HTTPS <http://en.wikipedia.org/wiki/HTTP_Secure>`_, it also requires that
        the `OpenSSL extension
        <http://php.net/manual/en/openssl.installation.php>`_ be enabled.

    .. note::
        :class: only-java

        These examples use the `Apache XML-RPC library
        <https://ws.apache.org/xmlrpc/>`_

Logging in
----------

Odoo requires users of the API to be authenticated before being able to query
much data.

The ``xmlrpc/2/common`` endpoint provides meta-calls which don't require
authentication, such as the authentication itself or fetching version
information. To verify if the connection information is correct before trying
to authenticate, the simplest call is to ask for the server's version. The
authentication itself is done through the ``authenticate`` function and
returns a user identifier (``uid``) used in authenticated calls instead of
the login.

.. rst-class:: switchable setup

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
        common_config.setServerURL(new URL(String.format("%s/xmlrpc/2/common", url)));
        client.execute(common_config, "version", Collections.emptyList());

.. code-block:: json

    {
        "server_version": "8.0",
        "server_version_info": [8, 0, 0, "final", 0],
        "server_serie": "8.0",
        "protocol_version": 1,
    }

.. rst-class:: switchable setup

    .. code-block:: python

        uid = common.authenticate(db, username, password, {})

    .. code-block:: ruby

        uid = common.call('authenticate', db, username, password, {})

    .. code-block:: php

        $uid = $common->authenticate($db, $username, $password, array());

    .. code-block:: java

        int uid = (int)client.execute(
            common_config, "authenticate", Arrays.asList(
                db, username, password, Collections.emptyMap()));

Calling methods
===============

The second — and most generally useful — is ``xmlrpc/2/object`` which is used
to call methods of odoo models via the ``execute_kw`` RPC function.

Each call to ``execute_kw`` takes the following parameters:

* the database to use, a string
* the user id (retrieved through ``authenticate``), an integer
* the user's password, a string
* the model name, a string
* the method name, a string
* an array/list of parameters passed by position
* a mapping/dict of parameters to pass by keyword (optional)

.. rst-class:: force-right

For instance to see if we can read the ``res.partner`` model we can call
``check_access_rights`` with ``operation`` passed by position and
``raise_exception`` passed by keyword (in order to get a true/false result
rather than true/error):

.. rst-class:: switchable setup

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
        models.execute("execute_kw", Arrays.asList(
            db, uid, password,
            "res.partner", "check_access_rights",
            Arrays.asList("read"),
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

.. rst-class:: switchable

    .. code-block:: python

        models.execute_kw(db, uid, password,
            'res.partner', 'search',
            [[['is_company', '=', True], ['customer', '=', True]]])

    .. code-block:: ruby

        models.execute_kw(db, uid, password,
            'res.partner', 'search',
            [[['is_company', '=', true], ['customer', '=', true]]])

    .. code-block:: php

        $domain = array(array('is_company', '=', true),
                        array('customer', '=', true));
        $models->execute_kw($db, $uid, $password,
            'res.partner', 'search', array($domain));

    .. code-block:: java

        final List domain = Arrays.asList(
            Arrays.asList("is_company", "=", true),
            Arrays.asList("customer", "=", true));
        Arrays.asList((Object[])models.execute("execute_kw", Arrays.asList(
            db, uid, password,
            "res.partner", "search",
            Arrays.asList(domain)
        )));

.. code-block:: json

    [7, 18, 12, 14, 17, 19, 8, 31, 26, 16, 13, 20, 30, 22, 29, 15, 23, 28, 74]

Pagination
''''''''''

By default a research will return the ids of all records matching the
condition, which may be a huge number. ``offset`` and ``limit`` parameters are
available to only retrieve a subset of all matched records.

.. rst-class:: switchable

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
            array($domain),
            array('offset'=>10, 'limit'=>5));

    .. code-block:: java

        Arrays.asList((Object[])models.execute("execute_kw", Arrays.asList(
            db, uid, password,
            "res.partner", "search",
            Arrays.asList(domain),
            new HashMap() {{ put("offset", 10); put("limit", 5); }}
        )));

.. code-block:: json

    [13, 20, 30, 22, 29]

Count records
-------------

Rather than retrieve a possibly gigantic list of records and count them
afterwards, :meth:`~openerp.models.Model.search_count` can be used to retrieve
only the number of records matching the query. It takes the same
:ref:`domain <reference/orm/domains>` filter as
:meth:`~openerp.models.Model.search` and no other parameter.

.. rst-class:: switchable

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
            array($domain));

    .. code-block:: java

        (Integer)models.execute("execute_kw", Arrays.asList(
            db, uid, password,
            "res.partner", "search_count",
            Arrays.asList(domain)
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

.. rst-class:: switchable

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
            array($domain),
            array('limit'=>1));
        $records = $models->execute_kw($db, $uid, $password,
            'res.partner', 'read', array($ids));
        // count the number of fields fetched by default
        count($records[0]);

    .. code-block:: java

        final List ids = Arrays.asList((Object[])models.execute(
            "execute_kw", Arrays.asList(
                db, uid, password,
                "res.partner", "search",
                Arrays.asList(domain),
                new HashMap() {{ put("limit", 1); }})));
        final Map record = (Map)((Object[])models.execute(
            "execute_kw", Arrays.asList(
                db, uid, password,
                "res.partner", "read",
                Arrays.asList(ids)
            )
        ))[0];
        // count the number of fields fetched by default
        record.size();

.. code-block:: json

    121

Conversedly, picking only three fields deemed interesting.

.. rst-class:: switchable

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

        Arrays.asList((Object[])models.execute("execute_kw", Arrays.asList(
            db, uid, password,
            "res.partner", "read",
            Arrays.asList(ids),
            new HashMap() {{
                put("fields", Arrays.asList("name", "country_id", "comment"));
            }}
        )));

.. code-block:: json

    [{"comment": false, "country_id": [21, "Belgium"], "id": 7, "name": "Agrolait"}]

.. note:: even if the ``id`` field is not requested, it is always returned

Listing record fields
---------------------

:meth:`~openerp.models.Model.fields_get` can be used to inspect
a model's fields and check which ones seem to be of interest.

Because
it returns a great amount of meta-information (it is also used by client
programs) it should be filtered before printing, the most interesting items
for a human user are ``string`` (the field's label), ``help`` (a help text if
available) and ``type`` (to know which values to expect, or to send when
updating a record):

.. rst-class:: switchable

    .. code-block:: python

        fields = models.execute_kw(db, uid, password, 'res.partner', 'fields_get', [])
        # filter keys of field attributes for display
        {field: {
                    k: v for k, v in attributes.iteritems()
                    if k in ['string', 'help', 'type']
                }
         for field, attributes in fields.iteritems()}

    .. code-block:: ruby

        fields = models.execute_kw(db, uid, password, 'res.partner', 'fields_get', [])
        # filter keys of field attributes for display
        fields.each {|k, v|
            fields[k] = v.keep_if {|kk, vv| %w(string help type).include? kk}
        }

    .. code-block:: php

        $fields_full = $models->execute_kw($db, $uid, $password,
            'res.partner', 'fields_get', array());
        // filter keys of field attributes for display
        $allowed = array_flip(array('string', 'help', 'type'));
        $fields = array();
        foreach($fields_full as $field => $attributes) {
          $fields[$field] = array_intersect_key($attributes, $allowed);
        }

    .. code-block:: java

        final Map<String, Map<String, Object>> fields  =
            (Map<String, Map<String, Object>>)models.execute("execute_kw", Arrays.asList(
                db, uid, password,
                "res.partner", "fields_get",
                Collections.emptyList()));
        // filter keys of field attributes for display
        final List<String> allowed = Arrays.asList("string", "help", "type");
        new HashMap<String, Map<String, Object>>() {{
            for(Entry<String, Map<String, Object>> item: fields.entrySet()) {
                put(item.getKey(), new HashMap<String, Object>() {{
                    for(Entry<String, Object> it: item.getValue().entrySet()) {
                        if (allowed.contains(it.getKey())) {
                            put(it.getKey(), it.getValue());
                        }
                    }
                }});
            }
        }};

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

Because that is a very common task, Odoo provides a
:meth:`~openerp.models.Model.search_read` shortcut which as its name notes is
equivalent to a :meth:`~openerp.models.Model.search` followed by a
:meth:`~openerp.models.Model.read`, but avoids having to perform two requests
and keep ids around. Its arguments are similar to
:meth:`~openerp.models.Model.search`'s, but it can also take a list of
``fields`` (like :meth:`~openerp.models.Model.read`, if that list is not
provided it'll fetch all fields of matched records):

.. rst-class:: switchable

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
            array($domain),
            array('fields'=>array('name', 'country_id', 'comment'), 'limit'=>5));

    .. code-block:: java

        Arrays.asList((Object[])models.execute("execute_kw", Arrays.asList(
            db, uid, password,
            "res.partner", "search_read",
            Arrays.asList(domain),
            new HashMap() {{
                put("fields", Arrays.asList("name", "country_id", "comment"));
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

.. rst-class:: switchable

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

        final Integer id = (Integer)models.execute("execute_kw", Arrays.asList(
            db, uid, password,
            "res.partner", "create",
            Arrays.asList(new HashMap() {{ put("name", "New Partner"); }})
        ));

.. code-block:: json

    78

Update records
--------------

.. rst-class:: switchable

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

        models.execute("execute_kw", Arrays.asList(
            db, uid, password,
            "res.partner", "write",
            Arrays.asList(
                Arrays.asList(id),
                new HashMap() {{ put("name", "Newer Partner"); }}
            )
        ));
        // get record name after having changed it
        Arrays.asList((Object[])models.execute("execute_kw", Arrays.asList(
            db, uid, password,
            "res.partner", "name_get",
            Arrays.asList(Arrays.asList(id))
        )));

.. code-block:: json

    [[78, "Newer partner"]]

Delete records
--------------

.. rst-class:: switchable

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

        models.execute("execute_kw", Arrays.asList(
            db, uid, password,
            "res.partner", "unlink",
            Arrays.asList(Arrays.asList(id))));
        // check if the deleted record is still in the database
        Arrays.asList((Object[])models.execute("execute_kw", Arrays.asList(
            db, uid, password,
            "res.partner", "search",
            Arrays.asList(Arrays.asList(Arrays.asList("id", "=", 78)))
        )));

.. code-block:: json

    []

.. _PostgreSQL: http://www.postgresql.org
.. _XML-RPC: http://en.wikipedia.org/wiki/XML-RPC
