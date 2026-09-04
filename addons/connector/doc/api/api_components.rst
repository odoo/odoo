.. _api-component:

##########
Components
##########

Components are the blocks allowing to build a flexible and
well decoupled code. They are based on the ``component`` addon, which
can as well be used separately.


***************
Core Components
***************

.. automodule:: connector.components.core
   :members:
   :undoc-members:
   :exclude-members: _module
   :show-inheritance:
   :private-members:


********************
Connector Components
********************

.. automodule:: connector.components.binder
   :members:
   :undoc-members:
   :exclude-members: _module
   :show-inheritance:
   :private-members:

.. automodule:: connector.components.mapper
   :members:
   :member-order: groupwise
   :exclude-members: MappingDefinition, Mapper, ImportMapper, ExportMapper, MapChild, ImportMapChild, ExportMapChild
   :show-inheritance:

   .. autoclass:: Mapper
      :members:
      :show-inheritance:

      .. autoattribute:: _name
      .. autoattribute:: _inherit
      .. autoattribute:: _usage

   .. autoclass:: ImportMapper
      :members:
      :show-inheritance:

      .. autoattribute:: _name
      .. autoattribute:: _inherit
      .. autoattribute:: _usage

   .. autoclass:: ExportMapper
      :members:
      :show-inheritance:

      .. autoattribute:: _name
      .. autoattribute:: _inherit
      .. autoattribute:: _usage

   .. autoclass:: MapChild
      :members:
      :show-inheritance:

      .. autoattribute:: _name
      .. autoattribute:: _inherit
      .. autoattribute:: _usage

   .. autoclass:: ImportMapChild
      :members:
      :show-inheritance:

      .. autoattribute:: _name
      .. autoattribute:: _inherit
      .. autoattribute:: _usage

   .. autoclass:: ExportMapChild
      :members:
      :show-inheritance:

      .. autoattribute:: _name
      .. autoattribute:: _inherit
      .. autoattribute:: _usage


.. automodule:: connector.components.backend_adapter
   :members:
   :show-inheritance:
   :exclude-members: BackendAdapter, CRUDAdapter

   .. autoclass:: BackendAdapter
      :members:
      :show-inheritance:

      .. autoattribute:: _name
      .. autoattribute:: _inherit
      .. autoattribute:: _usage

   .. autoclass:: CRUDAdapter
      :members:
      :show-inheritance:

      .. autoattribute:: _name
      .. autoattribute:: _inherit
      .. autoattribute:: _usage

.. automodule:: connector.components.synchronizer
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: _module
   :private-members:

.. automodule:: connector.components.listener
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: _module
   :private-members:

.. automodule:: connector.components.locker
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: _module
   :private-members:

***************************
Components Collection Model
***************************

.. automodule:: odoo.addons.component.models.collection
   :members:
   :undoc-members:
   :show-inheritance:


*********************
Components Exceptions
*********************

.. automodule:: odoo.addons.component.exception
   :members:
   :undoc-members:
   :show-inheritance:

********************
Components Internals
********************

Low-level APIs of the Components.

.. automodule:: odoo.addons.component.core
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: odoo.addons.component.builder
   :members:
   :undoc-members:
   :show-inheritance:
