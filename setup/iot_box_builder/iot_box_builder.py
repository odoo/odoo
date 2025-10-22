#!/usr/bin/env python3
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import argparse
import logging
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path

from fabric import Connection
from invoke import UnexpectedExit

logger = logging.getLogger('iot_box_builder')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

IOTBOX_IMAGE = "iotbox.img"
IOTBOX_VERSION = datetime.now().strftime('%Y.%m.%0d')
RASPI_IMAGE = "2025-10-01-raspios-trixie-armhf-lite.img.xz"
RASPI_IMAGE_URl = f"https://downloads.raspberrypi.com/raspios_lite_armhf/images/raspios_lite_armhf-2025-10-02/{RASPI_IMAGE}"
NGROK_TGZ = "ngrok-v3-stable-linux-arm.tgz"
NGROK_URL = f"https://bin.equinox.io/c/bNyj1mQVY4c/{NGROK_TGZ}"
BUILD_DIR = "/iot_build"
RASPI_PATH = f"{BUILD_DIR}/rpi/images"
BOX_MOUNT_POINT = "/iot_build/mnt"
IOTBOX_PATH = f"{RASPI_PATH}/{IOTBOX_IMAGE}"
SYSTEM_INCREASE_MiB = 2816
SYSTEM_INCREASE_AMOUNT_SECTORS = SYSTEM_INCREASE_MiB * 2048
QEMU_ARM_STATIC = "/usr/bin/qemu-arm-static"
BEFORE_INIT_FILES = Path(__file__).parent / 'overwrite_before_init'
AFTER_INIT_FILES = Path(__file__).parent / 'overwrite_after_init'
BUILD_UTILS_FILES = Path(__file__).parent / 'build_utils'
RPI_ODOO_CLONE_DIR = f"{BUILD_DIR}/overwrite_before_init/home/pi/odoo"


class KvmIotBuilder:
    def __init__(self, args):
        self.args = args
        self.image = args.vm_image
        self.login = args.vm_login
        self.ssh_key = args.vm_ssh_key
        self.odoo_org = 'odoo-dev' if args.dev else 'odoo'

    def timeout(self, signum, frame):
        logger.warning("vm timeout kill (pid: %s)", self.kvm_proc.pid)
        self.kvm_proc.terminate()

    def start(self):
        kvm_cmd = [
            "kvm",
            "-cpu", "host",
            "-nic", "user,model=virtio-net-pci,mac=52:54:00:d6:ad:96,hostfwd=tcp:127.0.0.1:10242-:10242",
            "-m", "8192",
            "-drive", f"if=virtio,file={self.image},snapshot=on",
            "-nographic",
            "-serial", "none",
            "-monitor", "none",
        ]
        logger.info("Starting kvm: %s", " ".join(kvm_cmd))
        self.kvm_proc = subprocess.Popen(kvm_cmd)
        time.sleep(10)
        try:
            signal.alarm(2400)
            signal.signal(signal.SIGALRM, self.timeout)
            self.sync_files()
            self.run()
        finally:
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
            self.kvm_proc.terminate()
            time.sleep(2)

    def sync_files(self):
        identity_options = f' -i {self.ssh_key}' if self.ssh_key else ''
        rsync_cmd = [
            'rsync',
            '-e', 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -p 10242' + identity_options,
            '-aq',
        ]
        subprocess.run(rsync_cmd + [f'{BEFORE_INIT_FILES}', f'{self.login}@127.0.0.1:{BUILD_DIR}'], check=True)
        subprocess.run(rsync_cmd + [f'{AFTER_INIT_FILES}', f'{self.login}@127.0.0.1:{BUILD_DIR}'], check=True)
        subprocess.run(rsync_cmd + [f'{BUILD_UTILS_FILES}', f'{self.login}@127.0.0.1:{BUILD_DIR}'], check=True)

    def run(self):
        connect_kwargs = {"key_filename": self.ssh_key} if self.ssh_key else None
        connection = Connection(host='127.0.0.1', user=self.login, port=10242, connect_timeout=30, connect_kwargs=connect_kwargs)

        connection.put(self.args.ca_pub_key, '/tmp/ca.pub')

        build_steps = [
            # Raspi Image setup
            f'mkdir -p {RASPI_PATH}',
            f'[[ -f {RASPI_PATH}/{RASPI_IMAGE} ]] || wget -nc -q {RASPI_IMAGE_URl} -O {RASPI_PATH}/{RASPI_IMAGE}',
            f'unxz {RASPI_PATH}/{RASPI_IMAGE}',
            f'mv {RASPI_PATH}/{RASPI_IMAGE.removesuffix(".xz")} {IOTBOX_PATH}',
            f'dd if=/dev/zero of={IOTBOX_PATH} bs=512 count={SYSTEM_INCREASE_AMOUNT_SECTORS} status=none conv=notrunc oflag=append',
            f'sudo growpart {IOTBOX_PATH} 2',
            f'sudo losetup -P /dev/loop0 {IOTBOX_PATH}',
            'ls /dev/loop0*',  # this should show the two mapped partitions loop devices
            '[[ -a /dev/loop0p2 ]]',  # Ensure that the second partition was properly mapped
            'sudo e2fsck -fy /dev/loop0p2',
            'sudo resize2fs /dev/loop0p2',
            'sudo e2label /dev/loop0p2 iotboxfs',
            # Odoo Clone
            f'mkdir -p {RPI_ODOO_CLONE_DIR}',
            f'git clone -b {self.args.odoo_branch} --no-local --no-checkout --depth=1 https://github.com/{self.odoo_org}/odoo.git {RPI_ODOO_CLONE_DIR}',
            f'cd {RPI_ODOO_CLONE_DIR} && git config core.sparsecheckout true',
            f'cd {RPI_ODOO_CLONE_DIR} && cat {BUILD_DIR}/build_utils/sparse-checkout >> .git/info/sparse-checkout',
            f'cd {RPI_ODOO_CLONE_DIR} && git read-tree -mu HEAD',
            f'cd {RPI_ODOO_CLONE_DIR} && git remote set-url origin https://github.com/{self.odoo_org}/odoo.git',
            f'mkdir -p {BUILD_DIR}/overwrite_before_init/usr/bin',
            # Ngrok setup
            f'[[ -f {BUILD_DIR}/overwrite_before_init/usr/bin/ngrok ]] || wget -nc -q {NGROK_URL} -O /tmp/ngrok.tgz',
            f'[[ -f {BUILD_DIR}/overwrite_before_init/usr/bin/ngrok ]] || tar xvzf /tmp/ngrok.tgz -C {BUILD_DIR}/overwrite_before_init/usr/bin --remove-files',
            # System partition customization
            f'mkdir -p {BOX_MOUNT_POINT}',
            f'sudo mount -v /dev/loop0p2 {BOX_MOUNT_POINT}',
            f'sudo mount -v /dev/loop0p1 {BOX_MOUNT_POINT}/boot',
            f'sudo cp {QEMU_ARM_STATIC} {BOX_MOUNT_POINT}/usr/bin/',
            f'sudo cp -a {BUILD_DIR}/overwrite_before_init/* {BOX_MOUNT_POINT}',
            f'sudo mkdir -p {BOX_MOUNT_POINT}/var/odoo',
            f'echo {IOTBOX_VERSION} > /tmp/iotbox_version',
            # chroot initialization
            f'sudo chroot {BOX_MOUNT_POINT} /bin/bash -c /etc/init_image.sh',
            f'sudo cp /tmp/ca.pub {BOX_MOUNT_POINT}/etc/ssh/ca.pub',
            f'sudo cp /tmp/iotbox_version {BOX_MOUNT_POINT}/var/odoo/',
            f'sudo cp -a {BUILD_DIR}/overwrite_after_init/* {BOX_MOUNT_POINT}',
            f'sudo chown 1001:1001 -R {BOX_MOUNT_POINT}/home/odoo/',
            f'cd /home/{self.login}',
            'sudo umount -v /dev/loop0p1',
            'sudo umount -v /dev/loop0p2',
            'sudo zerofree -v /dev/loop0p2',
            'sudo losetup -d /dev/loop0',
        ]

        for step in build_steps:
            logger.info('Running: "%s"', step)
            try:
                connection.run(step)
            except UnexpectedExit as e:
                logger.error('Step "%s" failed', step)
                logger.error('Error "%s"', e.result)
                connection.close()
                time.sleep(5)  # let the time for the connection to properly close
                self.kvm_proc.terminate()
        dest_image = f'{self.args.destdir}/iotbox_{IOTBOX_VERSION}.img'
        connection.get(f'{IOTBOX_PATH}', local=dest_image)
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script to build Odoo IotBox Raspberry PI image.")
    parser.add_argument("--vm-ssh-key", "-k", help="Ssh identify file to use for connection to the VM (Defaults to current user identity file)")
    parser.add_argument("--vm-image", "-i", required=True, help="Path to Qemu/KVM image used to build IotBox")
    parser.add_argument("--vm-login", "-l", required=True, help="Login for the VM")
    parser.add_argument("--destdir", "-d", default='/tmp', help="Directory where to put the built image (Defaults to '/tmp')")
    parser.add_argument("--odoo-branch", "-b", default="master", help="Odoo branch to clone (Defaults to master)")
    parser.add_argument("--dev", "-x", action='store_true', help="Clone branch from odoo-dev github")
    parser.add_argument("--ca-pub-key", "-c", required=True, help="CA public key")

    args = parser.parse_args()
    builder = KvmIotBuilder(args)
    builder.start()
