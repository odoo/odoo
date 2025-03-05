#!/bin/sh

file_exists() {
    [ -f "$1" ];
}

change_boot_priority() {
    FROM="$1"
    TO="$2"
    BOOT=${3:-"/boot"}

    echo "Changing boot priority from $FROM to $TO"
    PARTUUID_CURRENT=$(blkid -s PARTUUID -o value $FROM)
    PARTUUID_NEW=$(blkid -s PARTUUID -o value $TO)
    sed -i "s/${PARTUUID_CURRENT}/${PARTUUID_NEW}/" "${BOOT}/cmdline.txt"
}

prepare_upgrade () {
    # This method is called from the IoT Box Homepage to
    # prepare the upgrade process, then reboot on the recovery
    # partition to execute the upgrade method

    # Download latest IoT Box image
    set -- *iotbox*.zip # set the first match to $1
    if ! file_exists "$1"; then
        wget "https://nightly.odoo.com/master/iotbox/iotbox-latest.zip"
    fi
    IMAGE=$(echo *iotbox*.img)
    echo "Using image ${IMAGE}"

    # Mount the recovery partition and copy this script and odoo.conf file to it
    echo "Sending script and configuration to the recovery partition"
    mount /dev/mmcblk0p2 /mnt
    # copy the current script and `odoo.conf` to the recovery partition
    cp $0 /home/pi/odoo.conf /mnt

    # Unmount the recovery partition
    umount /mnt

    # Set the recovery partition as the partition to boot from
    echo "Setting boot priority to recovery partition"
    change_boot_priority "/dev/mmcblk0p3" "/dev/mmcblk0p2"

    reboot
}

upgrade () {
    # This method is called from the recovery partition to
    # upgrade the IoT Box system
    # Current FS: | boot | recovery | system |

    # Tiny Core `/root` partition is mounted as readonly,
    # so we need to mount it as read-write
    mount -o remount,rw /root

    # Shrink system partition to free space to create a storage partition to store the IoT Box image
    # To do so: shrink the `iotboxfs` partition filesystem, then the `iotboxfs` partition itself.
    echo "Shrinking system partition"
    e2fsck -fy /dev/mmcblk0p3 # Check and fix the file system before resizing
    resize2fs /dev/mmcblk0p3 13G # Set a lower size to avoid issues with `parted` (https://askubuntu.com/q/1293505)
    # Avoid auto exit when using `-s` while shrinking (see: https://unix.stackexchange.com/a/780563)
    echo -e "resizepart 3 15G\nyes\nquit" | parted /dev/mmcblk0 ---pretend-input-tty
    resize2fs /dev/mmcblk0p3 # extend filesystem to the limits of resized partition (https://askubuntu.com/q/1293505)

    # Create another partition to store the IoT Box image
    echo "Creating partition to store the IoT Box image"
    parted -s /dev/mmcblk0 mkpart primary ext4 15G 100% # use remaining space

    # As Tiny Core busybox doesn't contain `mkfs.ext4` or `mkfs` to create an ext4 filesystem,
    # we force the creation of the filesystem by copying the recovery partition (very small)
    # to the storage partition, then check-fix and resize the filesystem
    # We also increase the block size (4M) to speed up the process.
    dd if=/dev/mmcblk0p2 of=/dev/mmcblk0p4 bs=4M # status=progress unavailable in busybox
    e2fsck -fy /dev/mmcblk0p4
    resize2fs /dev/mmcblk0p4

    # Current FS: | boot | recovery | system | image storage |

    # Mount system and storage partitions to copy the IoT Box image
    mkdir -p /tmp/iotboxfs /tmp/storagefs
    mount /dev/mmcblk0p3 /tmp/iotboxfs
    mount -o noatime /dev/mmcblk0p4 /tmp/storagefs

    echo "Moving image to new storage partition"
    IMAGE="/tmp/storagefs/iotbox.zip"
#    mv "/tmp/iotboxfs/home/pi/odoo/addons/iot_box_image/configuration/iotbox-latest.zip" "$IMAGE"
    dd if=/tmp/iotboxfs/home/pi/odoo/addons/iot_box_image/configuration/iotbox-latest.zip of=/tmp/storagefs/iotbox.zip bs=1G
    echo "Unzipping image"
    ionice -c 2 -n 0 unzip -q "$IMAGE" -d /tmp/storagefs
    IMAGE="/tmp/storagefs/iotbox_beta.img"

    # Map the IoT Box image to loop devices
    losetup -Pf ${IMAGE}
    LOOP_IMAGE_BOOT="/dev/loop0p1"
    LOOP_IMAGE_ROOT="/dev/loop0p3"
    echo "Loop devices: ${LOOP_IMAGE_BOOT} ${LOOP_IMAGE_ROOT}"

    # Copy the boot partition (probably not necessary, but in case raspberry pi foundation updates the boot partition)
    echo "Copying boot partition"
    dd if="${LOOP_IMAGE_BOOT}" of=/dev/mmcblk0p1 bs=1M

    # Copy the system partition
    echo "Copying system partition"
    dd if="${LOOP_IMAGE_ROOT}" of=/dev/mmcblk0p3 bs=2G
    mv odoo.conf /mnt/iotboxfs/home/pi/ # Add the saved `odoo.conf` to the new system

    # Cleanup
    umount /tmp/iotboxfs /tmp/storagefs # Unmount the partitions
    losetup -d /dev/loop0 # Unmap the loop device
    parted -s /dev/mmcblk0 rm 4 # remove the storage partition

    # Set the recovery partition as the partition to boot from
    echo "Setting boot priority to system partition"
    mount /dev/mmcblk0p1 /tmp
    change_boot_priority "/dev/mmcblk0p2" "/dev/mmcblk0p3" "/tmp"
    umount /tmp

    # Reboot the device (`-f` is required to exit `initramfs` system)
    reboot -f
}

# Execute based on the argument
if [ "$#" -eq 1 ] && [ "$1" = "--prepare-upgrade" ]; then
    prepare_upgrade
elif [ "$#" -eq 1 ] && [ "$1" = "--upgrade" ]; then
    upgrade
else
    echo "Invalid arguments or no arguments provided"
    exit 1
fi
