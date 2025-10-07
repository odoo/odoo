As a developer, you have access to a events system. You can find the
documentation in the code or on http://odoo-connector.com

In a nutshell, you can create trigger events::

  class Base(models.AbstractModel):
      _inherit = 'base'

      @api.model
      def create(self, vals):
          record = super(Base, self).create(vals)
          self._event('on_record_create').notify(record, fields=vals.keys())
          return record

And subscribe listeners to the events::

  from odoo.addons.component.core import Component
  from odoo.addons.component_event import skip_if

  class MagentoListener(Component):
      _name = 'magento.event.listener'
      _inherit = 'base.connector.listener'

      @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
      def on_record_create(self, record, fields=None):
          """ Called when a record is created """
          record.with_delay().export_record(fields=fields)


This module triggers 3 events:

* ``on_record_create(record, fields=None)``
* ``on_record_write(record, fields=None)``
* ``on_record_unlink(record)``
