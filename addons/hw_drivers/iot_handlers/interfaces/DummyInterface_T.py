
from odoo.addons.hw_drivers.interface import Interface

class DummyInterface(Interface):
    """
    Dummy interface for testing purposes.
    This interface does not perform any actual operations and is used for testing the framework.
    """
    _loop_delay = 3
    connection_type = 'dummy'

    def get_devices(self):
        """
        Returns a dummy device for testing purposes.
        """
        return {
            'dummy_device': {
                'identifier': 'dummy_device',
                'name': 'Dummy Device',
            }
        }
