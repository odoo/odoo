As a developer, you have access to a component system. You can find the
documentation in the code or on http://odoo-connector.com

In a nutshell, you can create components::


  from odoo.addons.component.core import Component

  class MagentoPartnerAdapter(Component):
      _name = 'magento.partner.adapter'
      _inherit = 'magento.adapter'

      _usage = 'backend.adapter'
      _collection = 'magento.backend'
      _apply_on = ['res.partner']

And later, find the component you need at runtime (dynamic dispatch at
component level)::

  def run(self, external_id):
      backend_adapter = self.component(usage='backend.adapter')
      external_data = backend_adapter.read(external_id)


In order for tests using components to work, you will need to use the base
class provided by `odoo.addons.component.tests.common`:

* `TransactionComponentCase`

There are also some specific base classes for testing the component registry,
using the ComponentRegistryCase as a base class. See the docstrings in
`tests/common.py`.
