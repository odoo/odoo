RPC Calls
=========

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
class maps onto the OpenERP server objects via two primary methods,
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
interface to searches (``search`` + ``read`` in OpenERP RPC terms). It
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
RPC call every time they are called.

For that reason, it's actually possible to keep "intermediate" queries
around and use them differently/add new specifications on them.

.. js:class:: openerp.web.Model(name)

    .. js:attribute:: openerp.web.Model.name

        name of the OpenERP model this object is bound to

    .. js:function:: openerp.web.Model.call(method[, args][, kwargs])

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

    .. js:function:: openerp.web.Query.group_by(grouping...)

       Fetches the groups for the query, using the first specified
       grouping parameter

       :param Array<String> grouping: Lists the levels of grouping
                                      asked of the server. Grouping
                                      can actually be an array or
                                      varargs.
       :rtype: Deferred<Array<openerp.web.QueryGroup>> | null

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

Aggregation (grouping)
~~~~~~~~~~~~~~~~~~~~~~

OpenERP has powerful grouping capacities, but they are kind-of strange
in that they're recursive, and level n+1 relies on data provided
directly by the grouping at level n. As a result, while ``read_group``
works it's not a very intuitive API.

OpenERP Web 7.0 eschews direct calls to ``read_group`` in favor of
calling a method of :js:class:`~openerp.web.Query`, `much in the way
it is one in SQLAlchemy
<http://docs.sqlalchemy.org/en/latest/orm/query.html#sqlalchemy.orm.query.Query.group_by>`_ [#]_:

.. code-block:: javascript

    some_query.group_by(['field1', 'field2']).then(function (groups) {
        // do things with the fetched groups
    });

This method is asynchronous when provided with 1..n fields (to group
on) as argument, but it can also be called without any field (empty
fields collection or nothing at all). In this case, instead of
returning a Deferred object it will return ``null``.

When grouping criterion come from a third-party and may or may not
list fields (e.g. could be an empty list), this provides two ways to
test the presence of actual subgroups (versus the need to perform a
regular query for records):

* A check on ``group_by``'s result and two completely separate code
  paths

  .. code-block:: javascript

      var groups;
      if (groups = some_query.group_by(gby)) {
          groups.then(function (gs) {
              // groups
          });
      }
      // no groups

* Or a more coherent code path using :js:func:`when`'s ability to
  coerce values into deferreds:

  .. code-block:: javascript

      $.when(some_query.group_by(gby)).then(function (groups) {
          if (!groups) {
              // No grouping
          } else {
              // grouping, even if there are no groups (groups
              // itself could be an empty array)
          }
      });

The result of a (successful) :js:func:`~openerp.web.Query.group_by` is
an array of :js:class:`~openerp.web.QueryGroup`.

.. _rpc_rpc:

Low-level API: RPC calls to Python side
---------------------------------------

While the previous section is great for calling core OpenERP code
(models code), it does not work if you want to call the Python side of
OpenERP Web.

For this, a lower-level API exists on on
:js:class:`~openerp.web.Connection` objects (usually available through
``openerp.connection``): the ``rpc`` method.

This method simply takes an absolute path (which is the combination of
the Python controller's ``_cp_path`` attribute and the name of the
method you want to call) and a mapping of attributes to values (applied
as keyword arguments on the Python method [#]_). This function fetches
the return value of the Python methods, converted to JSON.

For instance, to call the ``resequence`` of the
:class:`~web.controllers.main.DataSet` controller:

.. code-block:: javascript

    openerp.connection.rpc('/web/dataset/resequence', {
        model: some_model,
        ids: array_of_ids,
        offset: 42
    }).then(function (result) {
        // resequenced on server
    });

.. [#] with a small twist: SQLAlchemy's ``orm.query.Query.group_by``
       is not terminal, it returns a query which can still be altered.

.. [#] except for ``context``, which is extracted and stored in the
       request object itself.
