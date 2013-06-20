
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

        @http.route('/my_url/some_html', type="html")
        def some_html(self):
            return "<h1>This is a test</h1>"

        @http.route('/my_url/some_json', type="json")
        def some_json(self):
            return {"sample_dictionary": "This is a sample JSON dictionary"}

A controller must inherit from ``http.Controller``. Each time you define a method with ``@http.route()`` it defines a
url to match. As example, the ``some_html()`` method will be called a client query the ``/my_url/some_html`` url.

Pure HTTP Requests
------------------

You can define methods to get any normal http requests by passing ``'html'`` to the ``type`` argument of
``http.route()``. When doing so, you get the HTTP parameters as named parameters of the method:

::

    @http.route('/say_hello', type="html")
    def say_hello(self, name):
        return "<h1>Hello %s</h1>" % name

This url could be contacted by typing this url in a browser: ``http://localhost:8069/say_hello?name=Nicolas``.

JSON Requests
-------------

Methods that received JSON can be defined by passing ``'json'`` to the ``type`` argument of ``http.route()``. The
OpenERP Javascript client can contact these methods using the JSON-RPC protocol. JSON methods must return JSON. Like the
HTTP methods they receive arguments as named parameters (except these arguments are JSON-RPC parameters).

::

    @http.route('/division', type="json")
    def division(self, i, j):
        return i / j # returns a number

Contacting Models
-----------------

To use the database you must access the OpenERP models. The global ``request`` object provides the necessary objects:

::

    @http.route('/my_name', type="html")
    def my_name(self):
        my_user_record = request.registry.get("res.users").browse(request.cr, request.uid, request.uid)
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
There are some cases when you need to enable not-logged in users to access some methods. To do so, add the ``'noauth'``
value to the ``authentication`` parameter of ``http.route()``:

::

    @http.route('/hello', type="html", authentication="noauth")
    def hello(self):
        return "<div>Hello unknown user!</div>"

Please note the ``request.uid`` user id will be ``None`` inside this method call. This is due to the fact no user was
authenticated.
