API changes from OpenERP Web 6.1 to 7.0
=======================================

Supported browsers
------------------

The OpenERP Web Client supports the following web browsers:

* Internet Explorer 9+
* Google Chrome 22+
* Firefox 13+
* Any browser using the latest version of Chrome Frame

DataSet -> Model
----------------

The 6.1 ``DataSet`` API has been deprecated in favor of the smaller
and more orthogonal :doc:`Model </rpc>` API, which more closely
matches the API in OpenERP Web's Python side and in OpenObject addons
and removes most stateful behavior of DataSet.

Migration guide
~~~~~~~~~~~~~~~

* Actual arbitrary RPC calls can just be remapped on a
  :js:class:`~openerp.web.Model` instance:

  .. code-block:: javascript

      dataset.call(method, args)

  or

  .. code-block:: javascript

      dataset.call_and_eval(method, args)

  can be replaced by calls to :js:func:`openerp.web.Model.call`:

  .. code-block:: javascript

      model.call(method, args)

  If callbacks are passed directly to the older methods, they need to
  be added to the new one via ``.then()``.

  .. note::

      The ``context_index`` and ``domain_index`` features were not
      ported, context and domain now need to be passed in "in full",
      they won't be automatically filled with the user's current
      context.

* Shorcut methods (``name_get``, ``name_search``, ``unlink``,
  ``write``, ...) should be ported to
  :js:func:`openerp.web.Model.call`, using the server's original
  signature. On the other hand, the non-shortcut equivalents can now
  use keyword arguments (see :js:func:`~openerp.web.Model.call`'s
  signature for details)

* ``read_slice``, which allowed a single round-trip to perform a
  search and a read, should be reimplemented via
  :js:class:`~openerp.web.Query` objects (see:
  :js:func:`~openerp.web.Model.query`) for clearer and simpler
  code. ``read_index`` should be replaced by a
  :js:class:`~openerp.web.Query` as well, combining
  :js:func:`~openerp.web.Query.offset` and
  :js:func:`~openerp.web.Query.first`.

Rationale
~~~~~~~~~

Renaming

    The name *DataSet* exists in the CS community consciousness, and
    (as its name implies) it's a set of data (often fetched from a
    database, maybe lazily). OpenERP Web's dataset behaves very
    differently as it does not store (much) data (only a bunch of ids
    and just enough state to break things). The name "Model" matches
    the one used on the Python side for the task of building an RPC
    proxy to OpenERP objects.

API simplification

    ``DataSet`` has a number of methods which serve as little more
    than shortcuts, or are there due to domain and context evaluation
    issues in 6.1.

    The shortcuts really add little value, and OpenERP Web 6.2 embeds
    a restricted Python evaluator (in javascript) meaning most of the
    context and domain parsing & evaluation can be moved to the
    javascript code and does not require cooperative RPC bridging.

DataGroup -> also Model
-----------------------

Alongside the deprecation of ``DataSet`` for
:js:class:`~openerp.web.Model`, OpenERP Web 7.0 removes
``DataGroup`` and its subtypes as public objects in favor of a single method on
:js:class:`~openerp.web.Query`:
:js:func:`~openerp.web.Query.group_by`.

Migration guide
~~~~~~~~~~~~~~~

Rationale
~~~~~~~~~

While the ``DataGroup`` API worked (mostly), it is quite odd and
alien-looking, a bit too Smalltalk-inspired (behaves like a
self-contained flow-control structure for reasons which may or may not
have been good).

Because it is heavily related to ``DataSet`` (as it *yields*
``DataSet`` objects), deprecating ``DataSet`` automatically deprecates
``DataGroup`` (if we want to stay consistent), which is a good time to
make the API more imperative and look more like what most developers
are used to.

But as ``DataGroup`` users in 6.1 were rare (and there really was little reason
to use it), it has been removed as a public API.


