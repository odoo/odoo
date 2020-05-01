:banner: banners/iot.jpg

==================
Internet of Things
==================

IoT Drivers allow any Odoo module to communicate in real-time with any device
connected to the IoT Box. Communication with the IoT Box goes both ways, so the
Odoo client can send commands to and receive information from any of the
supported devices. To add support for a device, all we need is a `Driver`.

At each boot, the IoT Box will load all of the Drivers that can
be located on the connected Odoo instance. Each module can contain a
`drivers` directory, whose content will be copied to the IoT Box.

Detect Devices
==============

The `addons/hw_drivers/controllers/driver.py` file contains a Manager that is
in charge of the devices. The Manager maintains a list of connected devices
and associates them with the right Driver.

Supported devices will appear both on the IoT Box Homepage that you can access
through its IP address and in the IoT module of the connected Odoo instance.

Driver
------

Once the Manager has retrieved the list of detected devices, it will loop
through all of the Drivers that have the same connection type and test their
respective `supported` method on all detected devices. If the supported method
of a Driver returns `True`, an instance of this Driver will be created for the
corresponding device.

Creating a new Driver requires:

- Extending `Driver`
- Setting the `connection_type` class attribute.
- Setting the `device_type`, `device_connection` and `device_name` attributes.
- Defining the `supported` method

.. code-block:: python

    from odoo.addons.hw_drivers.controllers.driver import Driver

    class DriverName(Driver):
        connection_type = 'ConnectionType'

        def __init__(self, device):
            super(NewDriver, self).__init__(device)
            self._device_type = 'DeviceType'
            self._device_connection = 'DeviceConnection'
            self._device_name = 'DeviceName'

        @classmethod
        def supported(cls, device):
            ...

Communicate With Devices
========================

Once your new device is detected and appears in the IoT module, the next step
is to communicate with it. Since the box only has a local IP address, it can
only be reached from the same local network. Communication, therefore, needs to
happen on the browser-side, in JavaScript.

The process depends on the direction of the communication:
- From the browser to the box, through `Actions`_
- From the box to the browser, through `Longpolling`_

Both channels are accessed from the same JS object, the `DeviceProxy`, which is
instantiated using the IP of the IoT Box and the device identifier.

.. code-block:: javascript

    var DeviceProxy = require('iot.widgets').DeviceProxy;

    var iot_device = new DeviceProxy({
        iot_ip: iot_ip,
        identifier: device_identifier
    });

Actions
-------

Actions are used to tell a selected device to execute a specific action,
such as taking a picture, printing a receipt, etc.

.. note::
    It must be noted that no “answer” will be sent by the box on this route,
    only the request status. The answer to the action, if any, has to be
    retrieved via the longpolling.

An action can be performed on the DeviceProxy Object.

.. code-block:: javascript

    iot_device.action(data);

In your driver, define an `action` method that will be executed when called
from an Odoo module. It takes the data given during the call as argument.

.. code-block:: python

    def action(self, data):
        ...

Longpolling
-----------

When any module in Odoo wants to read data from a specific device, it creates a
listener identified by the IP/domain of the box and the device identifier and
passes it a callback function to be called every time the device status
changes. The callback is called with the new data as argument.

.. code-block:: javascript

    iot_device.add_listener(this._onValueChange.bind(this));

    _onValueChange: function (result) {
        ...
    }

In the Driver, an event is released by calling the `device_changed` function
from the `event_manager`. All callbacks set on the listener will then be called
with `self.data` as argument.

.. code-block:: python

    from odoo.addons.hw_drivers.controllers.driver import event_manager

    class DriverName(Driver):
        connection_type = 'ConnectionType'

        def methodName(self):
            self.data = {
                'value': 0.5,
                ...
            }
            event_manager.device_changed(self)
