.. _code-overview:

#############
Code Overview
#############

Some simple code examples.

***************************
Trigger and listen an event
***************************

.. code-block:: python

  class AccountInvoice(models.Model):
      _inherit = 'account.invoice'

      @api.multi
      def action_invoice_paid(self):
          res = super(AccountInvoice, self).action_invoice_paid()
          for record in self:
              self._event('on_invoice_paid').notify(record)
          return res



.. code-block:: python

    from odoo.addons.component.core import Component


    class MyEventListener(Component):
        _name = 'my.event.listener'
        _inherit = 'base.event.listener'

        def on_invoice_paid(self, record):
            _logger.info('invoice %s has been paid!', record.name)

Ref: :ref:`api-event`


*************************
Delay an Asynchronous Job
*************************

.. code-block:: python

    from odoo.addons.queue_job.job import job


    class AccountInvoice(models.Model):
        _inherit = 'account.invoice'

        @job
        @api.multi
        def export_payment(self):
            self.ensure_one()
            _logger.info("I'm exporting the payment for %s", self.name)

        @api.multi
        def action_invoice_paid(self):
            res = super(AccountInvoice, self).action_invoice_paid()
            for record in self:
                record.with_delay(priority=5).export_payment()
            return res

Ref: :ref:`api-queue`

********************
Work with components
********************

This is a highly simplified version of a micro-connector, without using
events or jobs, for the sake of the example.

.. code-block:: python

    from odoo.addons.component.core import AbstractComponent


    class MagentoBackend(models.Model):
        _name = 'magento.backend'
        _description = 'Magento Backend'
        _inherit = 'connector.backend'

        location = fields.Char(string='Location', required=True)
        username = fields.Char(string='Username')
        password = fields.Char(string='Password')

        def import_partner(self, external_id):
            with self.work_on(model_name='magento.res.partner') as work:
                importer = work.component(usage='record.importer')
                # returns an instance of PartnerImporter, which has been
                # found with:the collection name (magento.backend, the model,
                # and the usage).
                importer.run(partner_id)

    # the next 2 components are abstract and are used by inheritance
    # by the others
    class BaseMagentoConnectorComponent(AbstractComponent):
        # same inheritance than Odoo models
        _name = 'base.magento.connector'
        _inherit = 'base.connector'
        # subscribe to:
        _collection = 'magento.backend'
        # the collection will be inherited to the components below,
        # because they inherit from this component


    class GenericAdapter(AbstractComponent):
        # same inheritance than Odoo models
        _name = 'magento.adapter'
        _inherit = ['base.backend.adapter', 'base.magento.connector']
        # usage is used for lookups of components
        _usage = 'backend.adapter'

        _magento_model = None

        def _call(self, *args, **kwargs):
            location = self.backend_record.location
            # use client API

        def read(self, fields=None):
            """ Search records according to some criterias
            and returns a list of ids

            :rtype: list
            """
            return self._call('%s.info' % self._magento_model, fields)


    # these are the components we need for our synchronization
    class PartnerAdapter(Component):
        _name = 'magento.partner.adapter'
        _inherit = 'magento.adapter'
        _apply_on = ['magento.res.partner']
        _magento_model = 'customer'


    class PartnerMapper(Component):
        _name = 'magento.partner.import.mapper'
        _inherit = 'magento.import.mapper'  # parent component omitted for brevity
        _apply_on = ['magento.res.partner']
        _usage = 'import.mapper'


    class PartnerBinder(Component):
        _name = 'magento.partner.binder'
        _inherit = 'magento.binder'  # parent component omitted for brevity
        _apply_on = ['magento.res.partner']
        _usage = 'binder'


    class PartnerImporter(Component):
        _name = 'magento.partner.importer'
        _inherit = 'magento.importer'  # parent component omitted for brevity
        _apply_on = ['magento.res.partner']
        _usage = 'record.importer'

        def run(self, external_id):
            # get the components we need for the sync

            # this one knows how to speak to magento
            backend_adapter = self.component(usage='backend.adapter')
            # this one knows how to convert magento data to odoo data
            mapper = self.component(usage='import.mapper')
            # this one knows how to link magento/odoo records
            binder = self.component(usage='binder')

            # read external data from magento
            external_data = backend_adapter.read(external_id)
            # convert to odoo data
            internal_data = mapper.map_record(external_data).values()
            # find if the magento id already exists in odoo
            binding = binder.to_internal(external_id)
            if binding:
                # if yes, we update it
                binding.write(internal_data)
            else:
                # or we create it
                binding = self.model.create(internal_data)
            # finally, we bind both, so the next time we import
            # the record, we'll update the same record instead of
            # creating a new one
            binder.bind(external_id, binding)


Ref: :ref:`api-component`
