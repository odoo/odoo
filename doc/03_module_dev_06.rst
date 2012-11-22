.. _module-dev-versioning:
.. _module_versioning:

=================
Module versioning
=================

OpenERP has been developed with modularity in mind: OpenERP should be flexible
enough so it can be adopted by any enterprise, of any size and in any market.
By using modules one can adapt OpenERP in many different ways: from completely
different business to smaller, company-specific changes.

As modules (and the core framework itself) evolve, it is necessary to identify
modules by their version so a sensible set of modules can be chosen for a
particular deployment.

There are two trends re-inforcing each others. Firstly OpenERP s.a. will work
on a smaller number of official modules and let the community handles more and
more development. Secondly all those modules will receive greater exposure on
`OpenERP Apps`_ where each module will be owned by a single author.

The solution advocated by OpenERP is straightforward and aims to avoid the
`dependency hell`_. In particular we don't want to deal with versioned
dependencies (i.e. a module depends on a specific version of another module).

For each stable release (e.g. OpenERP 6.1, or OpenERP 7.0) or, said in other
words, for each major version, there is only one (major) version of each
module. The minor version is bumped for bug fixes but is otherwise not
important here.

Making variations on some business needs must be done by creating new modules,
possibly depending on previously written modules. If depending on a module
proves too difficult, you can write a new module (not a new _version_). But
generally Python is flexible enough that depending on the existing module
should work.

For the next major version, refactoring modules can be done and similar
functionalities can be brought together in a better module.

.. _`OpenERP Apps`: http://apps.openerp.com/

.. _`dependency hell`: http://en.wikipedia.org/wiki/Dependency_hell

Example
=======

Whenever a new module is developed or must evolve, the above versioning policy
should be respected.

A particular concern one can face when deploying OpenERP to multiple customers
is now detailed as an example to provide a few guidelines. The hypotethical
situation is as follow. A partner needs to create a new module, called ``M``, for a
customer. Shortly after (but still within a typical OpenERP release cycle, so
there is no chance to bump the version number except for bug fixes), ``M`` must be
adapted for another customer.

The correct way to handle it is to leave ``M`` as it is and create a new module,
say called ``X``, that depends on ``M`` for the second customer. Both modules have the
same version (i.e. 6.1 or 7.0, targeting the corresponding OpenERP version).

If leaving ``M`` as it is is not possible (which should be very rare as Python
is incredibly flexible), the ``X`` module for the new customer can depend on a
new module ``N``, derived from ``M``. At this point, ``N`` is a new,
differently named module. It is not a ``M`` module with a increased version
number. Your goal should be to make ``N`` as close as possible to ``M``, so
that at the next version of OpenERP, the first customer can switch to ``N``
instead of ``M`` (or include the changes in a new version of ``M``). At that
point you are in the ideal situation: you have a module ``N`` for one customer,
and a module ``X`` depending on N to account for the differences between those
two customers.

