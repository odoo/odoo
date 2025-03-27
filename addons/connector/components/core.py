# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""

Base Component
==============

The connector proposes a 'base' Component, which can be used in
the ``_inherit`` of your own components.  This is not a
requirement.  It is already inherited by every component
provided by the Connector.

Components are organized according to different usages.  The connector suggests
5 main kinds of Components. Each might have a few different usages.  You can be
as creative as you want when it comes to creating new ones though.

One "usage" is responsible for a specific work, and alongside with the
collection (the backend) and the model, the usage will be used to find the
needed component for a task.

Some of the Components have an implementation in the ``Connector`` addon, but
some are empty shells that need to be implemented in the different connectors.

The usual categories are:

:py:class:`~connector.components.binder.Binder`
  The ``binders`` give the external ID or Odoo ID from respectively an
  Odoo ID or an external ID. A default implementation is available.

  Most common usages:

  * ``binder``

:py:class:`~connector.components.mapper.Mapper`
  The ``mappers`` transform a external record into an Odoo record or
  conversely.

  Most common usages:

  * ``import.mapper``
  * ``export.mapper``

:py:class:`~connector.components.backend_adapter.BackendAdapter`
  The ``backend.adapters`` implements the discussion with the ``backend's``
  APIs. They usually adapt their APIs to a common interface (CRUD).

  Most common usages:

  * ``backend.adapter``

:py:class:`~connector.components.synchronizer.Synchronizer`
  A ``synchronizer`` is the main piece of a synchronization.  It
  orchestrates the flow of a synchronization and use the other
  Components

  Most common usages:

  * ``record.importer``
  * ``record.exporter``
  * ``batch.importer``
  * ``batch.exporter``

The possibilities for components do not stop there, look at the
:class:`~connector.components.locker.RecordLocker` for an example of
single-purpose, decoupled component.


"""

from odoo.addons.component.core import AbstractComponent
from odoo.addons.queue_job.exception import RetryableJobError

from ..database import pg_try_advisory_lock


class BaseConnectorComponent(AbstractComponent):
    """Base component for the connector

    Is inherited by every components of the Connector (Binder, Mapper, ...)
    and adds a few methods which are of common usage in the connectors.

    """

    _name = "base.connector"

    @property
    def backend_record(self):
        """Backend record we are working with"""
        # backward compatibility
        return self.work.collection

    def binder_for(self, model=None):
        """Shortcut to get Binder for a model

        Equivalent to: ``self.component(usage='binder', model_name='xxx')``

        """
        return self.component(usage="binder", model_name=model)

    def advisory_lock_or_retry(self, lock, retry_seconds=1):
        """Acquire a Postgres transactional advisory lock or retry job

        When the lock cannot be acquired, it raises a
        :exc:`odoo.addons.queue_job.exception.RetryableJobError` so the job
        is retried after n ``retry_seconds``.

        Usage example:

        .. code-block:: python

            lock_name = 'import_record({}, {}, {}, {})'.format(
                self.backend_record._name,
                self.backend_record.id,
                self.model._name,
                self.external_id,
            )
            self.advisory_lock_or_retry(lock_name, retry_seconds=2)

        See :func:`odoo.addons.connector.connector.pg_try_advisory_lock` for
        details.

        :param lock: The lock name. Can be anything convertible to a
           string.  It needs to represent what should not be synchronized
           concurrently, usually the string will contain at least: the
           action, the backend name, the backend id, the model name, the
           external id
        :param retry_seconds: number of seconds after which a job should
           be retried when the lock cannot be acquired.
        """
        if not pg_try_advisory_lock(self.env, lock):
            raise RetryableJobError(
                "Could not acquire advisory lock",
                seconds=retry_seconds,
                ignore_retry=True,
            )
