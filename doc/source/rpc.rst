Outside the box: network interactions
=====================================

Building static displays is all nice and good and allows for neat
effects (and sometimes you're given data to display from third parties
so you don't have to make any effort), but a point generally comes
where you'll want to talk to the world and make some network requests.

OpenERP Web provides two primary APIs to handle this, a low-level
JSON-RPC based API communicating with the Python section of OpenERP
Web (and of your addon, if you have a Python part) and a high-level
API above that allowing your code to talk directly to the OpenERP
server, using familiar-looking calls.

All networking APIs are :doc:`asynchronous </async>`. As a result, all
of them will return :js:class:`Deferred` objects (whether they resolve
those with values or not). Understanding how those work before before
moving on is probably necessary.

High-level API: calling into OpenERP models
-------------------------------------------

Access to OpenERP object methods (made available through XML-RPC from
the server) is done via the :js:class:`openerp.web.Model` class. This
class maps ontwo the OpenERP server objects via two primary methods,
:js:func:`~openerp.web.Model.call` and
:js:func:`~openerp.web.Model.query`.

:js:func:`~openerp.web.Model.call` is a direct mapping to the
corresponding method of the OpenERP server object. Its usage is
similar to that of the OpenERP Model API, with three differences:

* The interface is :doc:`asynchronous </async>`, so instead of
  returning results directly RPC method calls will return
  :js:class:`Deferred` instances, which will themselves resolve to the
  result of the matching RPC call.

* Because ECMAScript 3/Javascript 1.5 doesnt feature any equivalent to
  ``__getattr__`` or ``method_missing``, there needs to be an explicit
  method to dispatch RPC methods.

* No notion of pooler, the model proxy is instantiated where needed,
  not fetched from an other (somewhat global) object

.. code-block:: javascript

    var Users = new Model('res.users');

    Users.call('change_password', ['oldpassword', 'newpassword'],
                      {context: some_context}).then(function (result) {
        // do something with change_password result
    });

:js:func:`~openerp.web.Model.query` is a shortcut for a builder-style
iterface to searches (``search`` + ``read`` in OpenERP RPC terms). It
returns a :js:class:`~openerp.web.Query` object which is immutable but
allows building new :js:class:`~openerp.web.Query` instances from the
first one, adding new properties or modifiying the parent object's:

.. code-block:: javascript

    Users.query(['name', 'login', 'user_email', 'signature'])
         .filter([['active', '=', true], ['company_id', '=', main_company]])
         .limit(15)
         .all().then(function (users) {
        // do work with users records
    });

The query is only actually performed when calling one of the query
serialization methods, :js:func:`~openerp.web.Query.all` and
:js:func:`~openerp.web.Query.first`. These methods will perform a new
RPC query every time they are called.

For that reason, it's actually possible to keep "intermediate" queries
around and use them differently/add new specifications on them.

.. js:class:: openerp.web.Model(name)

    .. js:attribute:: openerp.web.Model.name

        name of the OpenERP model this object is bound to

    .. js:function:: openerp.web.Model.call(method, args, kwargs)

         Calls the ``method`` method of the current model, with the
         provided positional and keyword arguments.

         :param String method: method to call over rpc on the
                               :js:attr:`~openerp.web.Model.name`
         :param Array<> args: positional arguments to pass to the
                              method, optional
         :param Object<> kwargs: keyword arguments to pass to the
                                 method, optional
         :rtype: Deferred<>         

    .. js:function:: openerp.web.Model.query(fields)

         :param Array<String> fields: list of fields to fetch during
                                      the search
         :returns: a :js:class:`~openerp.web.Query` object
                   representing the search to perform

.. js:class:: openerp.web.Query(fields)

    The first set of methods is the "fetching" methods. They perform
    RPC queries using the internal data of the object they're called
    on.

    .. js:function:: openerp.web.Query.all()

        Fetches the result of the current
        :js:class:`~openerp.web.Query` object's search.

        :rtype: Deferred<Array<>>

    .. js:function:: openerp.web.Query.first()

       Fetches the **first** result of the current
       :js:class:`~openerp.web.Query`, or ``null`` if the current
       :js:class:`~openerp.web.Query` does have any result.

       :rtype: Deferred<Object | null>

    .. js:function:: openerp.web.Query.count()

       Fetches the number of records the current
       :js:class:`~openerp.web.Query` would retrieve.

       :rtype: Deferred<Number>

    The second set of methods is the "mutator" methods, they create a
    **new** :js:class:`~openerp.web.Query` object with the relevant
    (internal) attribute either augmented or replaced.

    .. js:function:: openerp.web.Query.context(ctx)

       Adds the provided ``ctx`` to the query, on top of any existing
       context

    .. js:function:: openerp.web.Query.filter(domain)

       Adds the provided domain to the query, this domain is
       ``AND``-ed to the existing query domain.

    .. js:function:: opeenrp.web.Query.offset(offset)

       Sets the provided offset on the query. The new offset
       *replaces* the old one.

    .. js:function:: openerp.web.Query.limit(limit)

       Sets the provided limit on the query. The new limit *replaces*
       the old one.

    .. js:function:: openerp.web.Query.order_by(fields…)

       Overrides the model's natural order with the provided field
       specifications. Behaves much like Django's `QuerySet.order_by
       <https://docs.djangoproject.com/en/dev/ref/models/querysets/#order-by>`_:

       * Takes 1..n field names, in order of most to least importance
         (the first field is the first sorting key). Fields are
         provided as strings.

       * A field specifies an ascending order, unless it is prefixed
         with the minus sign "``-``" in which case the field is used
         in the descending order

       Divergences from Django's sorting include a lack of random sort
       (``?`` field) and the inability to "drill down" into relations
       for sorting.

Low-level API: RPC calls to Python side
---------------------------------------

