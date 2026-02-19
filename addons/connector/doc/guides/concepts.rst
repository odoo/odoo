.. _concepts:

##################
Connector Concepts
##################

The framework to develop connectors is decoupled in small pieces of
codes interacting together. Each of them can be used or not in an
implementation.

An example of implementation is the `Odoo Magento Connector`_.

This document describes them from a high-level point of view and gives
pointers to more concrete 'how-to' or small tutorials.

.. _`Odoo Magento Connector`: http://www.odoo-magento-connector.com

******
Events
******

Reference: :ref:`api-event`

Events are hooks in Odoo on which we can plug some actions. They are
based on an Observer pattern.

The same event can be shared across several connectors, easing their
implementation.
For instance, the module connector_ecommerce_ which extends the
framework with common e-commerce capabilities, adds its own events
common to e-commerce.

A connectors developer is mostly interested by:

* adding and listening to events (see :ref:`api-event`)

.. _jobs-queue:

**********
Jobs Queue
**********

Reference: :ref:`api-queue`

This feature is part of a standalone addon, but is a prerequisite for
the connector framework.

The module is ``queue_job`` in https://github.com/OCA/queue.

A connectors developer is mostly interested by:

* Delay a job (see the decorator :py:func:`~odoo.addons.queue_job.job.job`)


*******
Backend
*******

Reference: :ref:`api-backend-model`

The Backend Model is what represents the external service / system we
synchronize with. The name on the backend indicates what is the collection the
Components will be registered into. Put another way: every backend has its own
collection of Components.

It must use an ``_inherit`` on ``connector.backend``.

``connector.backend`` inherits
:class:`odoo.addons.component.models.collection.Collection` which has a
:meth:`odoo.addons.component.models.collection.Collection.work_on` that will be
used as entrypoint for the component system.  This method returns a
:class:`~odoo.addons.component.core.WorkContext`

***********
WorkContext
***********

Reference: :class:`~odoo.addons.component.core.WorkContext`

A :class:`~odoo.addons.component.core.WorkContext` is the work environment or
context that will be passed transversally through all the components. This is
also the entrypoint to the component system.

A connectors developer is mostly interested by:

* Get a Component from a WorkContext (:py:meth:`~odoo.addons.component.core.WorkContext.component`)

*********
Component
*********

Reference: :ref:`api-component`

:py:class:`~odoo.addons.component.core.Component` are pluggable classes used
for the synchronizations with the external systems (or anything!)

The Components system has been extracted in a standalone addon (``component``),
which means it can really be used in a totally different way.

The connector defines some base components, which you can find below.  Note
that you can and are encouraged to define your own Components as well.

Mappings
========

The base class is :py:class:`connector.components.mapper.Mapper`.

In your components, you probably want to inherit from:

* ``_inherit = 'base.import.mapper'``
* ``_inherit = 'base.export.mapper'``

And the usages for the lookups are:

* ``import.mapper``
* ``export.mapper``

A mapping translates an external record to an Odoo record and
conversely.

It supports:

direct mappings
    Fields *a* is written in field *b*.

method mappings
    A method is used to convert one or many fields to one or many
    fields, with transformation.
    It can be filtered, for example only applied when the record is
    created or when the source fields are modified.

submapping
    a sub-record (lines of a sale order) is converted using another
    Mapper

See the documentation of the class for more details.

Synchronizers
=============

The base class is :py:class:`connector.components.synchronizer.Synchronizer`.

In your components, you probably want to inherit from:

* ``_inherit = 'base.importer'``
* ``_inherit = 'base.exporter'``

And the usages for the lookups are:

* ``importer``
* ``exporter``

However, in your implementation, it is advised to use more refined usages such
as:

* ``record.importer``
* ``record.exporter``
* ``batch.importer``
* ``batch.exporter``
* ..

A synchronizer orchestrates a synchronization with a backend.  It can be a
record's import or export, a deletion of something, or anything else.  For
instance, it will use the mappings to convert the data between both systems,
the backend adapters to read or write data on the backend and the binders to
create the link between them.

Backend Adapters
================

The base class is
:py:class:`connector.components.backend_adapter.BackendAdapter`.

In your components, you probably want to inherit from:

* ``_inherit = 'base.backend.adapter'``
* ``_inherit = 'base.backend.adapter.crud'``

And the usages for the lookups are:

* ``backend.adapter``

An external adapter has a common interface to speak with the backend.
It translates the basic orders (search, read, write) to the protocol
used by the backend.

Binders
=======

The base class is
:py:class:`connector.components.binder.Binder`.

In your components, you probably want to inherit from:

* ``_inherit = 'base.binder'``

And the usages for the lookups are:

* ``binder``

Binders are components that know how to find the external ID for an
Odoo ID, how to find the Odoo ID for an external ID and how to
create the binding between them. A default implementation is
available and can be inherited if needed.

Listeners
=========

The base class is
:py:class:`connector.components.listener.ConnectorListener`.

In your components, you probably want to inherit from:

* ``_inherit = 'base.connector.listener'``

This is where you will register your event listeners.
See :mod:`addons.component_event.components.event`.


.. _binding:

********
Bindings
********

Reference: :ref:`api-binding-model`

A binding represents the link of a record between Odoo and a backend.

The proposed implementation for the connectors widely use the
`_inherits` capabilities.

Say we import a customer from *Magento*.

We create a `magento.res.partner` model, which `_inherits`
`res.partner`.

This model, called a *binding* model, knows the ID of the partner in
Odoo, the ID in Magento and the relation to the backend model.

It also stores all the necessary metadata related to this customer
coming from Magento.
