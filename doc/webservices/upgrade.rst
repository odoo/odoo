:banner: banners/upgrade_api.jpg
:types: api


:code-column:

.. _reference/upgrade-api:

================
Database Upgrade
================

Introduction
~~~~~~~~~~~~

This document describes the API used to upgrade an Odoo database to a
higher version.

It allows a database to be upgraded without ressorting to the html form at
https://upgrade.odoo.com
Although the database will follow the same process described on that form.


The required steps are:

* :ref:`creating a request <upgrade-api-create-method>`
* :ref:`uploading a database dump <upgrade-api-upload-method>`
* :ref:`running the upgrade process <upgrade-api-process-method>`
* :ref:`obtaining the status of the database request <upgrade-api-status-method>`
* :ref:`downloading the upgraded database dump <upgrade-api-download-method>`

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
    :rtype: JSON dictionary

The *create* method returns a JSON dictionary containing the following keys:

.. _upgrade-api-json-failure:

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

There are 2 methods to upload your database dump:

* the ``upload`` method using the HTTPS protocol
* the ``request_sftp_access`` method using the SFTP protocol

The ``upload`` method
---------------------

It's the most simple and most straightforward way of uploading your database dump.
It uses the HTTPS protocol.

.. py:function:: https://upgrade.odoo.com/database/v1/upload

    Uploads a database dump

    :param str key: (required) your private key
    :param str request: (required) your request id
    :return: request result
    :rtype: JSON dictionary

The request id and the private key are obtained using the :ref:`create method
<upgrade-api-create-method>`

The result is a JSON dictionary containing the list of ``failures``, which
should be empty if everything went fine.

.. rst-class:: setup doc-aside

.. switcher::

    .. code-block:: python

        import os
        import pycurl
        from urllib import urlencode

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

.. _upgrade-api-request-sftp-access-method:

The ``request_sftp_access`` method
----------------------------------

This method is recommanded for big database dumps.
It uses the SFTP protocol and supports resuming.

It will create a temporary SFTP server where you can connect to and allow you
to upload your database dump using an SFTP client.

.. py:function:: https://upgrade.odoo.com/database/v1/request_sftp_access

    Creates an SFTP server

    :param str key: (required) your private key
    :param str request: (required) your request id
    :param str ssh_keys: (required) the path to a file listing the ssh public keys you'd like to use
    :return: request result
    :rtype: JSON dictionary

The request id and the private key are obtained using the :ref:`create method
<upgrade-api-create-method>`

The file listing your ssh public keys should be roughly similar to a standard ``authorized_keys`` file.
This file should only contains public keys, blank lines or comments (lines starting with the ``#`` character)

Your database upgrade request should be in the ``draft`` state.

The ``request_sftp_access`` method returns a JSON dictionary containing the following keys:


.. rst-class:: setup doc-aside

.. switcher::

    .. code-block:: python

        import os
        import pycurl
        from urllib import urlencode

        UPLOAD_URL = "https://upgrade.odoo.com/database/v1/request_sftp_access"
        SSH_KEYS="/path/to/your/authorized_keys"

        fields = dict([
            ('request', '10534'),
            ('key', 'Aw7pItGVKFuZ_FOR3U8VFQ=='),
        ])
        postfields = urlencode(fields)

        c = pycurl.Curl()
        c.setopt(pycurl.URL, UPLOAD_URL+"?"+postfields)
        c.setopt(pycurl.POST, 1)
        c.setopt(c.HTTPPOST,[("ssh_keys",
                                (c.FORM_FILE, SSH_KEYS,
                                c.FORM_CONTENTTYPE, "text/plain"))
                            ])

        c.perform()
        c.close()

    .. code-block:: bash

        REQUEST_SFTP_ACCESS_URL="https://upgrade.odoo.com/database/v1/request_sftp_access"
        SSH_KEYS=/path/to/your/authorized_keys
        KEY="Aw7pItGVKFuZ_FOR3U8VFQ=="
        REQUEST_ID="10534"
        URL_PARAMS="key=${KEY}&request=${REQUEST_ID}"

        curl -sS "${REQUEST_SFTP_ACCESS_URL}?${URL_PARAMS}" -F ssh_keys=@${SSH_KEYS} > request_sftp_result.json

        # check for failures
        failures=$(cat request_sftp_result.json | jq -r '.failures[]')
        if [ "$failures" != "" ]; then
          echo $failures | jq -r '.'
          exit 1
        fi


``failures``
''''''''''''

The list of errors. See :ref:`failures <upgrade-api-json-failure>` for an
explanation about the JSON dictionary returned in case of failure.

``request``
'''''''''''

If the call is successful, the value associated to the *request* key
will be a dictionary containing your SFTP connexion parameters:

* ``hostname``: the host address to connect to
* ``sftp_port``: the port to connect to
* ``sftp_user``: the SFTP user to use for connecting
* ``shared_file``: the filename you need to use (identical to the ``filename`` value you have used when creating the request in the :ref:`create method <upgrade-api-create-method>`.)
* ``request_id``: the related upgrade request id (only informative, ,not required for the connection)
* ``sample_command``: a sample command using the 'sftp' client

You should normally be able to connect using the sample command as is.

You will only have access to the ``shared_file``. No other files will be
accessible and you will not be able to create new files in your shared
environment on the SFTP server.

Using the 'sftp' client
+++++++++++++++++++++++

Once you have successfully connected using your SFTP client, you can upload
your database dump. Here is a sample session using the 'sftp' client:

::

    $ sftp -P 2200 user_10534@upgrade.odoo.com
    Connected to upgrade.odoo.com.
    sftp> put /path/to/openchs.70.cdump openchs.70.cdump
    Uploading /path/to/openchs.70.cdump to /openchs.70.cdump
    sftp> ls -l openchs.70.cdump
    -rw-rw-rw-    0 0        0          849920 Aug 30 15:58 openchs.70.cdump

If your connection is interrupted, you can continue your file transfer using
the ``-a`` command line switch:

.. code-block:: text

    sftp> put -a /path/to/openchs.70.cdump openchs.70.cdump
    Resuming upload of /path/to/openchs.70.cdump to /openchs.70.cdump

If you don't want to manually type the command and need to automate your
database upgrade using a script, you can use a batch file or pipe your commands to 'sftp':

::

  echo "put /path/to/openchs.70.cdump openchs.70.cdump" | sftp -b - -P 2200 user_10534@upgrade.odoo.com

The ``-b`` parameter takes a filename. If the filename is ``-``, it reads the commands from standard input.


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
    :rtype: JSON dictionary

The request id and the private key are obtained using the :ref:`create method
<upgrade-api-create-method>`

The result is a JSON dictionary containing the list of ``failures``, which
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
    :rtype: JSON dictionary

The request id and the private key are obtained using the :ref:`create method
<upgrade-api-create-method>`

The result is a JSON dictionary containing various information about your
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
        curl -sS "${STATUS_URL}?${URL_PARAMS}"

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

.. _upgrade-api-download-method:

Downloading your database dump
==============================

Beside downloading your migrated database using the URL provided by the
:ref:`status method <upgrade-api-status-method>`, you can also use the SFTP
protocol as described in the :ref:`request_sftp_access method
<upgrade-api-request-sftp-access-method>`

The diffence is that you'll only be able to download the migrated database. No
uploading will be possible.

Your database upgrade request should be in the ``done`` state.

Once you have successfully connected using your SFTP client, you can download
your database dump. Here is a sample session using the 'sftp' client:

::

    $ sftp -P 2200 user_10534@upgrade.odoo.com
    Connected to upgrade.odoo.com.
    sftp> get upgraded_openchs.70.cdump /path/to/upgraded_openchs.70.cdump
    Downloading /upgraded_openchs.70.cdump to /path/to/upgraded_openchs.70.cdump

