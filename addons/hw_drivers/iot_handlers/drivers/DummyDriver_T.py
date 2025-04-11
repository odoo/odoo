
from odoo.addons.hw_drivers.driver import Driver

class DummyDriver(Driver):
    """
    Dummy driver for testing purposes.
    This driver does not perform any actual operations and is used for testing the framework.
    """
    connection_type = 'dummy'

    def __init__(self, identifier, device):
        super().__init__(identifier, device)
        self.device_type = 'dummy'
        self.device_name = device['name']
        self.owner = False
        self._actions.update({
            'dummy_action': self._action_dummy,
        })

    @classmethod
    def supported(cls, device):
        return True  # All devices with connection_type == 'dummy' are supported

    # def run(self):
    #     while not self._stopped.is_set():
    #         print("Dummy driver running...")
    #         pass  # Simulate a long-running process

    def _action_dummy(self, *args, **kwargs):
        """
        Dummy action for testing purposes.
        This action does not perform any actual operations and is used for testing the framework.
        """
        return {
            'status': 'success',
            'message': 'Dummy action executed successfully'
        }
