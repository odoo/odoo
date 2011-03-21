Contributing to OpenERP Web
===========================

* General organization and core ideas (design philosophies)
* Internal documentation, autodoc, Python and JS domains
* QWeb code documentation/description
* Documentation of the OpenERP APIs and choices taken based on that?
* Style guide and coding conventions (PEP8? More)
* Test frameworks in JS?

Testing
-------

Python
++++++

Testing for the OpenERP Web core is similar to :ref:`testing addons
<addons-testing>`: the tests live in ``openerpweb.tests``, unittest2_
is the testing framework and tests can be run via either unittest2
(``unit2 discover``) or via nose_ (``nosetests``).

Tests for the OpenERP Web core can also be run using ``setup.py
test``.


.. _unittest2:
    http://www.voidspace.org.uk/python/articles/unittest2.shtml

.. _nose:
    http://somethingaboutorange.com/mrl/projects/nose/1.0.0/
