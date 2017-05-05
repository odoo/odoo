Backend
=======

A backend for a version (for instance Magento 1.7), is represented
by an instance of the :py:class:`~connector.backend.Backend` class.

Each connector will also create a ``connector.backend`` which allows the users
to register their backends. For instance, the Magento connector has
``magento.backend`` (``_inherit``
:py:class:`connector.backend_model.connector_backend`).  This model contains a
``version`` field which should have the same list of versions (with the exact
same name) than the instances of :py:class:`~connector.backend.Backend`.

Example with the Magento Connector::

    # in magentoerpconnect/backend.py

    magento = backend.Backend('magento')
    """ Generic Magento Backend """

    magento1700 = backend.Backend(parent=magento, version='1.7')
    """ Magento Backend for version 1.7 """

    # in magentoerpconnect/magento_model.py

    class MagentoBackend(models.Model):
        _name = 'magento.backend'
        _description = 'Magento Backend'
        _inherit = 'connector.backend'

        _backend_type = 'magento'

        @api.model
        def _select_versions(self):
            """ Available versions

            Can be inherited to add custom versions.
            """
            return [('1.7', 'Magento 1.7')]

        # <snip>

        version = fields.Selection(
            selection='_select_versions',
            string='Version',
            required=True,
        )
        location = fields.Char(string='Location', required=True)
        username = fields.Char(string='Username')
        password = fields.Char(string='Password')

        # <snip>

In the code above, '1.7' is the matching key between the
:py:class:`~connector.backend.Backend` instance (``magento1700``) and the
``magento_backend`` record.

.. automodule:: connector.backend
   :members:
   :undoc-members:
   :show-inheritance:

Backend Models
==============

.. automodule:: connector.backend_model
   :members:
   :undoc-members:
   :show-inheritance:
