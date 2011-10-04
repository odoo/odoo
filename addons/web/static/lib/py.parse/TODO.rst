* Parser
	since parsing expressions, try with a pratt parser
	http://journal.stuffwithstuff.com/2011/03/19/pratt-parsers-expression-parsing-made-easy/
	http://effbot.org/zone/simple-top-down-parsing.htm

Evaluator
---------

* Stop busyworking trivial binary operator
* Make it *trivial* to build Python type-wrappers
* Implement Python's `data model
  protocols<http://docs.python.org/reference/datamodel.html#basic-customization>`_
  for *all* supported operations, optimizations can come later
* Automatically type-wrap everything (for now anyway)
