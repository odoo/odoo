
Web Controllers
===============

Web controllers are classes in OpenERP able to catch the http requests sent by any browser. They allow to generate
html pages to be served like any web server, implement new methods to be used by the Javascript client, etc...

Controllers File
----------------

By convention the controllers should be placed in the controllers directory of the module. Example:

.. code-block:: text

    web_example
    ├── controllers
    │   ├── __init__.py
    │   └── my_controllers.py
    ├── __init__.py
    └── __openerp__.py

In ``__init__.py`` you must add:

::

    import controllers

And here is the content of ``controllers/__init__.py``:

::
    
    import my_controllers

Now you can put the following content in ``controllers/my_controllers.py``:

::

    import openerp.addons.web.http as http
    from openerp.addons.web.http import request


Controller Declaration
----------------------

In your controllers file, you can now declare a controller this way:

::

    class MyController(http.Controller):
        _cp_path = '/my_url'

        @http.httprequest
        def some_html(self):
            return "<h1>This is a test</h1>"

        @http.jsonrequest
        def some_json(self):
            return {"sample_dictionary": "This is a sample JSON dictionary"}

A controller must inherit from ``http.Controller``. When defining a controller, you must define the url it will match.
This is the ``_cp_path`` class attribute.

Each time you define a method with ``@http.httprequest`` or ``@http.jsonrequest`` it defines a new part of url to
match. As example, the ``some_html()`` method will be called a client query the ``/my_url/some_html`` url.

If you want to match precisely the ``/my_url`` url, you must a define a method called ``index``. This is an exception
compared to other methods:

::

    @http.httprequest
    def index(self):
        return "<div>This is the /my_url</div>"

Pure HTTP Requests
------------------

You can define methods to get any requests using the ``@http.httprequest`` decorator. When doing so, you get the
HTTP parameters as named parameters of the method:

::

    @http.httprequest
    def say_hello(self, name):
        return "<h1>Hello %s</h1>" % name

This url could be contacted by typing this url in a browser: ``http://localhost:8069/my_url/say_hello?name=Nicolas``.

JSON Requests
-------------

The ``@http.jsonrequest`` decorator is used to define JSON requests. The OpenERP Javascript client can contact these
methods using the JSON-RPC protocol. JSON methods must return JSON. Like the HTTP methods they receive arguments
as named parameters (except these arguments are JSON-RPC parameters).

::

    @http.jsonrequest
    def division(self, i, j):
        return i / j # returns a number

Contacting Models
-----------------

To use the database you must access the OpenERP models. The global ``request`` object provides the necessary objects:

::

    @http.httprequest
    def my_name(self):
        my_user_record = request.registry.get("res.users").browse(request.cr, request.uid, request.ui)
        return "<h1>Your name is %s</h1>" % my_user_record.name

``request.registry`` is the registry that gives you access to the models. It is the equivalent of ``self.pool`` when
working inside OpenERP models.

``request.cr`` is the cursor object. This is the ``cr`` parameter you have to pass as first argument of every model
method in OpenERP.

``request.uid`` is the id of the current logged in user. This is the ``uid`` parameter you have to pass as second
argument of every model method in OpenERP.

Authorization Levels
--------------------

By default, all methods can only be used by users logged into OpenERP (OpenERP uses cookies to track logged users).
There are some cases when you need to enable not-logged in users to access some methods. To do so, add the
``http.noauth`` decorator to your method:

::

    @http.httprequest
    @http.noauth
    def hello(self):
        return "<div>Hello unknown user!</div>"

Please note the ``request.cr`` cursor will not be available in this case.
