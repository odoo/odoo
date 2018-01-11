* Parser
	since parsing expressions, try with a pratt parser
	http://journal.stuffwithstuff.com/2011/03/19/pratt-parsers-expression-parsing-made-easy/
	http://effbot.org/zone/simple-top-down-parsing.htm

Evaluator
---------

* Builtins should be built-in, there should be no need to add e.g. ``py.bool`` to the evaluation context (?)
* Stop busyworking trivial binary operator
* Make it *trivial* to build Python type-wrappers
* Implement Python's `data model protocols
  <http://docs.python.org/reference/datamodel.html#basic-customization>`_
  for *all* supported operations, optimizations can come later
* Automatically type-wrap everything (for now anyway)

Base type requirements:
***********************

* int
* float
* --str-- unicode
* bool
* dict
* tuple
* list
* ?module
* ?object
* datetime.time
* datetime.timedelta
* NotImplementedType

Base methods requirement
************************

* ``__getattr__``
* ``dict.get``
* ``__len__``

In datamodel, not implemented in any type, untested
***************************************************

* a[b]

* a + b, a - b, a * b, ...

* +a, ~a
