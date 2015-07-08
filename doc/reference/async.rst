:orphan:

.. _reference/async:

Asynchronous Operations
=======================

As a language (and runtime), javascript is fundamentally
single-threaded. This means any blocking request or computation will
block the whole page (and, in older browsers, the software itself
even preventing users from switching to another tab): a javascript
environment can be seen as an event-based runloop where application
developers have no control over the runloop itself.

As a result, performing long-running synchronous network requests or
other types of complex and expensive accesses is frowned upon and
asynchronous APIs are used instead.

The goal of this guide is to provide some tools to deal with
asynchronous systems, and warn against systemic issues or dangers.

Deferreds
---------

Deferreds are a form of `promises`_. OpenERP Web currently uses
`jQuery's deferred`_.

The core idea of deferreds is that potentially asynchronous methods
will return a :js:class:`Deferred` object instead of an arbitrary
value or (most commonly) nothing.

This object can then be used to track the end of the asynchronous
operation by adding callbacks onto it, either success callbacks or
error callbacks.

A great advantage of deferreds over simply passing callback functions
directly to asynchronous methods is the ability to :ref:`compose them
<reference/async/composition>`.

Using deferreds
~~~~~~~~~~~~~~~

Deferreds's most important method is :js:func:`Deferred.then`. It is
used to attach new callbacks to the deferred object.

* the first parameter attaches a success callback, called when the
  deferred object is successfully resolved and provided with the
  resolved value(s) for the asynchronous operation.

* the second parameter attaches a failure callback, called when the
  deferred object is rejected and provided with rejection values
  (often some sort of error message).

Callbacks attached to deferreds are never "lost": if a callback is
attached to an already resolved or rejected deferred, the callback
will be called (or ignored) immediately. A deferred is also only ever
resolved or rejected once, and is either resolved or rejected: a given
deferred can not call a single success callback twice, or call both a
success and a failure callbacks.

:js:func:`~Deferred.then` should be the method you'll use most often
when interacting with deferred objects (and thus asynchronous APIs).

Building deferreds
~~~~~~~~~~~~~~~~~~

After using asynchronous APIs may come the time to build them: for
mocks_, to compose deferreds from multiple source in a complex
manner, in order to let the current operations repaint the screen or
give other events the time to unfold, ...

This is easy using jQuery's deferred objects.

.. note:: this section is an implementation detail of jQuery Deferred
          objects, the creation of promises is not part of any
          standard (even tentative) that I know of. If you are using
          deferred objects which are not jQuery's, their API may (and
          often will) be completely different.

Deferreds are created by invoking their constructor [#]_ without any
argument. This creates a :js:class:`Deferred` instance object with the
following methods:

:js:func:`Deferred.resolve`

    As its name indicates, this method moves the deferred to the
    "Resolved" state. It can be provided as many arguments as
    necessary, these arguments will be provided to any pending success
    callback.

:js:func:`Deferred.reject`

    Similar to :js:func:`~Deferred.resolve`, but moves the deferred to
    the "Rejected" state and calls pending failure handlers.

:js:func:`Deferred.promise`

    Creates a readonly view of the deferred object. It is generally a
    good idea to return a promise view of the deferred to prevent
    callers from resolving or rejecting the deferred in your stead.

:js:func:`~Deferred.reject` and :js:func:`~Deferred.resolve` are used
to inform callers that the asynchronous operation has failed (or
succeeded). These methods should simply be called when the
asynchronous operation has ended, to notify anybody interested in its
result(s).

.. _reference/async/composition:

Composing deferreds
~~~~~~~~~~~~~~~~~~~

What we've seen so far is pretty nice, but mostly doable by passing
functions to other functions (well adding functions post-facto would
probably be a chore... still, doable).

Deferreds truly shine when code needs to compose asynchronous
operations in some way or other, as they can be used as a basis for
such composition.

There are two main forms of compositions over deferred: multiplexing
and piping/cascading.

Deferred multiplexing
`````````````````````

The most common reason for multiplexing deferred is simply performing
multiple asynchronous operations and wanting to wait until all of them are
done before moving on (and executing more stuff).

The jQuery multiplexing function for promises is :js:func:`when`.

.. note:: the multiplexing behavior of jQuery's :js:func:`when` is an
          (incompatible, mostly) extension of the behavior defined in
          `CommonJS Promises/B`_.

This function can take any number of promises [#]_ and will return a
promise.

The returned promise will be resolved when *all* multiplexed promises
are resolved, and will be rejected as soon as one of the multiplexed
promises is rejected (it behaves like Python's ``all()``, but with
promise objects instead of boolean-ish).

The resolved values of the various promises multiplexed via
:js:func:`when` are mapped to the arguments of :js:func:`when`'s
success callback, if they are needed. The resolved values of a promise
are at the same index in the callback's arguments as the promise in
the :js:func:`when` call so you will have:

.. code-block:: javascript

    $.when(p0, p1, p2, p3).then(
            function (results0, results1, results2, results3) {
        // code
    });

.. warning::

    in a normal mapping, each parameter to the callback would be an
    array: each promise is conceptually resolved with an array of 0..n
    values and these values are passed to :js:func:`when`'s
    callback. But jQuery treats deferreds resolving a single value
    specially, and "unwraps" that value.

    For instance, in the code block above if the index of each promise
    is the number of values it resolves (0 to 3), ``results0`` is an
    empty array, ``results2`` is an array of 2 elements (a pair) but
    ``results1`` is the actual value resolved by ``p1``, not an array.

Deferred chaining
`````````````````

A second useful composition is starting an asynchronous operation as
the result of an other asynchronous operation, and wanting the result
of both: with the tools described so far, handling e.g. OpenERP's
search/read sequence with this would require something along the lines
of:

.. code-block:: javascript

    var result = $.Deferred();
    Model.search(condition).then(function (ids) {
        Model.read(ids, fields).then(function (records) {
            result.resolve(records);
        });
    });
    return result.promise();

While it doesn't look too bad for trivial code, this quickly gets
unwieldy.

But :js:func:`~Deferred.then` also allows handling this kind of
chains: it returns a new promise object, not the one it was called
with, and the return values of the callbacks is important to this behavior:
whichever callback is called,

* If the callback is not set (not provided or left to null), the
  resolution or rejection value(s) is simply forwarded to
  :js:func:`~Deferred.then`'s promise (it's essentially a noop)

* If the callback is set and does not return an observable object (a
  deferred or a promise), the value it returns (``undefined`` if it
  does not return anything) will replace the value it was given, e.g.

  .. code-block:: javascript

      promise.then(function () {
          console.log('called');
      });

  will resolve with the sole value ``undefined``.

* If the callback is set and returns an observable object, that object
  will be the actual resolution (and result) of the pipe. This means a
  resolved promise from the failure callback will resolve the pipe,
  and a failure promise from the success callback will reject the
  pipe.

  This provides an easy way to chain operation successes, and the
  previous piece of code can now be rewritten:

  .. code-block:: javascript

      return Model.search(condition).then(function (ids) {
          return Model.read(ids, fields);
      });

  the result of the whole expression will encode failure if either
  ``search`` or ``read`` fails (with the right rejection values), and
  will be resolved with ``read``'s resolution values if the chain
  executes correctly.

:js:func:`~Deferred.then` is also useful to adapt third-party
promise-based APIs, in order to filter their resolution value counts
for instance (to take advantage of :js:func:`when` 's special
treatment of single-value promises).

jQuery.Deferred API
~~~~~~~~~~~~~~~~~~~

.. js:function:: when(deferreds…)

    :param deferreds: deferred objects to multiplex
    :returns: a multiplexed deferred
    :rtype: :js:class:`Deferred`

.. js:class:: Deferred

    .. js:function:: Deferred.then(doneCallback[, failCallback])

        Attaches new callbacks to the resolution or rejection of the
        deferred object. Callbacks are executed in the order they are
        attached to the deferred.

        To provide only a failure callback, pass ``null`` as the
        ``doneCallback``, to provide only a success callback the
        second argument can just be ignored (and not passed at all).

        Returns a new deferred which resolves to the result of the
        corresponding callback, if a callback returns a deferred
        itself that new deferred will be used as the resolution of the
        chain.

        :param doneCallback: function called when the deferred is resolved
        :param failCallback: function called when the deferred is rejected
        :returns: the deferred object on which it was called
        :rtype: :js:class:`Deferred`

    .. js:function:: Deferred.done(doneCallback)

        Attaches a new success callback to the deferred, shortcut for
        ``deferred.then(doneCallback)``.

        .. note:: a difference is the result of :js:func:`Deferred.done`'s
                  is ignored rather than forwarded through the chain

        This is a jQuery extension to `CommonJS Promises/A`_ providing
        little value over calling :js:func:`~Deferred.then` directly,
        it should be avoided.

        :param doneCallback: function called when the deferred is resolved
        :type doneCallback: Function
        :returns: the deferred object on which it was called
        :rtype: :js:class:`Deferred`

    .. js:function:: Deferred.fail(failCallback)

        Attaches a new failure callback to the deferred, shortcut for
        ``deferred.then(null, failCallback)``.

        A second jQuery extension to `Promises/A <CommonJS
        Promises/A>`_. Although it provides more value than
        :js:func:`~Deferred.done`, it still is not much and should be
        avoided as well.

        :param failCallback: function called when the deferred is rejected
        :type failCallback: Function
        :returns: the deferred object on which it was called
        :rtype: :js:class:`Deferred`

    .. js:function:: Deferred.promise()

        Returns a read-only view of the deferred object, with all
        mutators (resolve and reject) methods removed.

    .. js:function:: Deferred.resolve(value…)

        Called to resolve a deferred, any value provided will be
        passed onto the success handlers of the deferred object.

        Resolving a deferred which has already been resolved or
        rejected has no effect.

    .. js:function:: Deferred.reject(value…)

        Called to reject (fail) a deferred, any value provided will be
        passed onto the failure handler of the deferred object.

        Rejecting a deferred which has already been resolved or
        rejected has no effect.

.. [#] or simply calling :js:class:`Deferred` as a function, the
       result is the same

.. [#] or not-promises, the `CommonJS Promises/B`_ role of
       :js:func:`when` is to be able to treat values and promises
       uniformly: :js:func:`when` will pass promises through directly,
       but non-promise values and objects will be transformed into a
       resolved promise (resolving themselves with the value itself).

       jQuery's :js:func:`when` keeps this behavior making deferreds
       easy to build from "static" values, or allowing defensive code
       where expected promises are wrapped in :js:func:`when` just in
       case.

.. _promises: http://en.wikipedia.org/wiki/Promise_(programming)
.. _jQuery's deferred: http://api.jquery.com/category/deferred-object/
.. _CommonJS Promises/A: http://wiki.commonjs.org/wiki/Promises/A
.. _CommonJS Promises/B: http://wiki.commonjs.org/wiki/Promises/B
.. _mocks: http://en.wikipedia.org/wiki/Mock_object
