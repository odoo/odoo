from libcamera import CameraManager
from pathlib import Path

from odoo.addons.hw_drivers.interface import Interface


class CameraInterface(Interface):
    connection_type = 'video'

    @staticmethod
    def get_devices():
        camera_devices = {}
        video_devices = {p.stat().st_rdev: p.name for p in Path('/dev').glob('video*')}
        for camera in CameraManager.singleton().cameras:
            properties = {key.name: value for key, value in camera.properties.items()}
            old_identifier = f"camera-{properties['Location']}"
            identifier = camera.id

            camera_devices[identifier] = {
                'name': properties['Model'],
                'identifier': identifier,
                'interface': f"/dev/{video_devices.get(properties['SystemDevices'][0])}",
            }

            # TODO: Remove this in master forward-port
            # The old identifier would always evaluate to 'camera-2', meaning multiple
            # cameras could not be used. We have fixed this by using a different identifier,
            # but to avoid losing client's backend configuration we will still send the
            # 'camera-2' device in stable.
            camera_devices[old_identifier] = {**camera_devices[identifier]}
            camera_devices[old_identifier]['identifier'] = old_identifier
            camera_devices[old_identifier]['name'] += ' (LEGACY, do not use)'

        return camera_devices
