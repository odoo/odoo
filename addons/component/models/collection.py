# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""

Collection Model
================

This is the base Model shared by all the Collections.
In the context of the Connector, a collection is the Backend.
The `_name` given to the Collection Model will be the name
to use in the `_collection` of the Components usable for the Backend.

"""

from contextlib import contextmanager

from odoo import models

from ..core import WorkContext


class Collection(models.AbstractModel):
    """The model on which components are subscribed

    It would be for instance the ``backend`` for the connectors.

    Example::

        class MagentoBackend(models.Model):
            _name = 'magento.backend'  # name of the collection
            _inherit = 'collection.base'


        class MagentoSaleImporter(Component):
            _name = 'magento.sale.importer'
            _apply_on = 'magento.sale.order'
            _collection = 'magento.backend'  # name of the collection

            def run(self, magento_id):
                mapper = self.component(usage='import.mapper')
                extra_mappers = self.many_components(
                    usage='import.mapper.extra',
                )
                # ...

    Use it::

        >>> backend = self.env['magento.backend'].browse(1)
        >>> with backend.work_on('magento.sale.order') as work:
        ...     importer = work.component(usage='magento.sale.importer')
        ...     importer.run(1)

    See also: :class:`odoo.addons.component.core.WorkContext`


    """

    _name = "collection.base"
    _description = "Base Abstract Collection"

    @contextmanager
    def work_on(self, model_name, **kwargs):
        """Entry-point for the components, context manager

        Start a work using the components on the model.
        Any keyword argument will be assigned to the work context.
        See documentation of :class:`odoo.addons.component.core.WorkContext`.

        It is a context manager, so you can attach objects and clean them
        at the end of the work session, such as::

            @contextmanager
            def work_on(self, model_name, **kwargs):
                self.ensure_one()
                magento_location = MagentoLocation(
                    self.location,
                    self.username,
                    self.password,
                )
                # We create a Magento Client API here, so we can create the
                # client once (lazily on the first use) and propagate it
                # through all the sync session, instead of recreating a client
                # in each backend adapter usage.
                with MagentoAPI(magento_location) as magento_api:
                    _super = super(MagentoBackend, self)
                    # from the components we'll be able to do:
                    # self.work.magento_api
                    with _super.work_on(
                            model_name, magento_api=magento_api, **kwargs
                            ) as work:
                        yield work

        """
        self.ensure_one()
        # Allow propagation of custom component registry via context
        # TODO: maybe to be moved to `WorkContext.__init__`
        components_registry = self.env.context.get("components_registry")
        if components_registry:
            kwargs["components_registry"] = components_registry
        yield WorkContext(model_name=model_name, collection=self, **kwargs)
