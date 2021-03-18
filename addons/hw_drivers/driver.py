# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from threading import Thread, Event

from odoo.addons.hw_drivers.main import drivers, iot_devices


class DriverMetaClass(type):
    def __new__(cls, clsname, bases, attrs):
        newclass = super(DriverMetaClass, cls).__new__(cls, clsname, bases, attrs)
        if hasattr(newclass, 'priority'):
            newclass.priority += 1
        else:
            newclass.priority = 0
        drivers.append(newclass)
        return newclass


class Driver(Thread, metaclass=DriverMetaClass):
    """
    Hook to register the driver into the drivers list
    """
    connection_type = ''

    def __init__(self, identifier, device):
        super(Driver, self).__init__()
        self.dev = device
        self.device_identifier = identifier
        self.device_name = ''
        self.device_connection = ''
        self.device_type = ''
        self.device_manufacturer = ''
        self.data = {'value': ''}
<<<<<<< HEAD
=======
        self._actions = {}
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
        self._stopped = Event()

    @classmethod
    def supported(cls, device):
        """
        On specific driver override this method to check if device is supported or not
        return True or False
        """
        return False

    def action(self, data):
<<<<<<< HEAD
        """
        On specific driver override this method to make a action with device (take picture, printing,...)
        """
        raise NotImplementedError()
=======
        """Helper function that calls a specific action method on the device.

        :param data: the `_actions` key mapped to the action method we want to call
        :type data: string
        """
        self._actions[data['action']](data)
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729

    def disconnect(self):
        self._stopped.set()
        del iot_devices[self.device_identifier]
