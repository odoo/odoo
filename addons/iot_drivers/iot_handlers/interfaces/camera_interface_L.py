from libcamera import CameraManager
from pathlib import Path

from odoo.addons.iot_drivers.interface import Interface


class CameraInterface(Interface):
    connection_type = 'video'

    @staticmethod
    def get_devices():
        camera_devices = {}
        video_devices = {p.stat().st_rdev: p.name for p in Path('/dev').glob('video*')}
        for camera in CameraManager.singleton().cameras:
            properties = {key.name: value for key, value in camera.properties.items()}
            identifier = camera.id

            camera_devices[identifier] = {
                'name': properties['Model'],
                'identifier': identifier,
                'interface': f"/dev/{video_devices.get(properties['SystemDevices'][0])}",
            }

        return camera_devices
