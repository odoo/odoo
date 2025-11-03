"""Module to manage odoo code upgrades using git"""

import logging
import re
import requests
import subprocess
from odoo.addons.iot_drivers.tools.helpers import (
    odoo_restart,
    toggleable,
)
from odoo.addons.iot_drivers.tools.system import (
    rpi_only,
    IS_TEST,
    git,
    pip,
    path_file,
)

_logger = logging.getLogger(__name__)


def get_last_stable_odoo_version():
    """Get the last stable Odoo version from the server."""
    try:
        # 200 per page, as there already are 86 branches (08/2025)
        response = requests.get(
        'https://api.github.com/repos/odoo/odoo/branches?per_page=200', timeout=5
        )
        response.raise_for_status()
        branches = response.json()
    except requests.exceptions.RequestException:
        _logger.exception("Failed to fetch branches from GitHub")
        return None

    ordered_branches = sorted({
        float(match.group(1))
        for branch in branches
        if (match := re.search(r'(\d+(?:\.\d+)?)', branch['name']))
    }, reverse=True)

    if not ordered_branches:
        return None

    last = ordered_branches[0]
    return f'saas-{last}' if int(last) != last else str(last)


@toggleable
def check_git_branch():
    """Checkout the IoT Box code to the last stable Odoo branch"""
    if IS_TEST:
        return

    try:
        target_branch = get_last_stable_odoo_version()
        if not target_branch:
            _logger.warning("Could not get latest stable Odoo branch, will update following the local branch")
            target_branch = git('symbolic-ref', '-q', '--short', 'HEAD')
            if not git('ls-remote', 'origin', target_branch):
                _logger.warning("'%s' does not exist on remote, assuming 'master'", target_branch)
                target_branch = "master"

        # Repository updates
        shallow_lock = path_file("odoo/.git/shallow.lock")
        if shallow_lock.exists():
            shallow_lock.unlink()  # In case of previous crash/power-off, clean old lockfile
        checkout(target_branch)
        update_requirements()

        update_packages()  # System updates

        _logger.warning("Update completed, restarting...")
        odoo_restart()
    except Exception:
        _logger.exception('An error occurred while trying to update the code with git')


def _ensure_production_remote(local_remote):
    """Ensure that the remote repository is the production one
    (https://github.com/odoo/odoo.git).

    :param local_remote: The name of the remote repository.
    """
    production_remote = "https://github.com/odoo/odoo.git"
    if git('remote', 'get-url', local_remote) != production_remote:
        _logger.info("Setting remote repository to production: %s", production_remote)
        git('remote', 'set-url', local_remote, production_remote)


def checkout(branch, remote=None):
    """Checkout to the given branch of the given git remote.

    :param branch: The name of the branch to check out.
    :param remote: The name of the local git remote to use (usually ``origin`` but computed if not provided).
    """
    _logger.info("Preparing local repository for checkout")
    git('branch', '-m', branch)  # Rename the current branch to the target branch name

    remote = remote or git('config', f'branch.{branch}.remote') or 'origin'
    _ensure_production_remote(remote)

    _logger.info("Checking out %s/%s", remote, branch)
    git('remote', 'set-branches', remote, branch)
    git('fetch', remote, branch, '--depth=1', '--prune')  # refs/remotes to avoid 'unknown revision'
    git('reset', 'FETCH_HEAD', '--hard')

    _logger.info("Cleaning the working directory")
    git('clean', '-dfx')


def update_requirements():
    """Update the Python requirements of the IoT Box, installing the ones
    listed in the requirements.txt file.
    """
    requirements_file = path_file('odoo', 'addons', 'iot_box_image', 'configuration', 'requirements.txt')
    if not requirements_file.exists():
        _logger.info("No requirements file found, not updating.")
        return

    _logger.info("Updating pip requirements")
    pip('-r', requirements_file)


@rpi_only
def update_packages():
    """Update apt packages on the IoT Box, installing the ones listed in
    the packages.txt file.
    Requires ``writable`` context manager.
    """
    packages_file = path_file('odoo', 'addons', 'iot_box_image', 'configuration', 'packages.txt')
    if not packages_file.exists():
        _logger.info("No packages file found, not updating.")
        return

    # update and install packages in the foreground
    commands = (
        "export DEBIAN_FRONTEND=noninteractive && "
        "mount -t proc proc /proc && "
        "apt-get update && "
        f"xargs apt-get -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' install < {packages_file}"
    )
    _logger.warning("Updating apt packages")
    if subprocess.run(
        f'sudo chroot /root_bypass_ramdisks /bin/bash -c "{commands}"', shell=True, check=False
    ).returncode != 0:
        _logger.error("An error occurred while trying to update the packages")
        return

    # upgrade and remove packages in the background
    background_cmd = 'chroot /root_bypass_ramdisks /bin/bash -c "apt-get upgrade -y && apt-get -y autoremove"'
    subprocess.Popen(["sudo", "bash", "-c", background_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
