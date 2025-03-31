#!/usr/bin/env bash

file_exists () {
    [[ -f $1 ]];
}

create_partition () {
    mount -o remount,rw /

    if  [ -f start_upgrade ]
    then
        echo "Error_Upgrade_Already_Started"
        exit 0
    fi

    touch start_upgrade

    echo "Fdisking"

    PARTITION=$(lsblk | awk 'NR==2 {print $1}')
    PARTITION="/dev/${PARTITION}"
    SECTORS_SIZE=$(fdisk -l "${PARTITION}" | awk 'NR==1 {print $7}')

    if [ "${SECTORS_SIZE}" -lt 15583488 ] # self-flash not permited if SD size < 16gb
    then
        rm start_upgrade
        echo "Error_Card_Size"
        exit 0
    fi

    PART_ODOO_ROOT=$(fdisk -l | tail -n 1 | awk '{print $1}')
    START_OF_ODOO_ROOT_PARTITION=$(fdisk -l | tail -n 1 | awk '{print $2}')
    END_OF_ODOO_ROOT_PARTITION=$((START_OF_ODOO_ROOT_PARTITION + 11714061)) # sectors to have a partition of ~5.6Go
    START_OF_UPGRADE_ROOT_PARTITION=$((END_OF_ODOO_ROOT_PARTITION + 1)) # sectors to have a partition of ~7.0Go
    (echo 'p';                                  # print
     echo 'd';                                  # delete partition
     echo '2';                                  #   number 2
     echo 'n';                                  # create new partition
     echo 'p';                                  #   primary
     echo '2';                                  #   number 2
     echo "${START_OF_ODOO_ROOT_PARTITION}";    #   starting at previous offset
     echo "${END_OF_ODOO_ROOT_PARTITION}";      #   ending at ~9.9Go
     echo 'n';                                  # create new partition
     echo 'p';                                  #   primary
     echo '3';                                  #   number 3
     echo "${START_OF_UPGRADE_ROOT_PARTITION}"; #   starting at previous offset
     echo '';                                   #   ending at default (fdisk should propose max) ~7.0Go
     echo 'p';                                  # print
     echo 'w') |fdisk "${PARTITION}"       # write and quit

    PART_RASPIOS_ROOT=$(sudo fdisk -l | tail -n 1 | awk '{print $1}')
    sleep 5

    # Clean partition
    mount -o remount,rw /
    partprobe # apply changes to partitions
    resize2fs "${PART_ODOO_ROOT}"
    mkfs.ext4 -Fv "${PART_RASPIOS_ROOT}" # change file sytstem

    echo "end fdisking"
}

download_raspios () {
    if  [ ! -f *raspios*.img ] ; then
        # download latest Raspios image and check integrity
        LATEST_RASPIOS=$(curl -LIsw %{url_effective} http://downloads.raspberrypi.org/raspios_lite_armhf_latest | tail -n 1)
        wget -c "${LATEST_RASPIOS}"
        RASPIOS=$(echo *raspios*.zip)
        wget -c "${LATEST_RASPIOS}".sha256
        CHECK=$(sha256sum -c "${RASPIOS}".sha256)
        if [ "${CHECK}" != "${RASPIOS}: OK" ]
        then
            # Checksum is not correct so clean and reset self-flashing
            mount -o remount,rw /
            # Clean raspios img
            rm "${RASPIOS}" "${RASPIOS}".sha256

            rm start_upgrade
            echo "Error_Raspios_Download"
            exit 0
        fi
        unzip "${RASPIOS}"
    fi

    echo "end dowloading raspios"
}

copy_raspios () {
    umount -v /boot

    # mapper raspios
    PART_RASPIOS_ROOT=$(fdisk -l | tail -n 1 | awk '{print $1}')
    PART_ODOO_ROOT=$(fdisk -l | tail -n 2 | awk 'NR==1 {print $1}')
    PART_BOOT=$(fdisk -l | tail -n 3 | awk 'NR==1 {print $1}')
    RASPIOS=$(echo *raspios*.img)
    LOOP_RASPIOS=$(kpartx -avs "${RASPIOS}")
    LOOP_RASPIOS_ROOT=$(echo "${LOOP_RASPIOS}" | tail -n 1 | awk '{print $3}')
    LOOP_RASPIOS_ROOT="/dev/mapper/${LOOP_RASPIOS_ROOT}"
    LOOP_BOOT=$(echo "${LOOP_RASPIOS}" | tail -n 2 | awk 'NR==1 {print $3}')
    LOOP_BOOT="/dev/mapper/${LOOP_BOOT}"

    mount -o remount,rw /
    # copy raspios
    dd if="${LOOP_RASPIOS_ROOT}" of="${PART_RASPIOS_ROOT}" bs=4M status=progress
    e2fsck -fv "${PART_RASPIOS_ROOT}" # resize2fs requires clean fs

    # Modify startup
    mkdir -v raspios
    mount -v "${PART_RASPIOS_ROOT}" raspios
    resize2fs "${PART_RASPIOS_ROOT}"
    chroot raspios/ /bin/bash -c "sudo apt-get -y update"
    chroot raspios/ /bin/bash -c "sudo apt-get -y install kpartx"
    PATH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cp -v "${PATH_DIR}"/upgrade.sh raspios/home/pi/
    NBR_LIGNE=$(sed -n -e '$=' raspios/etc/rc.local)
    sed -ie "${NBR_LIGNE}"'i\. /home/pi/upgrade.sh; copy_iot' raspios/etc/rc.local
    cp -v /etc/fstab raspios/etc/fstab
    sed -ie "s/$(echo ${PART_ODOO_ROOT} | sed -e 's/\//\\\//g')/$(echo ${PART_RASPIOS_ROOT} | sed -e 's/\//\\\//g')/g" raspios/etc/fstab
    mkdir raspios/home/pi/config
    find /home/pi -maxdepth 1 -type f ! -name ".*" -exec cp {} raspios/home/pi/config/ \;

    # download latest IoT Box image and check integrity
    wget -c 'https://nightly.odoo.com/master/iotbox/iotbox-latest.zip' -O raspios/iotbox-latest.zip
    wget -c 'https://nightly.odoo.com/master/iotbox/SHA1SUMS.txt' -O raspios/SHA1SUMS.txt
    cd raspios/
    CHECK=$(sha1sum -c --ignore-missing SHA1SUMS.txt)
    cd ..

    umount -v raspios
    if [ "${CHECK}" != "iotbox-latest.zip: OK" ]
    then
        # Checksum is not correct so clean and reset self-flashing
        rm start_upgrade
        echo "Error_Iotbox_Download"
        exit 0
    fi

    # copy boot
    mkfs.ext4 -Fv "${PART_BOOT}" # format /boot file sytstem
    e2fsck -fv "${PART_BOOT}" # clean /boot fs
    dd if="${LOOP_BOOT}" of="${PART_BOOT}" bs=4M status=progress

    # Modify boot file
    mkdir -v boot
    mount -v "${PART_BOOT}" boot
    PART_IOT_BOOT_ID=$(grep -oP '(?<=root=).*(?=rootfstype)' boot/cmdline.txt)
    sed -ie "s/$(echo ${PART_IOT_BOOT_ID} | sed -e 's/\//\\\//g')/$(echo ${PART_RASPIOS_ROOT} | sed -e 's/\//\\\//g')/g" boot/cmdline.txt
    umount -v boot

    kpartx -dv "${RASPIOS}"
    rm -v "${RASPIOS}"

    reboot
}

copy_iot () {
    mount -o remount,rw /

    PART_IOTBOX_ROOT=$(fdisk -l | tail -n 2 | awk 'NR==1 {print $1}')
    PART_BOOT=$(fdisk -l | tail -n 3 | awk 'NR==1 {print $1}')

    # unzip latest IoT Box image
    unzip iotbox-latest.zip
    rm -v iotbox-latest.zip
    IOTBOX=$(echo *iotbox*.img)

    # mapper IoTBox
    LOOP_IOTBOX=$(kpartx -avs "${IOTBOX}")
    LOOP_IOTBOX_ROOT=$(echo "${LOOP_IOTBOX}" | tail -n 1 | awk '{print $3}')
    LOOP_IOTBOX_ROOT="/dev/mapper/${LOOP_IOTBOX_ROOT}"
    LOOP_BOOT=$(echo "${LOOP_IOTBOX}" | tail -n 2 | awk 'NR==1 {print $3}')
    LOOP_BOOT="/dev/mapper/${LOOP_BOOT}"

    umount -v /boot
    sleep 5

    echo "----------------------------------"
    echo "Flash in progress - Please wait..."
    echo "----------------------------------"
    # copy new IoT Box
    dd if="${LOOP_IOTBOX_ROOT}" of="${PART_IOTBOX_ROOT}" bs=4M status=progress
    # copy boot of new IoT Box
    dd if="${LOOP_BOOT}" of="${PART_BOOT}" bs=4M status=progress

    mount -v "${PART_BOOT}" /boot

    # Modify boot file
    PART_BOOT_ID=$(grep -oP '(?<=root=).*(?=rootfstype)' /boot/cmdline.txt)
    sed -ie "s/$(echo ${PART_BOOT_ID} | sed -e 's/\//\\\//g')/$(echo ${PART_IOTBOX_ROOT} | sed -e 's/\//\\\//g')/g" /boot/cmdline.txt
    sed -i 's| init=/usr/lib/raspi-config/init_resize.sh||' /boot/cmdline.txt

    # Modify startup
    mkdir -v odoo
    mount -v "${PART_IOTBOX_ROOT}" odoo
    cp -v /home/pi/upgrade.sh odoo/home/pi/
    NBR_LIGNE=$(sed -n -e '$=' odoo/etc/rc.local)
    sed -ie "${NBR_LIGNE}"'i\. /home/pi/upgrade.sh; clean_local' odoo/etc/rc.local
    find /home/pi/config -maxdepth 1 -type f ! -name ".*" -exec cp {} odoo/home/pi/ \;

    reboot
}

cleanup () {
    # clean partitions
    PART_RASPIOS_ROOT=$(fdisk -l | tail -n 1 | awk '{print $1}')
    mkfs.ext4 -Fv "${PART_RASPIOS_ROOT}" # format file sytstem
    wipefs -a "${PART_RASPIOS_ROOT}"

    PARTITION=$(echo "${PART_RASPIOS_ROOT}" | sed 's/..$//')

    (echo 'p';                                  # print
     echo 'd';                                  # delete partition
     echo '3';                                  #   number 3
     echo 'p';                                  # print
     echo 'w') |fdisk "${PARTITION}"            # write and quit

    echo "end cleanup"
}

clean_local () {
    mount -o remount,rw /
    mount -o remount,rw /root_bypass_ramdisks/
    cleanup
    NBR_LIGNE=$(sed -n -e '$=' /root_bypass_ramdisks/etc/rc.local)
    DEL_LIGNE=$((NBR_LIGNE - 1))
    sed -i "${DEL_LIGNE}"'d' /root_bypass_ramdisks/etc/rc.local

    rm /home/pi/upgrade.sh

    mount -o remount,ro /
    mount -o remount,ro /root_bypass_ramdisks/
}
