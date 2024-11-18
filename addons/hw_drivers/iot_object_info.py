
import logging
from threading import Thread

_logger = logging.getLogger(__name__)


class IoTObjectInfo:
    """Abstract class for getting information about an arbitrary IoT object."""

    def get_iot_info(self) -> dict:
        """Get information about the object contained in a dictionary.
        This method should NOT be overridden by subclasses."""
        all_iot_info = self._set_iot_info()
        # To avoid having to super().get_iot_info().update() in subclasses
        # we use this for loop which will update a dict with the info of all child classes defined dict
        for cls in self.__class__.__mro__:
            if cls == IoTObjectInfo:
                break
            if hasattr(cls, '_set_iot_info'):
                all_iot_info.update(cls._set_iot_info(self))
        return all_iot_info

    def _set_iot_info(self) -> dict:
        """Define the dict info for the current object
        This method should be overridden by subclasses."""
        return {}

    def _get_thread_info(self, thread: Thread = 'self') -> dict:
        """Create a dictionary with information about a thread.
        If no information is provided, assume the current object inherit from Thread."""
        if not thread:
            return '(unintialized thread)'
        if thread == 'self':
            thread = self
        return {
            'name': thread.name,
            'ident': thread.ident,
            'is_alive': thread.is_alive(),
            'is_daemon': thread.daemon,
        }
