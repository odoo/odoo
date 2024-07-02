
from contextlib import suppress
from datetime import datetime, timezone
import logging
import netifaces
from pkg_resources import working_set
from platform import system, uname
from subprocess import check_output
import sys

from odoo import tools
from odoo.addons.hw_drivers.main import drivers, interfaces_instance, iot_devices
from odoo.addons.hw_drivers.tools import helpers
from odoo.service.common import exp_version

Vcgencmd = None
GPIO = None
with suppress(ImportError):
    from vcgencmd import Vcgencmd
    import RPi.GPIO as GPIO

_logger = logging.getLogger(__name__)


class IoTObjectInfoController:
    """Handle the control of the dict info for the IoT objects."""
    @classmethod
    def _iot_info_system(cls) -> dict:
        platform_system = system()
        ssl_certificate = helpers._get_certificate()
        if not isinstance(ssl_certificate, dict):
            ssl_certificate = {
                'get_notAfter': ssl_certificate.get_notAfter(),
                'get_notBefore': ssl_certificate.get_notBefore(),
                'get_subject': ssl_certificate.get_subject(),
                'get_issuer': ssl_certificate.get_issuer(),
            }

        iot_info_system = {
            'platform': {
                'uname': uname(),
            },
            'netifaces': {
                'AF_INET': netifaces.AF_INET,
                'AF_INET6': netifaces.AF_INET6,
                'AF_LINK': netifaces.AF_LINK,
                'interfaces': {
                    interface_name: netifaces.ifaddresses(interface_name)
                    for interface_name in netifaces.interfaces()
                }
            },
            'datetime': datetime.now(timezone.utc).isoformat(),
            'helper checks/getters': {
                'check_certificate': helpers.check_certificate(),
                'get_certificate': ssl_certificate,
                'get_ip': helpers.get_ip(),
                'get_mac_address': helpers.get_mac_address(),
                'get_path_nginx': helpers.get_path_nginx() if platform_system == 'Windows' else '(only for Windows IoT)',
                'get_ssid': helpers.get_ssid() if platform_system == 'Linux' else '(only for Linux IoT-box)',
                'get_odoo_server_url': helpers.get_odoo_server_url(),
                'get_version': helpers.get_version(),
            },
            'python': {
                'version': sys.version,
                'argv': sys.argv,
                'path': sys.path,
                'pip': sorted([f"{i.key}=={i.version}" for i in working_set]),
            },
            'odoo (used by IoT)': {
                'version': exp_version(),
                'config': tools.config.options,
            }
        }
        if platform_system == 'Linux':
            iot_info_system.update({
                'raspberry pi':
                {
                    'board model': GPIO.RPI_INFO.get('TYPE') if GPIO else 'GPIO python library not available',
                    'vcgencmd': cls._iot_info_linux_vcgencmd(),
                    'git': {
                    'commit hash': check_output(
                        ["git", "--work-tree=/home/pi/odoo/", "--git-dir=/home/pi/odoo/.git", "rev-parse", "HEAD"]
                        ).decode('ascii').rstrip(),
                    },
                }
            })
        return iot_info_system

    @staticmethod
    def _iot_info_linux_vcgencmd() -> dict:
        if not Vcgencmd:
            return 'vcgencmd python library not available'
        vcgm = Vcgencmd()
        return {
            'version': vcgm.version(),
            'get_throttled': vcgm.get_throttled(),
            'measure_temp': vcgm.measure_temp(),
            'measure_volts': vcgm.measure_volts('core'),
        }

    @staticmethod
    def _iot_info_interfaces() -> dict:
        return {
            interface_instance.__class__.__name__: interface_instance.get_iot_info()
            for interface_instance in interfaces_instance
        }

    @staticmethod
    def _iot_info_drivers_and_devices() -> dict:
        # The concept of drivers and devices is very close as an IoT device is an instance of a driver
        iot_info_drivers = {
            driver_class.__name__: {
                'connection_type': driver_class.connection_type,
                'devices': []
            }
            for driver_class in drivers
        }
        iot_info_devices = {}
        for iot_device_identifier, iot_device_instance in iot_devices.items():
            iot_device_instance_info = iot_device_instance.get_iot_info()
            iot_device_driver_name = iot_device_instance.__class__.__name__
            iot_info_devices[f"{iot_device_identifier} ({iot_device_driver_name})"] = iot_device_instance_info
            iot_info_drivers[iot_device_driver_name]['devices'].append(iot_device_identifier)
        return iot_info_drivers, iot_info_devices

    @classmethod
    def get_all_iot_info(cls) -> dict:
        """Get the IoT objects information in a dictionary format"""
        driver_iot_info, device_iot_info = cls._iot_info_drivers_and_devices()
        return {
            'system': cls._iot_info_system(),
            'interfaces': cls._iot_info_interfaces(),
            'drivers': driver_iot_info,
            'devices': device_iot_info,
        }
