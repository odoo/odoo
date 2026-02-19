.. _migration-guide:

########################################
Migration Guide to the new Connector API
########################################

During the year 2017, the connector evolved greatly.
We can recognize three different aspect of the framework, they all have been
rewritten:

* The Job Queue API (:ref:`api-queue`)
* The Event API (:ref:`api-event`)
* The ``ConnectorUnit`` API, which is the core of the composability
  of the Connector. It has been replaced by a standalone addon
  called ``component``. (:ref:`api-component`)

The Connector has been splitted in different addons:

* ``queue_job`` in https://github.com/OCA/queue
* ``component`` in the same repository
* ``component_event`` in the same repository
* ``connector`` uses the 3 addons and the parts specifics to the connectors

This guide will show how to migrate from the old API to the new one.

The previous API will stay until the migration to Odoo 11.0.

.. contents:: Sections:
   :local:
   :backlinks: top
   :depth: 2

**************
Migrating Jobs
**************

Jobs are now more integrated within the Odoo API. They are no longer
standalone functions but are applied on methods of Models.  Another change is
that they have been extracted into their own addon, so obviously the Python
paths change.

Declaration of a job
====================

Before
------

.. code-block:: python

    from odoo.addons.connector.queue.job import job, related_action
    from ..related_action import unwrap_binding, link

    # function at module-level
    @job(default_channel='root.magento')
    @related_action(action=link)
    def import_record(session, model_name, backend_id, magento_id, force=False):
        """ Import a record from Magento """
        # ...

    @job(default_channel='root.magento')
    @related_action(action=unwrap_binding)
    def export_record(session, model_name, binding_id, fields=None):
        """ Import a record from Magento """
        # ...


After
-----

.. code-block:: python

    from odoo.addons.queue_job.job import job, related_action
    from odoo import api, models


    class MagentoBinding(models.AbstractModel):
        _name = 'magento.binding'
        _inherit = 'external.binding'
        _description = 'Magento Binding (abstract)'

        @job(default_channel='root.magento')
        @related_action(action='related_action_magento_link')
        @api.model
        def import_record(self, backend, external_id, force=False):
            """ Import a Magento record """
            backend.ensure_one()
            # ...

        @job(default_channel='root.magento')
        @related_action(action='related_action_unwrap_binding')
        @api.multi
        def export_record(self, fields=None):
            """ Export a record on Magento """
            self.ensure_one()
            # ...


Observations
------------

* The job is declared on the generic abstract binding model from which all
  bindings inherit. This is not a requirement, but for this kind of job it is
  the perfect fit.
* ``session``, ``model_name`` and ``binding_id`` are no longer required as they
  are already known in ``self``.  Jobs can be used as well on ``@api.multi`` and
  ``@api.model``.
* Passing arguments as records is supported, in the new version of
  ``import_record``, no need to browse on the backend if a record was passed
* The action of a related action is now the name of a method on the
  ``queue.job`` model.
* If you need to share a job between several models, put them in an
  AbstractModel and add an ``_inherit`` on the models.

Links
-----

* :meth:`odoo.addons.queue_job.job.job`
* :meth:`odoo.addons.queue_job.job.related_action`


Invocation of a job
===================

Before
------

.. code-block:: python

    from odoo.addons.connector.session import ConnectorSession
    from .unit.export_synchronizer import export_record


    class MyBinding(models.Model):
        _name = 'my.binding'
        _inherit = 'magento.binding'

        @api.multi
        def button_trigger_export_sync(self):
            session = ConnectorSession.from_env(self.env)
            export_record(session, binding._name, self.id, fields=['name'])

        @api.multi
        def button_trigger_export_async(self):
            session = ConnectorSession.from_env(self.env)
            export_record.delay(session, self._name, self.id,
                                fields=['name'], priority=12)


After
-----

.. code-block:: python

    class MyBinding(models.Model):
        _name = 'my.binding'

        @api.multi
        def button_trigger_export_sync(self):
            self.export_record(fields=['name'])

        @api.multi
        def button_trigger_export_async(self):
            self.with_delay(priority=12).export_record(fields=['name'])

Observations
------------

* No more imports are needed for the invocation
* ``ConnectorSession`` is now dead
* Arguments for the job (such as ``priority``) are no longer mixed with the
  arguments passed to the method
* When the job is called on a "browse" record, the job will be executed
  on an instance of this record:

  .. code-block:: python

      >>> binding = self.env['my.binding'].browse(1)
      >>> binding.button_trigger_export_async()

  In the execution of the job:

  .. code-block:: python

      @job
      def export_record(self, fields=None):
          print self
          print fields
      # =>
      # my.binding,1
      # ['name']

Links
-----

* :meth:`odoo.addons.queue_job.job.job`
* :meth:`odoo.addons.queue_job.models.base.Base.with_delay`

****************
Migrating Events
****************

Events are now handled by the ``component_event`` addon.

Triggering an event
===================

Before
------

First you had to create an :class:`~odoo.addons.connector.event.Event` instance:

.. code-block:: python

    on_record_create = Event()

And then import and trigger it, passing a lot of arguments to it:

.. code-block:: python

    from odoo.addons.connector.event import on_record_create

    class Base(models.AbstractModel):
        """ The base model, which is implicitly inherited by all models. """
        _inherit = 'base'

        @api.model
        def create(self, vals):
            record = super(Base, self).create(vals)
            on_record_create.fire(self.env, self._name, record.id, vals)
            return record


After
-----

.. code-block:: python

    class Base(models.AbstractModel):
        _inherit = 'base'

        @api.model
        def create(self, vals):
            record = super(Base, self).create(vals)
            self._event('on_record_create').notify(record, fields=vals.keys())
            return record

Observations
------------

* No more imports are needed for the invocation
  Only the arguments you want to pass should be passed to
  :meth:`odoo.addons.component_event.components.event.CollectedEvents.notify`.
* The name of the event must start with ``'on_'``

Links
-----

* :mod:`odoo.addons.component_event.components.event`


Listening to an event
=====================

Before
------

.. code-block:: python

    from odoo.addons.connector.event import on_record_create

    @on_record_create
    def delay_export(env, model_name, record_id, vals):
        if session.context.get('connector_no_export'):
            return
        fields = vals.keys()
        export_record.delay(session, model_name, record_id, fields=fields)

    @on_something
    def do_anything(env, model_name, record_id):
      # ...

After
-----

.. code-block:: python

    from odoo.addons.component.core import Component
    from odoo.addons.component_event import skip_if

    class MagentoListener(Component):
        _name = 'magento.event.listener'
        _inherit = 'base.connector.listener'

        @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
        def on_record_create(self, record, fields=None):
            """ Called when a record is created """
            record.with_delay().export_record(fields=fields)

        def on_something(self, record):
            # ...

Observations
------------

* The listeners are now components
* The name of the method is the same than the one notified in the previous
  section
* A listener Component might container several listener methods
* It must inherit from ``'base.event.listener'``, or one of its descendants.
* The check of the key ``connector_no_export`` in the context can
  be replaced by the decorator :func:`odoo.addons.component_event.skip_if`

Links
-----

* :mod:`odoo.addons.component_event.components.event`


Listening to an event only for some Models
==========================================

Before
------

.. code-block:: python

    from odoo.addons.connector.event import on_record_create

    @on_record_create(model_names=['magento.address', 'magento.res.partner'])
    def delay_export(env, model_name, record_id, vals):
        if session.context.get('connector_no_export'):
            return
        fields = vals.keys()
        export_record.delay(session, model_name, record_id, fields=fields)

After
-----

.. code-block:: python

    from odoo.addons.component.core import Component
    from odoo.addons.component_event import skip_if

    class MagentoListener(Component):
        _name = 'magento.event.listener'
        _inherit = 'base.event.listener'
        _apply_on = ['magento.address', 'magento.res.partner']

        @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
        def on_record_create(self, record, fields=None):
            """ Called when a record is created """
            record.with_delay().export_record(fields=fields)

Observations
------------

* Same than previous example but we added ``_apply_on`` on the Component.

Links
-----

* :mod:`odoo.addons.component_event.components.event`


********************
Migrating Components
********************

Backends
========

Before
------

You could have several versions for a backend:

.. code-block:: python

    magento = backend.Backend('magento')
    """ Generic Magento Backend """

    magento1700 = backend.Backend(parent=magento, version='1.7')
    """ Magento Backend for version 1.7 """

    magento1900 = backend.Backend(parent=magento, version='1.9')
    """ Magento Backend for version 1.9 """



It was linked with a Backend model such as:

.. code-block:: python

    class MagentoBackend(models.Model):
        _name = 'magento.backend'
        _description = 'Magento Backend'
        _inherit = 'connector.backend'

        _backend_type = 'magento'

        @api.model
        def select_versions(self):
            """ Available versions in the backend.
            Can be inherited to add custom versions.  Using this method
            to add a version from an ``_inherit`` does not constrain
            to redefine the ``version`` field in the ``_inherit`` model.
            """
            return [('1.7', '1.7+')]

        version = fields.Selection(selection='select_versions', required=True)



After
-----

All the :class:`backend.Backend` instances must be deleted.

And the ``_backend_type`` must be removed from the Backend model.

.. code-block:: python

    class MagentoBackend(models.Model):
        _name = 'magento.backend'
        _description = 'Magento Backend'
        _inherit = 'connector.backend'

        @api.model
        def select_versions(self):
            """ Available versions in the backend.
            Can be inherited to add custom versions.  Using this method
            to add a version from an ``_inherit`` does not constrain
            to redefine the ``version`` field in the ``_inherit`` model.
            """
            return [('1.7', '1.7+')]

        version = fields.Selection(selection='select_versions', required=True)


Observations
------------

* The version is now optional in the Backend Models.
* Backend Models are based on Component's Collections:
  :class:`odoo.addons.component.models.collection.Collection`

Links
-----

* :ref:`api-component`
* :class:`odoo.addons.component.models.collection.Collection`


Inheritance
===========

Before
------

You could inherit a ``ConnectorUnit`` by creating a custom Backend
version and decorating your class with it

.. code-block:: python

    magento_custom = backend.Backend(parent=magento1700, version='custom')
    """ Custom Magento Backend """


.. code-block:: python

    # base one
    @magento
    class MagentoPartnerAdapter(GenericAdapter):
        # ...

    # other file...

    from .backend import magento_custom

    # custom one
    @magento_custom
    class MyPartnerAdapter(MagentoPartnerAdapter):
        # ...

        def do_something(self):
            # do it this way

You could also replace an existing class, this is mentionned in `Replace or
unregister a component`_.


After
-----

For an existing component:

.. code-block:: python

    from odoo.addons.component.core import Component

    class MagentoPartnerAdapter(Component):
        _name = 'magento.partner.adapter'
        _inherit = 'magento.adapter'

        def do_something(self):
            # do it this way

You can extend it:

.. code-block:: python

    from odoo.addons.component.core import Component

    class MyPartnerAdapter(Component):
        _inherit = 'magento.partner.adapter'

        def do_something(self):
            # do it this way

Or create a new different component with the existing one as base:

.. code-block:: python

    from odoo.addons.component.core import Component

    class MyPartnerAdapter(Component):
        _name = 'my.magento.partner.adapter'
        _inherit = 'magento.partner.adapter'

        def do_something(self):
            # do it this way


Observations
------------

* The inheritance is similar to the Odoo's one (without ``_inherits``.
* All components have a Python inheritance on
  :class:`~odoo.addons.component.core.AbstractComponent` or
  :class:`~odoo.addons.component.core.Component`
* The names are global (as in Odoo), so you should prefix them with a namespace
* The name of the classes has no effect
* As in Odoo Models, a Component can ``_inherit`` from a list of Components
* All components implicitly inherits from a ``'base'`` component

Links
-----

* :ref:`api-component`
* :class:`odoo.addons.component.core.AbstractComponent`



Entrypoint for working with components
======================================

Before
------

Previously, when you had to work with ``ConnectorUnit`` from a Model or from a job,
depending of the Odoo version you to:

.. code-block:: python

    from odoo.addons.connector.connector import ConnectorEnvironment

    # ...

        backend_record = session.env['magento.backend'].browse(backend_id)
        env = ConnectorEnvironment(backend_record, 'magento.res.partner')
        importer = env.get_connector_unit(MagentoImporter)
        importer.run(magento_id, force=force)

Or:

.. code-block:: python

    from odoo.addons.connector.connector import ConnectorEnvironment
    from odoo.addons.connector.session import ConnectorSession

    #...

        backend_record = session.env['magento.backend'].browse(backend_id)
        session = ConnectorSession.from_env(self.env)
        env = ConnectorEnvironment(backend_record, session, 'magento.res.partner')
        importer = env.get_connector_unit(MagentoImporter)
        importer.run(external_id, force=force)

Which was commonly abstracted in a helper function such as:


.. code-block:: python

    def get_environment(session, model_name, backend_id):
        """ Create an environment to work with.  """
        backend_record = session.env['magento.backend'].browse(backend_id)
        env = ConnectorEnvironment(backend_record, session, 'magento.res.partner')
        lang = backend_record.default_lang_id
        lang_code = lang.code if lang else 'en_US'
        if lang_code == session.context.get('lang'):
            return env
        else:
            with env.session.change_context(lang=lang_code):
                return env

After
-----

.. code-block:: python

    # ...
        backend_record = self.env['magento.backend'].browse(backend_id)
        with backend_record.work_on('magento.res.partner') as work:
            importer = work.component(usage='record.importer')
            importer.run(external_id, force=force)

Observations
------------

* And when you are already in a Component, refer to `Find a component`_

Links
-----

* :class:`~odoo.addons.component.core.WorkContext`


Find a component
================

Before
------

To find a ``ConnectorUnit``, you had to ask for given class or subclass:

.. code-block:: python

    # our ConnectorUnit to find
    @magento
    class MagentoPartnerAdapter(GenericAdapter):
        _model_name = ['magent.res.partner']

    # other file...

    def run(self, record):
        backend_adapter = self.unit_for(GenericAdapter)

It was searched for the current model and the current backend.

After
-----

For an existing component:

.. code-block:: python

    from odoo.addons.component.core import Component

    class MagentoPartnerAdapter(Component):
        _name = 'magento.partner.adapter'
        _inherit = 'magento.adapter'

        _usage = 'backend.adapter'
        _collection = 'magento.backend'
        _apply_on = ['res.partner']

    # other file...

    def run(self, record):
        backend_adapter = self.component(usage='backend.adapter')



Observations
------------

* The model is compared with the ``_apply_on`` attribute
* The Backend is compared with the ``_collection`` attribute, it must
  have the same name than the Backend Model.
* The ``_usage`` indicates what the purpose of the component is, and
  allow to find the correct one for our task. It allow more dynamic
  usages than the previous usage of a class.
* Usually, the ``_usage`` and the ``_collection`` will be ``_inherit`` 'ed from
  a component (here from ``'magento.adapter``), so they won't need to be
  repeated in all Components.
* A good idea is to have a base abstract Component for the Collection, then
  an abstract Component for every usage::

    class BaseMagentoConnectorComponent(AbstractComponent):

        _name = 'base.magento.connector'
        _inherit = 'base.connector'
        _collection = 'magento.backend'

    class MagentoBaseExporter(AbstractComponent):
        """ Base exporter for Magento """

        _name = 'magento.base.exporter'
        _inherit = ['base.exporter', 'base.magento.connector']
        _usage = 'record.exporter'

    class MagentoImportMapper(AbstractComponent):
        _name = 'magento.import.mapper'
        _inherit = ['base.magento.connector', 'base.import.mapper']
        _usage = 'import.mapper'

    # ...

* The main usages are:
  * import.mapper
  * export.mapper
  * backend.adapter
  * importer
  * exporter
  * binder
  * event.listener
* But for the importer and exporter, I recommend to use more precise ones in
  the connectors: record.importer, record.exporter, batch.importer,
  batch.exporter
* You are allowed to be creative with the ``_usage``, it's the key that will
  allow you to find the right one component you need. (e.g. on
  ``stock.picking`` you need to 1. export the record, 2. export the tracking.
  Then use ``record.exporter`` and ``tracking.exporter``).
* AbstractComponent will never be returned by a lookup


Links
-----

* :ref:`api-component`
* :class:`odoo.addons.component.core.AbstractComponent`


Backend Versions
================

Before
------

You could have several versions for a backend:

.. code-block:: python

    magento = backend.Backend('magento')
    """ Generic Magento Backend """

    magento1700 = backend.Backend(parent=magento, version='1.7')
    """ Magento Backend for version 1.7 """

    magento1900 = backend.Backend(parent=magento, version='1.9')
    """ Magento Backend for version 1.9 """


And use them for a class-level dynamic dispatch

.. code-block:: python

    from odoo.addons.magentoerpconnect.backend import magento1700, magento1900

    @magento1700
    class PartnerAdapter1700(GenericAdapter):
        # ...

        def do_something(self):
            # do it this way

    @magento1900
    class PartnerAdapter1900(GenericAdapter):
        # ...

        def do_something(self):
            # do it that way


After
-----

This feature has been removed, it introduced a lot of complexity (notably
regarding inheritance) for few gain.  The version is now optional on the
backends and the version dispatch, if needed, should be handled manually.

In methods:

.. code-block:: python

    from odoo.addons.component.core import Component

    class PartnerAdapter(Component):
        # ...

        def do_something(self):
            if self.backend_record.version == '1.7':
                # do it this way
            else:
                # do it that way

Or with a factory:

.. code-block:: python

    from odoo.addons.component.core import Component

    class PartnerAdapterFactory(Component):
        # ...

        def get_component(self, version):
            if self.backend_record.version == '1.7':
                return self.component(usage='backend.adapter.1.7')
            else:
                return self.component(usage='backend.adapter.1.9')

Observations
------------

* None

Links
-----

* :ref:`api-component`


Replace or unregister a component
=================================

Before
------

You could replace a ``ConnectorUnit`` with the ``replace`` argument passed to
the backend decorator:

.. code-block:: python

    @magento(replacing=product.ProductImportMapper)
    class ProductImportMapper(product.ProductImportMapper):


After
-----

First point: this should hardly be needed now, as you can inherit a component
like Odoo Models.  Still, if you need to totally replace a component by
another, let's say there is this component:

.. code-block:: python

    from odoo.addons.component.core import Component

    class ProductImportMapper(Component):
        _name = 'magento.product.import.mapper'
        _inherit = 'magento.import.mapper'

        _apply_on = ['magento.product.product']
        # normally the following attrs are inherited from the _inherit
        _usage = 'import.mapper'
        _collection = 'magento.backend'


Then you can remove the usage of the component: it will never be used:

.. code-block:: python

    from odoo.addons.component.core import Component

    class ProductImportMapper(Component):
        _inherit = 'magento.product.import.mapper'
        _usage = None

And create your own, that will be picked up instead of the base one:

.. code-block:: python

    from odoo.addons.component.core import Component

    class MyProductImportMapper(Component):
        _name = 'my.magento.product.import.mapper'
        _inherit = 'magento.import.mapper'

        _apply_on = ['magento.product.product']
        # normally the following attrs are inherited from the _inherit
        _usage = 'import.mapper'
        _collection = 'magento.backend'


Observations
------------

* None

Links
-----

* :ref:`api-component`


Various hints
=============

* The components and the jobs know how to work with Model instances,
  so prefer them over ids in parameters.
