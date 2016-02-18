:banner: banners/upgrade_api.jpg
:types: api


:code-column:

.. _reference/upgrade-api:

===========
Upgrade API
===========

Introduction
~~~~~~~~~~~~

This document describes the API used to upgrade an Odoo database to a
higher version.

It allows a database to be upgraded without ressorting to the html form at
https://upgrade.odoo.com
Although the database will follow the same process described on that form.


The required steps are:

* creating a request
* uploading a database dump
* running the upgrade process
* obtaining the status of the database request
* downloading the upgraded database dump

The methods
~~~~~~~~~~~

.. _upgrade-api-create-method:

Creating a database upgrade request
===================================

This action creates a database request with the following information:

* your contract reference
* your email address
* the target version (the Odoo version you want to upgrade to)
* the purpose of your request (test or production)
* the database dump name (required but purely informative)
* optionally the server timezone (for Odoo source version < 6.1)

The ``create`` method
---------------------

.. py:function:: https://upgrade.odoo.com/database/v1/create

    Creates a database upgrade request

    :param str contract: (required) your enterprise contract reference
    :param str email: (required) your email address
    :param str target: (required) the Odoo version you want to upgrade to. Valid choices: 6.0, 6.1, 7.0, 8.0
    :param str aim: (required) the purpose of your upgrade database request. Valid choices: test, production.
    :param str filename: (required) a purely informative name for you database dump file
    :param str timezone: (optional) the timezone used by your server. Only for Odoo source version < 6.1
    :return: request result
    :rtype: json dictionary

The *create* method returns a json dictionary containing the following keys:

``failures``
''''''''''''

The list of errors.

A list of dictionaries, each dictionary giving information about one particular
error. Each dictionary can contain various keys depending of the type of error
but you will always get the ``reason`` and the ``message`` keys:

* ``reason``: the error type
* ``message``: a human friendly message

Some possible keys:

* ``code``: a faulty value
* ``value``: a faulty value
* ``expected``: a list of valid values

See a sample output aside.

.. rst-class:: setup doc-aside

.. switcher::

    .. code-block:: json

            {
              "failures": [
                {
                  "expected": [
                    "6.0",
                    "6.1",
                    "7.0",
                    "8.0",
                  ],
                  "message": "Invalid value \"5.0\"",
                  "reason": "TARGET:INVALID",
                  "value": "5.0"
                },
                {
                  "code": "M123456-abcxyz",
                  "message": "Can not find contract M123456-abcxyz",
                  "reason": "CONTRACT:NOT_FOUND"
                }
              ]
            }


``request``
'''''''''''

If the *create* method is successful, the value associated to the *request* key
will be a dictionary containing various information about the created request:

The most important keys are:

* ``id``: the request id
* ``key``: your private key for this request

These 2 values will be requested by the other methods (upload, process and status)

The other keys will be explained in the section describing the :ref:`status method <upgrade-api-status-method>`.


Sample script
'''''''''''''

Here are 2 examples of database upgrade request creation using:

* one in the python programming language using the pycurl library
* one in the bash programming language using `curl <http://curl.haxx.se>`_ (tool
  for transfering data using http) and `jq <https://stedolan.github.io/jq>`_ (JSON processor):

.. rst-class:: setup doc-aside

.. switcher::

    .. code-block:: python

        from urllib import urlencode
        from io import BytesIO
        import pycurl
        import json

        CREATE_URL = "https://upgrade.odoo.com/database/v1/create"
        CONTRACT = "M123456-abcdef"
        AIM = "test"
        TARGET = "8.0"
        EMAIL = "john.doe@example.com"
        FILENAME = "db_name.dump"

        fields = dict([
            ('aim', AIM),
            ('email', EMAIL),
            ('filename', DB_SOURCE),
            ('contract', CONTRACT),
            ('target', TARGET),
        ])
        postfields = urlencode(fields)

        c = pycurl.Curl()
        c.setopt(pycurl.URL, CREATE_URL)
        c.setopt(c.POSTFIELDS, postfields)
        data = BytesIO()
        c.setopt(c.WRITEFUNCTION, data.write)
        c.perform()

        # transform output into a dict:
        response = json.loads(data.getvalue())

        # get http status:
        http_code = c.getinfo(pycurl.HTTP_CODE)
        c.close()

    .. code-block:: bash

        CONTRACT=M123456-abcdef
        AIM=test
        TARGET=8.0
        EMAIL=john.doe@example.com
        FILENAME=db_name.dump
        CREATE_URL="https://upgrade.odoo.com/database/v1/create"
        URL_PARAMS="contract=${CONTRACT}&aim=${AIM}&target=${TARGET}&email=${EMAIL}&filename=${FILENAME}"
        curl -sS "${CREATE_URL}?${URL_PARAMS}" > create_result.json

        # check for failures
        failures=$(cat create_result.json | jq -r '.failures[]')
        if [ "$failures" != "" ]; then
          echo $failures | jq -r '.'
          exit 1
        fi

.. _upgrade-api-upload-method:

Uploading your database dump
============================

This action upload your database dump.

The ``upload`` method
---------------------

.. py:function:: https://upgrade.odoo.com/database/v1/upload

    Uploads a database dump

    :param str key: (required) your private key
    :param str request: (required) your request id
    :return: request result
    :rtype: json dictionary

The request id and the private key are obtained using the :ref:`create method
<upgrade-api-create-method>`

The result is a json dictionary containing the list of ``failures``, which
should be empty if everything went fine.

.. rst-class:: setup doc-aside

.. switcher::

    .. code-block:: python

        import os
        import pycurl
        from urllib import urlencode
        from io import BytesIO
        import json

        UPLOAD_URL = "https://upgrade.odoo.com/database/v1/upload"
        DUMPFILE = "openchs.70.cdump"

        fields = dict([
            ('request', '10534'),
            ('key', 'Aw7pItGVKFuZ_FOR3U8VFQ=='),
        ])
        headers = {"Content-Type": "application/octet-stream"}
        postfields = urlencode(fields)

        c = pycurl.Curl()
        c.setopt(pycurl.URL, UPLOAD_URL+"?"+postfields)
        c.setopt(pycurl.POST, 1)
        filesize = os.path.getsize(DUMPFILE)
        c.setopt(pycurl.POSTFIELDSIZE, filesize)
        fp = open(DUMPFILE, 'rb')
        c.setopt(pycurl.READFUNCTION, fp.read)
        c.setopt(
            pycurl.HTTPHEADER,
            ['%s: %s' % (k, headers[k]) for k in headers])

        c.perform()
        c.close()

    .. code-block:: bash

        UPLOAD_URL="https://upgrade.odoo.com/database/v1/upload"
        DUMPFILE="openchs.70.cdump"
        KEY="Aw7pItGVKFuZ_FOR3U8VFQ=="
        REQUEST_ID="10534"
        URL_PARAMS="key=${KEY}&request=${REQUEST_ID}"
        HEADER="Content-Type: application/octet-stream"
        curl -H $HEADER --data-binary "@${DUMPFILE}" "${UPLOAD_URL}?${URL_PARAMS}"

.. _upgrade-api-process-method:

Asking to process your request
==============================

This action ask the Upgrade Platform to process your database dump.

The ``process`` method
----------------------

.. py:function:: https://upgrade.odoo.com/database/v1/process

    Process a database dump

    :param str key: (required) your private key
    :param str request: (required) your request id
    :return: request result
    :rtype: json dictionary

The request id and the private key are obtained using the :ref:`create method
<upgrade-api-create-method>`

The result is a json dictionary containing the list of ``failures``, which
should be empty if everything went fine.

.. rst-class:: setup doc-aside

.. switcher::

    .. code-block:: python

        from urllib import urlencode
        from io import BytesIO
        import pycurl
        import json

        PROCESS_URL = "https://upgrade.odoo.com/database/v1/process"

        fields = dict([
            ('request', '10534'),
            ('key', 'Aw7pItGVKFuZ_FOR3U8VFQ=='),
        ])
        postfields = urlencode(fields)

        c = pycurl.Curl()
        c.setopt(pycurl.URL, PROCESS_URL)
        c.setopt(c.POSTFIELDS, postfields)
        data = BytesIO()
        c.setopt(c.WRITEFUNCTION, data.write)
        c.perform()

        # transform output into a dict:
        response = json.loads(data.getvalue())

        # get http status:
        http_code = c.getinfo(pycurl.HTTP_CODE)
        c.close()

    .. code-block:: bash

        PROCESS_URL="https://upgrade.odoo.com/database/v1/process"
        KEY="Aw7pItGVKFuZ_FOR3U8VFQ=="
        REQUEST_ID="10534"
        URL_PARAMS="key=${KEY}&request=${REQUEST_ID}"
        curl -sS "${PROCESS_URL}?${URL_PARAMS}"

.. _upgrade-api-status-method:

Obtaining your request status
=============================

This action ask the status of your database upgrade request.

The ``status`` method
---------------------

.. py:function:: https://upgrade.odoo.com/database/v1/status

    Ask the status of a database upgrade request

    :param str key: (required) your private key
    :param str request: (required) your request id
    :return: request result
    :rtype: json dictionary

The request id and the private key are obtained using the :ref:`create method
<upgrade-api-create-method>`

The result is a json dictionary containing various information about your
database upgrade request.

.. rst-class:: setup doc-aside

.. switcher::

    .. code-block:: python

        from urllib import urlencode
        from io import BytesIO
        import pycurl
        import json

        STATUS_URL = "https://upgrade.odoo.com/database/v1/status"

        fields = dict([
            ('request', '10534'),
            ('key', 'Aw7pItGVKFuZ_FOR3U8VFQ=='),
        ])
        postfields = urlencode(fields)

        c = pycurl.Curl()
        c.setopt(pycurl.URL, PROCESS_URL)
        c.setopt(c.POSTFIELDS, postfields)
        data = BytesIO()
        c.setopt(c.WRITEFUNCTION, data.write)
        c.perform()

        # transform output into a dict:
        response = json.loads(data.getvalue())

        c.close()

    .. code-block:: bash

        STATUS_URL="https://upgrade.odoo.com/database/v1/status"
        KEY="Aw7pItGVKFuZ_FOR3U8VFQ=="
        REQUEST_ID="10534"
        URL_PARAMS="key=${KEY}&request=${REQUEST_ID}"
        curl -sS "${PROCESS_URL}?${URL_PARAMS}"

Sample output
-------------

The ``request`` key contains various useful information about your request:

``id``
    the request id
``key``
    your private key
``email``
    the email address you supplied when creating the request
``target``
    the target Odoo version you supplied when creating the request
``aim``
    the purpose (test, production) of your database upgrade request you supplied when creating the request
``filename``
    the filename you supplied when creating the request
``timezone``
    the timezone you supplied when creating the request
``state``
    the state of your request
``issue_stage``
    the stage of the issue we have create on Odoo main server
``issue``
    the id of the issue we have create on Odoo main server
``status_url``
    the URL to access your database upgrade request html page
``notes_url``
    the URL to get the notes about your database upgrade
``original_sql_url``
    the URL used to get your uploaded (not upgraded) database as an SQL stream
``original_dump_url``
    the URL used to get your uploaded (not upgraded) database as an archive file
``upgraded_sql_url``
    the URL used to get your upgraded database as an SQL stream
``upgraded_dump_url``
    the URL used to get your upgraded database as an archive file
``modules_url``
    the URL used to get your custom modules
``filesize``
    the size of your uploaded database file
``database_uuid``
    the Unique ID of your database
``created_at``
    the date when you created the request
``estimated_time``
    an estimation of the time it takes to upgrade your database
``processed_at``
    time when your database upgrade was started
``elapsed``
    the time it takes to upgrade your database
``filestore``
    your attachments were converted to the filestore
``customer_message``
    an important message related to your request
``database_version``
    the guessed Odoo version of your uploaded (not upgraded) database
``postgresql``
    the guessed Postgresql version of your uploaded (not upgraded) database
``compressions``
    the compression methods used by your uploaded database

.. rst-class:: setup doc-aside

.. switcher::

    .. code-block:: json

        {
          "failures": [],
          "request": {
            "id": 10534,
            "key": "Aw7pItGVKFuZ_FOR3U8VFQ==",
            "email": "john.doe@example.com",
            "target": "8.0",
            "aim": "test",
            "filename": "db_name.dump",
            "timezone": null,
            "state": "draft",
            "issue_stage": "new",
            "issue": 648398,
            "status_url": "https://upgrade.odoo.com/database/eu1/10534/Aw7pItGVKFuZ_FOR3U8VFQ==/status",
            "notes_url": "https://upgrade.odoo.com/database/eu1/10534/Aw7pItGVKFuZ_FOR3U8VFQ==/upgraded/notes",
            "original_sql_url": "https://upgrade.odoo.com/database/eu1/10534/Aw7pItGVKFuZ_FOR3U8VFQ==/original/sql",
            "original_dump_url": "https://upgrade.odoo.com/database/eu1/10534/Aw7pItGVKFuZ_FOR3U8VFQ==/original/archive",
            "upgraded_sql_url": "https://upgrade.odoo.com/database/eu1/10534/Aw7pItGVKFuZ_FOR3U8VFQ==/upgraded/sql",
            "upgraded_dump_url": "https://upgrade.odoo.com/database/eu1/10534/Aw7pItGVKFuZ_FOR3U8VFQ==/upgraded/archive",
            "modules_url": "https://upgrade.odoo.com/database/eu1/10534/Aw7pItGVKFuZ_FOR3U8VFQ==/modules/archive",
            "filesize": "912.99 Kb",
            "database_uuid": null,
            "created_at": "2015-09-09 07:13:49",
            "estimated_time": null,
            "processed_at": null,
            "elapsed": "00:00",
            "filestore": false,
            "customer_message": null,
            "database_version": null,
            "postgresql": "9.4",
            "compressions": [
              "pgdmp_custom",
              "sql"
            ]
          }
        }


