.. _code-overview:

#############
Code Overview
#############

Here is an overview of some of the concepts in the framework.

As an example, we'll see the steps for exporting an invoice to Magento.
The steps won't show all the steps, but a simplified excerpt of a real
use case exposing the main ideas.

********
Backends
********

All start with the declaration of the :py:class:`~connector.backend.Backend`::

  import openerp.addons.connector.backend as backend

  magento = backend.Backend('magento')
  """ Generic Magento Backend """

  magento1700 = backend.Backend(parent=magento, version='1.7')
  """ Magento Backend for version 1.7 """

As you see, Magento is the parent of Magento 1.7. We can define a
hierarchy of backends.

********
Bindings
********

The ``binding`` is the link between an Odoo record and an external
record. There is no forced implementation for the ``bindings``. The most
straightforward techniques are: storing the external ID in the same
model (``account.invoice``), in a new link model or in a new link model
which ``_inherits`` ``account.invoice``. Here we choose the latter
solution::

  class MagentoAccountInvoice(models.Model):
      _name = 'magento.account.invoice'
      _inherits = {'account.invoice': 'openerp_id'}
      _description = 'Magento Invoice'

      backend_id = fields.Many2one(comodel_name='magento.backend', string='Magento Backend', required=True, ondelete='restrict')
      openerp_id = fields.Many2one(comodel_name='account.invoice', string='Invoice', required=True, ondelete='cascade')
      magento_id = fields.Char(string='ID on Magento')  # fields.char because 0 is a valid Magento ID
      sync_date = fields.Datetime(string='Last synchronization date')
      magento_order_id = fields.Many2one(comodel_name='magento.sale.order', string='Magento Sale Order', ondelete='set null')
      # we can also store additional data related to the Magento Invoice

*******
Session
*******

The framework uses :py:class:`~connector.session.ConnectorSession`
objects to store the ``cr``, ``uid`` and ``context`` in a
:class:`openerp.api.Environment`.  So from a session, we can access to
the usual ``self.env`` (new API) or ``self.pool`` (old API).

******
Events
******

We can create :py:class:`~connector.event.Event` on which we'll be able
to subscribe consumers.  The connector already integrates the most
generic ones:
:py:meth:`~connector.event.on_record_create`,
:py:meth:`~connector.event.on_record_write`,
:py:meth:`~connector.event.on_record_unlink`

When we create a ``magento.account.invoice`` record, we want to delay a
job to export it to Magento, so we subscribe a new consumer on
:py:meth:`~connector.event.on_record_create`::

  @on_record_create(model_names='magento.account.invoice')
  def delay_export_account_invoice(session, model_name, record_id):
      """
      Delay the job to export the magento invoice.
      """
      export_invoice.delay(session, model_name, record_id)

On the last line, you can notice an ``export_invoice.delay``. We'll
discuss about that in Jobs_

****
Jobs
****

A :py:class:`~connector.queue.job.Job` is a task to execute later.
In that case: create the invoice on Magento.

Any function decorated with :py:meth:`~connector.queue.job.job` can
be posted in the queue of jobs using a ``delay()`` function
and will be run as soon as possible::

  @job
  def export_invoice(session, model_name, record_id):
      """ Export a validated or paid invoice. """
      invoice = session.env[model_name].browse(record_id)
      backend_id = invoice.backend_id.id
      env = get_environment(session, model_name, backend_id)
      invoice_exporter = env.get_connector_unit(MagentoInvoiceSynchronizer)
      return invoice_exporter.run(record_id)

There is a few things happening there:

* We find the backend on which we'll export the invoice.
* We build an :py:class:`~connector.connector.Environment` with the
  current :py:class:`~connector.session.ConnectorSession`,
  the model we work with and the target backend.
* We get the :py:class:`~connector.connector.ConnectorUnit` responsible
  for the work using
  :py:meth:`~connector.connector.Environment.get_connector_unit`
  (according the backend version and the model)  and we call ``run()``
  on it.


*************
ConnectorUnit
*************

These are all classes which are responsible for a specific work.
The main types of :py:class:`~connector.connector.ConnectorUnit` are
(the implementation of theses classes belongs to the connectors):

:py:class:`~connector.connector.Binder`

  The ``binders`` give the external ID or Odoo ID from respectively an
  Odoo ID or an external ID. A default implementation is available.

:py:class:`~connector.unit.mapper.Mapper`

  The ``mappers`` transform a external record into an Odoo record or
  conversely.

:py:class:`~connector.unit.backend_adapter.BackendAdapter`

  The ``adapters`` implements the discussion with the ``backend's``
  APIs. They usually adapt their APIs to a common interface (CRUD).

:py:class:`~connector.unit.synchronizer.Synchronizer`

    The ``synchronizers`` are the main piece of a synchronization.  They
    define the flow of a synchronization and use the other
    :py:class:`~connector.connector.ConnectorUnit` (the ones above or
    specific ones).

For the export of the invoice, we just need an ``adapter`` and a
``synchronizer`` (the real implementation is more complete)::

  @magento
  class AccountInvoiceAdapter(GenericAdapter):
      """ Backend Adapter for the Magento Invoice """
      _model_name = 'magento.account.invoice'
      _magento_model = 'sales_order_invoice'

      def create(self, order_increment_id, items, comment, email, include_comment):
          """ Create a record on the external system """
          return self._call('%s.create' % self._magento_model,
                            [order_increment_id, items, comment,
                            email, include_comment])
  @magento
  class MagentoInvoiceSynchronizer(Exporter):
      """ Export invoices to Magento """
      _model_name = ['magento.account.invoice']

      def _export_invoice(self, magento_id, lines_info, mail_notification):
          # use the ``backend adapter`` to create the invoice
          return self.backend_adapter.create(magento_id, lines_info,
                                            _("Invoice Created"),
                                            mail_notification, False)

      def _get_lines_info(self, invoice):
          [...]

      def run(self, binding_id):
          """ Run the job to export the validated/paid invoice """
          invoice = self.model.browse(binding_id)
          magento_order = invoice.magento_order_id
          magento_id = self._export_invoice(magento_order.magento_id, lines_info, True)
          # use the ``binder`` to write the external ID
          self.binder.bind(magento_id, binding_id)
