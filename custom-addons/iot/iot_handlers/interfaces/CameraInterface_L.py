from fcntl import ioctl
from glob import glob
import v4l2

from odoo.addons.hw_drivers.interface import Interface


class CameraInterface(Interface):
    connection_type = 'video'

    def get_devices(self):
        camera_devices = {}
        videos = glob('/dev/video*')
        for video in videos:
            with open(video, 'w') as path:
                dev = v4l2.v4l2_capability()
                ioctl(path, v4l2.VIDIOC_QUERYCAP, dev)
                dev.interface = video
                identifier = dev.bus_info.decode('utf-8')
                camera_devices[identifier] = dev
        return camera_devices
