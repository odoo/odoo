
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

    import openerp.http as http
    from openerp.http import request


Controller Declaration
----------------------

In your controllers file, you can now declare a controller this way:

::

    class MyController(http.Controller):

        @http.route('/my_url/some_html', type="http")
        def some_html(self):
            return "<h1>This is a test</h1>"

        @http.route('/my_url/some_json', type="json")
        def some_json(self):
            return {"sample_dictionary": "This is a sample JSON dictionary"}

A controller must inherit from ``http.Controller``. Each time you define a method with ``@http.route()`` it defines a
url to match. As example, the ``some_html()`` method will be called a client query the ``/my_url/some_html`` url.

Pure HTTP Requests
------------------

You can define methods to get any normal http requests by passing ``'http'`` to the ``type`` argument of
``http.route()``. When doing so, you get the HTTP parameters as named parameters of the method:

::

    @http.route('/say_hello', type="http")
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

URL Patterns
------------

Any URL passed to ``http.route()`` can contain patterns. Example:

::

    @http.route('/files/<path:file_path>', type="http")
    def files(self, file_path):
        ... # return a file identified by the path store in the 'my_path' variable

When such patterns are used, the method will received additional parameters that correspond to the parameters defined in
the url. For exact documentation about url patterns, see Werkzeug's documentation:
http://werkzeug.pocoo.org/docs/routing/ .

Also note you can pass multiple urls to ``http.route()``:


::

    @http.route(['/files/<path:file_path>', '/other_url/<path:file_path>'], type="http")
    def files(self, file_path):
        ...

Contacting Models
-----------------

To use the database you must access the OpenERP models. The global ``request`` object provides the necessary objects:

::

    @http.route('/my_name', type="http")
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

By default, all access to the models will use the rights of the currently logged in user (OpenERP uses cookies to track
logged users). It is also impossible to reach an URL without being logged (the user's browser will receive an HTTP
error).

There are some cases when the current user is not relevant, and we just want to give access to anyone to an URL. A
typical example is be the generation of a home page for a website. The home page should be visible by anyone, whether
they have an account or not. To do so, add the ``'admin'`` value to the ``auth`` parameter of ``http.route()``:

::

    @http.route('/hello', type="http", auth="admin")
    def hello(self):
        return "<div>Hello unknown user!</div>"

When using the ``admin`` authentication the access to the OpenERP models will be performed with the ``Administrator``
user and ``request.uid`` will be equal to ``openerp.SUPERUSER_ID`` (the id of the administrator).

It is important to note that when using the ``Administrator`` user all security is bypassed. So the programmers
implementing such methods should take great care of not creating security issues in the application.

Overriding Controllers
----------------------

Existing routes can be overridden. To do so, create a controller that inherit the controller containing the route you
want to override. Example that redefine the home page of your OpenERP application.

::

    import openerp.addons.web.controllers.main as main

    class Home2(main.Home):
        @http.route('/', type="http", auth="db")
        def index(self):
            return "<div>This is my new home page.</div>"

By re-defining the ``index()`` method, you change the behavior of the original ``Home`` class. Now the ``'/'`` route
will match the new ``index()`` method in ``Home2``.
