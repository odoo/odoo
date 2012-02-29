API changes from OpenERP Web 6.1 to 6.2
=======================================

DataSet -> Model
----------------

The 6.1 ``DataSet`` API has been deprecated in favor of the smaller
and more orthogonal :doc:`Model </rpc>` API, which more closely
matches the API in OpenERP Web's Python side and in OpenObject addons
and removes most stateful behavior of DataSet.

Migration guide
~~~~~~~~~~~~~~~

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
