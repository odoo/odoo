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

Connection
==========

.. snippet:: sh
    :hide:

    set -e
    set -x

.. snippet:: python
    :hide:

    import urlparse
    import xmlrpclib

.. snippet:: ruby
    :hide:

    require 'uri'
    require 'xmlrpc/client'

.. snippet:: php
    :hide:

    <?php
    /*
    run instructions:
    * install Composer (http://getcomposer.org) or just download the latest
      non-snapshot composer.phar (https://getcomposer.org/download/) next to
      this script
    * run "composer require darkaonline/ripcord" (or "php composer.phar require darkaonline/ripcord")
    * run the script ("php api_integration.php")
    */
    require __DIR__ . '/vendor/autoload.php';
    use Ripcord\Ripcord as ripcord;

.. snippet:: java
    :hide:

    /*
    run instructions:
    * download/install sbt (http://www.scala-sbt.org)
    * next to this file, create a file "build.sbt" with the following content:
    name := "API Integration Examples"
    version := "0.1"
    resolvers += "Central" at "http://central.maven.org/maven2/"
    libraryDependencies += "org.apache.xmlrpc" % "xmlrpc-client" % "3.1.3"
    * run "sbt run" in this file's directory
    */
    import java.net.URL;
    import java.util.*;
    import org.apache.xmlrpc.client.XmlRpcClient;
    import org.apache.xmlrpc.client.XmlRpcClientConfigImpl;
    import static java.util.Arrays.asList;
    import static java.util.Collections.*;

    class api_integration {
        public static void main(String[] args)
            throws org.apache.xmlrpc.XmlRpcException,
                   java.net.MalformedURLException {

Configuration
-------------

If you already have an Odoo server installed, you can just use its
parameters.

.. warning::

    For Odoo Online instances (<domain>.odoo.com), users are created without a
    *local* password (as a person you are logged in via the Odoo Online
    authentication system, not by the instance itself). To use XML-RPC on Odoo
    Online instances, you will need to set a password on the user account you
    want to use:

    * Log in your instance with an administrator account
    * Go to :menuselection:`Settings --> Users --> Users`
    * Click on the user you want to use for XML-RPC access
    * Click the :guilabel:`Change Password` button
    * Set a :guilabel:`New Password` value then click
      :guilabel:`Change Password`.

    The *server url* is the instance's domain (e.g.
    *https://mycompany.odoo.com*), the *database name* is the name of the
    instance (e.g. *mycompany*). The *username* is the configured user's login
    as shown by the *Change Password* screen.

.. rst-class:: setup doc-aside

.. switcher::

    .. snippet:: python
        :indent: #

        url = <insert server URL>
        database = <insert database name>
        username = 'admin'
        password = <insert password for your admin user (default: admin)>

    .. snippet:: ruby
        :indent: #

        url = <insert server URL>
        database = <insert database name>
        username = "admin"
        password = <insert password for your admin user (default: admin)>

    .. snippet:: php
        :indent: //

        $url = <insert server URL>;
        $database = <insert database name>;
        $username = "admin";
        $password = <insert password for your admin user (default: admin)>;

    .. snippet:: java
        :indent: //

        final String url = <insert server URL>,
                database = <insert database name>,
                username = "admin",
                password = <insert password for your admin user (default: admin)>;

    .. snippet:: sh
        :indent: #

        url=<insert server URL>
        database=<insert database name>
        username="admin"
        password=<insert password for your admin user (default: admin)>

demo
''''

To make exploration simpler, you can also ask https://demo.odoo.com for a test
database.

.. todo:: curl/jsonrpc version of start?

.. rst-class:: setup doc-aside

.. switcher::

    .. snippet:: python

        info = xmlrpclib.ServerProxy('https://demo.odoo.com/start').start()
        url, database, username, password = \
            info['host'], info['database'], info['user'], info['password']

    .. snippet:: ruby

        info = XMLRPC::Client.new2('https://demo.odoo.com/start').call('start')
        url, database, username, password = \
            info['host'], info['database'], info['user'], info['password']

    .. case:: PHP

        .. snippet:: php

            $info = ripcord::client('https://demo.odoo.com/start')->start();
            list($url, $database, $username, $password) =
              [$info['host'], $info['database'], $info['user'], $info['password']];

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

        .. snippet:: java

            final XmlRpcClient client = new XmlRpcClient();

            final XmlRpcClientConfigImpl start_config = new XmlRpcClientConfigImpl();
            start_config.setServerURL(new URL("https://demo.odoo.com/start"));
            final Map<?, ?> info = (Map)client.execute(
                start_config, "start", emptyList());

            final String url = (String)info.get("host"),
                    database = (String)info.get("database"),
                    username = (String)info.get("user"),
                    password = (String)info.get("password");

        .. note::

            These examples use the `Apache XML-RPC library
            <https://ws.apache.org/xmlrpc/>`_

            The examples do not include imports as these imports couldn't be
            pasted in the code.

    .. case:: sh

        .. note::

            While higher-level languages have XML-RPC libraries, for shell
            examples we will hand-craft JSON-RPC2_ requests using cURL_,
            extracting data using jq_.

Logging in
----------

Odoo uses `Basic HTTP Authentication`_ for RPC authentication. The
authentication credentials are provided to the XML-RPC API either as part of
the URL or separately depending on the library.

The bare ``/RPC2`` endpoint handles meta calls (which may or may not require
authentication)

.. rst-class:: doc-aside

.. switcher::

    .. snippet:: python

        common = xmlrpclib.ServerProxy('{}/RPC2'.format(url))
        common.version()

    .. snippet:: ruby

        common = XMLRPC::Client.new2("#{url}/RPC2")
        common.call('version')

    .. snippet:: php

        $common = ripcord::client("${url}/RPC2");
        $common->version();

    .. snippet:: java

        final XmlRpcClient common = new XmlRpcClient();
        final XmlRpcClientConfigImpl common_config = new XmlRpcClientConfigImpl();
        common_config.setServerURL(
            new URL(String.format("%s/RPC2", url)));
        common.execute(common_config, "version", emptyList());

    .. case:: sh

        .. snippet:: sh

            curl -H "Content-Type: application/json" \
                 -s -X POST \
                 -d@- "$url/RPC2" \
                 <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "version",
                "params": []
            }
            !

        .. note::

            Using cURL_, we must manually set the ``Content-Type`` header
            (so that the RPC endpoint understands this is a JSON-RPC request)
            and ``POST`` it. ``-d@-`` lets us provide the JSON-RPC *request
            body* as a `here document`_ immediately following our command.

.. rst-class:: doc-aside

.. code-block:: json

    {
        "server_version": "8.0",
        "server_version_info": [8, 0, 0, "final", 0],
        "server_serie": "8.0",
        "protocol_version": 1,
    }

If a database name is provided through the ``db`` query parameter, the same
endpoint handles authenticated database-specific calls and the RPC client has
to be initialized with authentication.

.. rst-class:: doc-aside

.. switcher::

    .. snippet:: python

        db = xmlrpclib.ServerProxy(
            '{url.scheme}://{user}:{password}@{url.netloc}/RPC2?db={db}'.format(
                url=urlparse.urlsplit(url),
                db=database,
                user=username,
                password=password,
            ),
        )
        db.res.users.context_get(())

    .. snippet:: ruby

        url = URI.parse(url)
        port = url.port or url.class::DEFAULT_PORT
        db = XMLRPC::Client.new2(
            "#{url.scheme}://#{username}:#{password}@#{url.host}:#{port}/RPC2?db=#{database}"
        )
        db.call('res.users.context_get', [])

    .. snippet:: php

        $url = parse_url($url);
        $port = $url['port'] ?: getservbyname($url['scheme'], 'tcp');
        $db = Ripcord::client(
            "${url['scheme']}://$username:$password@${url['host']}:$port/RPC2?db=$database"
        );
        $db->res->users->context_get([]);

    .. snippet:: java

        final XmlRpcClient db = new XmlRpcClient();
        final XmlRpcClientConfigImpl dbConfig = new XmlRpcClientConfigImpl();
        dbConfig.setServerURL(new URL(url+"/RPC2?db="+database));
        dbConfig.setBasicUserName(username);
        dbConfig.setBasicPassword(password);
        db.setConfig(dbConfig);
        db.execute("res.users.context_get", asList(0));

    .. case:: sh

        .. snippet:: sh

            db="-u $username:$password -H Content-Type:application/json -s -X POST -d@- $url/RPC2?db=$database"
            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.users.context_get",
                "params": [[]]
            }
            !

        .. note::

            Using cURL_, `Basic HTTP Authentication`_ credentials are provided
            via the ``-u`` parameter.

Calling methods
===============

When connected to a specific database, the procedure name is the concatenation
of the model name, ``.`` and the method name. The parameters are:

* a mandatory subject, which provides both the records and context to use for
  the call (if any) and can be one of:

  - a falsy value (in the Python sense so an empty collection, the boolean
    false, a null, the integer 0, ...)
  - an array (list) of record ids
  - a struct (mapping/dict) with the keys ``ids`` (an array/list of record
    ids) and ``context`` (call's context)
* an optional array of positional parameters
* an optional struct of positional parameters

The result of the call is whatever the method returned, with a few
conversions:

* returned recordsets are converted to arrays of ids
* iterables are converted to arrays of whatever they contain
* mappings are converted to structs
* mapping keys are converted to strings
* other objects are converted to structs of their ``vars``

Depending on the API, it may also be possible to create or keep a proxy to a
model on which you can keep calling methods.

.. container:: doc-aside

    For instance to see if we can read the ``res.partner`` model we can call
    ``check_access_rights`` with no subject, ``operation`` passed by position
    and ``raise_exception`` passed by keyword (in order to get a true/false
    result rather than true/error):

    .. switcher::

        .. snippet:: python

            partners = db.res.partner
            partners.check_access_rights(
                (), ['read'], {'raise_exception': False})

        .. snippet:: ruby

            partners = db.proxy('res.partner')
            partners.check_access_rights(
                [], ['read'], {raise_exception: false})

        .. snippet:: php

            $partners = $db->res->partner;
            $partners->check_access_rights(
                [], ['read'], ['raise_exception' => false]);

        .. snippet:: java

            db.execute(
                "res.partner.check_access_rights", asList(
                0, asList("read"),
                new HashMap<String, Object>() {{ put("raise_exception", false); }}
            ));

        .. snippet:: sh

            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.check_access_rights",
                "params": [[], ["read"], {"raise_exception": false}]
            }
            !

    .. code-block:: json

        true

List records
------------

Records can be listed and filtered via :meth:`~odoo.models.Model.search`.

:meth:`~odoo.models.Model.search` takes a mandatory
:ref:`domain <reference/orm/domains>` filter (possibly empty), and returns the
database identifiers of all records matching the filter. To list customer
companies for instance:

.. container:: doc-aside

    .. switcher::

        .. snippet:: python

            partners.search((), [
                [['is_company', '=', True], ['customer', '=', True]]
            ])

        .. snippet:: ruby

            partners.search([], [
                [['is_company', '=', true], ['customer', '=', true]]
            ])

        .. snippet:: php

            $partners->search([], [
                [['is_company', '=', true], ['customer', '=', true]]
            ]);

        .. snippet:: java

            asList((Object[])db.execute(
                "res.partner.search", asList(0, asList(
                asList(
                    asList("is_company", "=", true),
                    asList("customer", "=", true))
            ))));

        .. snippet:: sh

            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.search",
                "params": [[], [
                    [["is_company", "=", true], ["customer", "=", true]]
                ]]
            }
            !

    .. code-block:: json

        [7, 18, 12, 14, 17, 19, 8, 31, 26, 16, 13, 20, 30, 22, 29, 15, 23, 28, 74]

Pagination
''''''''''

By default a search will return the ids of all records matching the
condition, which may be a huge number. ``offset`` and ``limit`` parameters are
available to only retrieve a subset of all matched records.

.. container:: doc-aside

    .. switcher::

        .. snippet:: python

            partners.search((), [
                [['is_company', '=', True], ['customer', '=', True]]
            ], {'offset': 10, 'limit': 5})

        .. snippet:: ruby

            partners.search([], [
                [['is_company', '=', true], ['customer', '=', true]]
            ], {offset: 10, limit: 5})

        .. snippet:: php

            $partners->search([], [
                [['is_company', '=', true], ['customer', '=', true]]
            ], ['offset'=>10, 'limit'=>5]);

        .. snippet:: java

            asList((Object[])db.execute(
                "res.partner.search", asList(0, asList(
                asList(
                    asList("is_company", "=", true),
                    asList("customer", "=", true))
            ), new HashMap<String, Object>() {{
                put("offset", 10);
                put("limit", 5);
            }}
            )));

        .. snippet:: sh

            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.search",
                "params": [[], [
                    [["is_company", "=", true], ["customer", "=", true]]
                ], {"offset": 10, "limit": 5}]
            }
            !

    .. code-block:: json

        [13, 20, 30, 22, 29]

Count records
-------------

Rather than retrieve a possibly gigantic list of records and count them,
:meth:`~odoo.models.Model.search_count` can be used to retrieve
only the number of records matching the query. It takes the same
:ref:`domain <reference/orm/domains>` filter as
:meth:`~odoo.models.Model.search` and no other parameter.

.. container:: doc-aside

    .. switcher::

        .. snippet:: python

            partners.search_count((), [
                [['is_company', '=', True], ['customer', '=', True]]
            ])

        .. snippet:: ruby

            partners.search_count([], [
                [['is_company', '=', true], ['customer', '=', true]]
            ])

        .. snippet:: php

            $partners->search_count([], [
                [['is_company', '=', true], ['customer', '=', true]]
            ]);

        .. snippet:: java

            Integer.class.cast(db.execute(
                "res.partner.search_count", asList(0, asList(
                asList(
                    asList("is_company", "=", true),
                    asList("customer", "=", true))
            ))));

        .. snippet:: sh

            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.search_count",
                "params": [[], [
                    [["is_company", "=", true], ["customer", "=", true]]
                ]]
            }
            !

    .. code-block:: json

        19

.. warning::

    calling ``search`` then ``search_count`` (or the other way around) may not
    yield coherent results if other users are using the server: stored data
    could have changed between the calls

Read records
------------

Record data is accessible via the :meth:`~odoo.models.Model.read` method,
which takes a list of ids (as returned by
:meth:`~odoo.models.Model.search`) and optionally a list of fields to
fetch. By default, it will fetch all the fields the current user can read,
which tends to be a huge amount.

.. container:: doc-aside

    .. switcher::

        .. snippet:: python

            ids = partners.search((), [
                [['is_company', '=', True], ['customer', '=', True]]
            ], {'limit': 1})
            [record] = partners.read(ids)
            # count the number of fields fetched by default
            len(record)

        .. snippet:: ruby

            ids = partners.search([], [
                [['is_company', '=', true], ['customer', '=', true]]
            ], {limit: 1})
            record = partners.read(ids).first
            # count the number of fields fetched by default
            record.length

        .. snippet:: php

            $ids = $partners->search([], [
                [['is_company', '=', true], ['customer', '=', true]]
            ], ['limit'=>1]);
            $records = $partners->read($ids);
            // count the number of fields fetched by default
            count($records[0]);

        .. snippet:: java

            final List ids = asList((Object[])db.execute(
                "res.partner.search", asList(0, asList(
                asList(
                    asList("is_company", "=", true),
                    asList("customer", "=", true))
            ), new HashMap<String, Object>() {{ put("limit", 1); }} )));
            final Map record = (Map)((Object[])db.execute(
                "res.partner.read", asList(ids)
            ))[0];
            // count the number of fields fetched by default
            record.size();

        .. snippet:: sh

            ids=$(curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.search",
                "params": [[], [
                    [["is_company", "=", true], ["customer", "=", true]]
                ], {"limit": 1}]
            }
            !
            )

            curl $db <<! | jq -e -c '.result[0] | length'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.read",
                "params": [$ids]
            }
            !

    .. code-block:: json

        121

Conversedly, picking only three fields deemed interesting.

.. container:: doc-aside

    .. switcher::

        .. snippet:: python

            partners.read(ids, {'fields': ['name', 'country_id', 'comment']})

        .. snippet:: ruby

            partners.read(ids, {fields: %w(name country_id comment)})

        .. snippet:: php

            $partners->read($ids, ['fields'=>['name', 'country_id', 'comment']]);

        .. snippet:: java

            asList((Object[])db.execute(
                "res.partner.read", asList(
                ids,
                new HashMap<String, Object>() {{
                    put("fields", asList("name", "country_id", "comment"));
                }}
            )));

        .. snippet:: sh

            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.read",
                "params": [$ids, {"fields": ["name", "country_id", "comment"]}]
            }
            !

    .. code-block:: json

        [{"comment": false, "country_id": [21, "Belgium"], "id": 7, "name": "Agrolait"}]

.. note:: even if the ``id`` field is not requested, it is always returned

Listing record fields
---------------------

:meth:`~odoo.models.Model.fields_get` can be used to inspect
a model's fields and check which ones seem to be of interest.

Because it returns a large amount of meta-information (it is also used by client
programs) it should be filtered before printing, the most interesting items
for a human user are ``string`` (the field's label), ``help`` (a help text if
available) and ``type`` (to know which values to expect, or to send when
updating a record):

.. container:: doc-aside

    .. switcher::

        .. snippet:: python

            partners.fields_get((), {'attributes': ['string', 'help', 'type']})

        .. snippet:: ruby

            partners.fields_get([], {attributes: %w(string help type)})

        .. snippet:: php

            $partners->fields_get([], ['attributes' => ['string', 'help', 'type']]);

        .. snippet:: java

            final Map<?, ?> m = (Map)db.execute(
                "res.partner.fields_get", asList(
                0,
                new HashMap<String, Object>() {{
                    put("attributes", asList("string", "help", "type"));
                }}
            ));

        .. snippet:: sh

            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.fields_get",
                "params": [[], {"attributes": ["string", "help", "type"]}]
            }
            !

    .. code-block:: json

        {
            "ean13": {
                "type": "char",
                "help": "BarCode",
                "string": "EAN13"
            },
            "property_account_position_id": {
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
            "ref_company_ids": {
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
:meth:`~odoo.models.Model.search_read` shortcut which as its name suggests is
equivalent to a :meth:`~odoo.models.Model.search` followed by a
:meth:`~odoo.models.Model.read`, but avoids having to perform two requests
and keep ids around.

Its arguments are similar to :meth:`~odoo.models.Model.search`'s, but it
can also take a list of ``fields`` (like :meth:`~odoo.models.Model.read`,
if that list is not provided it will fetch all fields of matched records):

.. container:: doc-aside

    .. switcher::

        .. snippet:: python

            partners.search_read((), [
                [['is_company', '=', True], ['customer', '=', True]]
            ], {'fields': ['name', 'country_id', 'comment'], 'limit': 5})

        .. snippet:: ruby

            partners.search_read([], [
                [['is_company', '=', true], ['customer', '=', true]]
            ], {fields: %w(name country_id comment), limit: 5})

        .. snippet:: php

            $partners->search_read([], [
                [['is_company', '=', true], ['customer', '=', true]]
            ], ['fields'=>['name', 'country_id', 'comment'], 'limit'=>5]);

        .. snippet:: java

            asList((Object[])db.execute(
                "res.partner.search_read", asList(
                0, asList(
                asList(
                    asList("is_company", "=", true),
                    asList("customer", "=", true))
            ), new HashMap<String, Object>() {{
                put("fields", asList("name", "country_id", "comment"));
                put("limit", 5);
            }})));

        .. snippet:: sh

            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.search_read",
                "params": [[], [
                    [["is_company", "=", true], ["customer", "=", true]]
                ], {"fields": ["name", "country_id", "comment"], "limit": 5}]
            }
            !

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

Records of a model are created using :meth:`~odoo.models.Model.create`. The
method will create a single record and return its database identifier.

:meth:`~odoo.models.Model.create` takes a mapping of fields to values, used
to initialize the record. For any field which has a default value and is not
set through the mapping argument, the default value will be used.

.. container:: doc-aside

    .. switcher::

        .. snippet:: python

            newids = partners.create((), [{
                'name': "New Partner",
            }])

        .. snippet:: ruby

            newids = partners.create([], [{
                name: "New Partner",
            }])

        .. snippet:: php

            $newids = $partners->create([], [[
                'name'=>"New Partner"
            ]]);

        .. snippet:: java

            final Object newids = db.execute(
                "res.partner.create", asList(0, asList(
                new HashMap<String, Object>() {{ put("name", "New Partner"); }}
            )));

        .. snippet:: sh

            newids=$(curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.create",
                "params": [[], [{
                    "name": "New Partner"
                }]]
            }
            !
            )

    .. code-block:: json

        78

.. warning::

    while most value types are what would be expected (integer for
    :class:`~odoo.fields.Integer`, string for :class:`~odoo.fields.Char`
    or :class:`~odoo.fields.Text`),

    * :class:`~odoo.fields.Date`, :class:`~odoo.fields.Datetime` and
      :class:`~odoo.fields.Binary` fields use string values
    * :class:`~odoo.fields.One2many` and :class:`~odoo.fields.Many2many`
      use a special command protocol detailed in :meth:`the documentation to
      the write method <odoo.models.Model.write>`.

Update records
--------------

Records can be updated using :meth:`~odoo.models.Model.write`, it takes
a list of records to update and a mapping of updated fields to values similar
to :meth:`~odoo.models.Model.create`.

Multiple records can be updated simultanously, but they will all get the same
values for the fields being set. It is not currently possible to perform
"computed" updates (where the value being set depends on an existing value of
a record).

.. container:: doc-aside

    .. switcher::

        .. snippet:: python

            partners.write(newids, [{
                'name': "Newer partner"
            }])
            # get record name after having changed it
            partners.name_get(newids)

        .. snippet:: ruby

            partners.write(newids, [{
                name: "Newer partner"
            }])
            # get record name after having changed it
            partners.name_get(newids)

        .. snippet:: php

            $partners->write($newids, [[
                'name'=>"Newer partner"
            ]]);
            // get record name after having changed it
            $partners->name_get($newids);

        .. snippet:: java

            db.execute(
                "res.partner.write", asList(
                newids, asList(
                new HashMap<String, Object>() {{ put("name", "Newer Partner"); }}
            )));
            // get record name after having changed it
            asList((Object[])db.execute(
                "res.partner.name_get", asList(
                newids
            )));

        .. snippet:: sh

            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.write",
                "params": [$newids, [{
                    "name": "Newer partner"
                }]]
            }
            !
            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.name_get",
                "params": [$newids]
            }
            !

    .. code-block:: json

        [[78, "Newer partner"]]

Delete records
--------------

Records can be deleted in bulk by providing their ids to
:meth:`~odoo.models.Model.unlink`.

.. container:: doc-aside

    .. switcher::

        .. snippet:: python

            partners.unlink(newids)
            # check if the deleted record is still in the database
            partners.search((), [[['id', 'in', newids]]])

        .. snippet:: ruby

            partners.unlink(newids)
            # check if the deleted record is still in the database
            partners.search([], [[['id', 'in', newids]]])

        .. snippet:: php

            $partners->unlink($newids);
            // check if the deleted record is still in the database
            $partners->search(0, [[['id', 'in', $newids]]]);

        .. snippet:: java

            db.execute("res.partner.unlink", asList(newids));
            // check if the deleted record is still in the database
            asList((Object[])db.execute(
                "res.partner.search", asList(
                0, asList(asList(asList("id", "in", newids)))
            )));

        .. snippet:: sh

            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.unlink",
                "params": [$newids]
            }
            !
            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "res.partner.search",
                "params": [[], [[["id", "in", $newids]]]]
            }
            !

    .. code-block:: json

        []

Inspection and introspection
----------------------------

.. todo:: ``get_external_id`` is kinda crap and may not return an id: it just
          gets a random existing xid but won't generate one if there is no
          xid currently associated with the record. And operating with xids
          isn't exactly fun in RPC.

While we previously used :meth:`~odoo.models.Model.fields_get` to query a
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
    list of the model's fields through a :class:`~odoo.fields.One2many` to
    :ref:`reference/webservice/inspection/fields`
``view_ids``
    :class:`~odoo.fields.One2many` to the :ref:`reference/views` defined
    for the model
``access_ids``
    :class:`~odoo.fields.One2many` relation to the
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

        .. snippet:: python

            db.ir.model.create((), [{
                'name': "Custom Model",
                'model': "x_custom_model",
                'state': 'manual',
            }])
            db.x_custom_model.fields_get((), {
                'attributes': ['string', 'help', 'type']
            })

        .. snippet:: php

            $db->ir->model->create([], [[
                'name' => "Custom Model",
                'model' => 'x_custom_model',
                'state' => 'manual'
            ]]);
            $db->x_custom_model->fields_get([], [
                'attributes' => ['string', 'help', 'type']
            ]);

        .. snippet:: ruby

            db.call('ir.model.create', [], [{
                name: "Custom Model",
                model: 'x_custom_model',
                state: 'manual'
            }])
            db.call('x_custom_model.fields_get', [], {
                attributes: %w(string help type)
            })

        .. snippet:: java

            db.execute(
                "ir.model.create", asList(0, asList(
                new HashMap<String, Object>() {{
                    put("name", "Custom Model");
                    put("model", "x_custom_model");
                    put("state", "manual");
                }}
            )));
            final Object fields = db.execute(
                "x_custom_model.fields_get", asList(
                0, asList(
                new HashMap<String, Object> () {{
                    put("attributes", asList(
                            "string",
                            "help",
                            "type"));
                }}
            )));

        .. snippet:: sh

            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "ir.model.create",
                "params": [[], [{
                    "name": "Custom Model",
                    "model": "x_custom_model",
                    "state": "manual"
                }]]
            }
            !
            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "x_custom_model.fields_get",
                "params": [[], {
                    "attributes": ["string", "help", "type"]
                }]
            }
            !

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
    :class:`~odoo.fields.Many2one` to
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
    :class:`~odoo.fields.Many2many` to ``res.groups``
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

        .. snippet:: python

            db.ir.model.create((), [{
                'name': "Custom Model",
                'model': "x_custom",
                'state': 'manual',
                'field_id': [(0, 0, {
                    'name': 'x_name',
                    'field_description': "Name",
                    'ttype': 'char',
                    'required': True,
                })],
            }])
            record_ids = db.x_custom.create((), [{
                'x_name': "test record",
            }])
            db.x_custom.read(record_ids)

        .. snippet:: php

            $db->ir->model->create([], [[
                'name' => "Custom Model",
                'model' => 'x_custom',
                'state' => 'manual',
                'field_id' => [[0, 0, [
                    'name' => 'x_name',
                    'field_description' => "Name",
                    'ttype' => 'char',
                    'required' => true
                ]]]
            ]]);
            $record_ids = $db->x_custom->create([], [[
                'x_name' => "test record"
            ]]);
            $db->x_custom->read($record_ids);

        .. snippet:: ruby

            db.call('ir.model.create', [], [{
                name: "Custom Model",
                model: "x_custom",
                state: 'manual',
                field_id: [[0, 0, {
                    name: "x_name",
                    field_description: "Name",
                    ttype: "char",
                    required: true
                }]]
            }])
            record_ids = db.call('x_custom.create', [], [{
                x_name: "test record"
            }])
            db.call('x_custom.read', record_ids)

        .. snippet:: java

            db.execute(
                "ir.model.create", asList(
                0, asList(new HashMap<String, Object>() {{
                    put("name", "Custom Model");
                    put("model", "x_custom");
                    put("state", "manual");
                    put("field_id", asList(asList(0, 0, new HashMap<String, Object>() {{
                        put("name", "x_name");
                        put("field_description", "Name");
                        put("ttype", "char");
                        put("required", true);
                    }})));
                }})
            ));
            final Object record_ids = db.execute(
                "x_custom.create", asList(
                0, asList(new HashMap<String, Object>() {{
                    put("x_name", "test record");
                }})
            ));

            db.execute("x_custom.read", asList(record_ids));

        .. snippet:: sh

            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "ir.model.create",
                "params": [[], [{
                    "name": "Custom Model",
                    "model": "x_custom",
                    "state": "manual",
                    "field_id": [[0, 0, {
                        "name": "x_name",
                        "field_description": "Name",
                        "ttype": "char",
                        "required": true
                    }]]
                }]]
            }
            !
            records_ids=$(curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "x_custom.create",
                "params": [[], [{
                    "x_name": "test record"
                }]]
            }
            !
            )
            curl $db <<! | jq -e -c '.result'
            {
                "jsonrpc": "2.0",
                "id": null,
                "method": "x_custom.read",
                "params": [$record_ids]
            }
            !

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

.. custom models cleanup
.. snippet:: python
    :hide:

    custom_ids = db.ir.model.search((), [
        [('model', 'ilike', 'x_custom')]
    ])
    db.ir.model.unlink(custom_ids)

.. snippet:: ruby
    :hide:

    custom_ids = db.call('ir.model.search', [], [
        [['model', 'ilike', 'x_custom']]
    ])
    db.call('ir.model.unlink', custom_ids)

.. snippet:: php
    :hide:

    $custom_ids = $db->ir->model->search([], [
        [['model', 'ilike', 'x_custom']]
    ]);
    $db->ir->model->unlink($custom_ids);

.. snippet:: java
    :hide:

    final Object custom_ids = db.execute(
        "ir.model.search", asList(
        0, asList(asList(
            asList("model", "ilike", "x_custom")
        ))
    ));
    db.execute("ir.model.unlink", asList(custom_ids));

.. snippet:: sh
    :hide:

    custom_ids=$(curl $db <<! | jq -e -c '.result'
    {
        "jsonrpc": "2.0",
        "id": null,
        "method": "ir.model.search",
        "params": [[], [
            [["model", "ilike", "x_custom"]]
        ]]
    }
    !
    )
    curl $db <<! | jq -e -c '.result'
    {
        "jsonrpc": "2.0",
        "id": null,
        "method": "ir.model.unlink",
        "params": [$custom_ids]
    }
    !

Report printing
---------------

Available reports can be listed by searching the ``ir.actions.report``
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

.. snippet:: java
    :hide:

        }
    }

.. _Basic HTTP Authentication: https://tools.ietf.org/html/rfc7617
.. _cURL: https://curl.haxx.se
.. _here document: http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_07_04
.. _jq: https://stedolan.github.io/jq/
.. _JSON-RPC2: http://www.jsonrpc.org/specification
.. _PostgreSQL: http://www.postgresql.org
.. _XML-RPC: http://en.wikipedia.org/wiki/XML-RPC
.. _base64: http://en.wikipedia.org/wiki/Base64
