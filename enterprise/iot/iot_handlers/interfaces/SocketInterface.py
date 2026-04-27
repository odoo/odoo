import logging
import socket

from odoo import _
from odoo.addons.hw_drivers.interface import Interface
from odoo.addons.hw_drivers.main import iot_devices

_logger = logging.getLogger(__name__)

# Because drivers don't get loaded as normal Python modules but directly in
# load_iot_handlers called by Manager.run, the log levels that get applied to the odoo
# import hierarchy won't apply here. This means DEBUG level messages will not display
# even if specified and INFO messages will show even if the log level is configured to
# be ERROR at the odoo-bin level. In order to work around this, it's possible to
# uncomment this line and set the desired level directly for this module.
# _logger.setLevel(logging.DEBUG)

socket_devices = {}


class SocketInterface(Interface):
    connection_type = 'socket'

    def __init__(self):
        super().__init__()
        self.open_socket(9000)

    def open_socket(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', port))
        self.sock.listen()

    @staticmethod
    def create_socket_device(dev, addr):
        """Creates a socket_devices entry that wraps the socket.
        The Interface thread will detect it being added and instantiate a corresponding
        Driver in iot_devices based on the results of the `supported` call.
        """
        _logger.debug("Creating new socket_device")
        socket_devices[addr] = type('', (), {'dev': dev})

    def replace_socket_device(self, dev, addr):
        """Replaces an existing socket_devices entry.
        The socket contained in the socket_devices entry is also used by the Driver
        thread defined in iot_devices that's reading and writing from it. The Driver
        thread can modify both socket_devices and iot_devices. The Interface thread can
        update iot_devices based on changes in socket_devices. In order to clean up
        the existing connection, it'll be necessary to actively close it at the TCP
        level, wait for the Driver thread to terminate in response to that, and for the
        Interface to do any iot_devices related cleanup in response.
        After this the new connection can replace the old one.
        """
        driver_thread = iot_devices.get(addr)

        # Actively close the existing connection and do not allow receiving further
        # data. This will result in a currently blocking recv call returning b'' and
        # subsequent recv calls raising an OSError about a bad file descriptor.
        old_dev = socket_devices[addr].dev
        _logger.debug("Closing socket: %s", old_dev)
        try:
            # If the socket was already closed, a bad file descriptor OSError will be
            # raised. This can happen if the IngenicoDriver thread initiated the
            # disconnect itself.
            old_dev.shutdown(socket.SHUT_RD)
        except OSError:
            pass
        old_dev.close()

        if driver_thread:
            _logger.debug("Waiting for driver thread to finish")
            driver_thread.join()
            _logger.debug("Driver thread finished")

        del socket_devices[addr]

        # Shutting down the socket will result in the corresponding IngenicoDriver
        # thread terminating and removing the corresponding entry in iot_devices. In the
        # Interface thread _detected_devices will still contain the old socket device.
        # This means update_iot_devices won't detect there was a change after
        # create_socket_device gets called since that would create a new entry with the
        # same key. A composite key of ip and port would avoid that, but this causes
        # problems since the key is also reported to the Odoo database, which means a
        # new device would show up in the IoT app for each key. _detected_devices is a
        # dict_keys, which means we can't directly modify it either. Hence this hack.
        _logger.debug("Updating _detected_devices")
        new_detected_devices = dict.fromkeys(self._detected_devices, 0)
        if addr in new_detected_devices:
            del new_detected_devices[addr]
            _logger.debug("Updated _detected_devices")
        else:
            _logger.warning("socket_device entry %s was not found in _detected_devices", addr)
        self._detected_devices = new_detected_devices

        SocketInterface.create_socket_device(dev, addr)

    def get_devices(self):
        try:
            dev, addr = self.sock.accept()
            _logger.debug("Accepted new socket connection: %s", addr)
            if not addr:
                _logger.warning("Socket accept returned no address")
                return socket_devices

            if addr[0] not in socket_devices:
                self.create_socket_device(dev, addr[0])
            else:
                # This can happen if the device power cycled or a network cable
                # was temporarily unplugged: if the device tries to connect again
                # we might still have the old connection open and it needs to be
                # cleaned up.
                self.replace_socket_device(dev, addr[0])
        except OSError:
            pass

        # update_iot_devices in Interface stores the keys() attribute of the value
        # returned here in self._detected_devices. keys() returns a dict_keys object,
        # and that stays in sync with the original dictionary. So if we were to directly
        # return socket_devices, no difference between the old and new state would ever
        # be detected (except the very first time when _detected_devices is an empty
        # dict), because they would be exactly the same.
        return socket_devices.copy()
