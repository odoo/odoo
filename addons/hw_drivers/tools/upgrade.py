"""Module to manage odoo code upgrades using git"""

import logging
import platform
import requests
import subprocess
from functools import wraps
from odoo.addons.hw_drivers.tools.helpers import (
    odoo_restart,
    path_file,
    require_db,
    toggleable,
    writable,
)

_logger = logging.getLogger(__name__)

IS_LINUX = platform.system() == 'Linux'


def linux(function):
    """Decorator to check if the system is Linux before running the function."""
    @wraps(function)
    def wrapper(*args, **kwargs):
        if IS_LINUX:
            return function(*args, **kwargs)
    return wrapper


def git(*args):
    """Run a git command with the given arguments, taking system
    into account.

    :param args: list of arguments to pass to git
    """
    git_executable = 'git' if IS_LINUX else path_file('git', 'cmd', 'git.exe')
    command = [git_executable, f'--work-tree={path_file("odoo")}', f'--git-dir={path_file("odoo", ".git")}', *args]

    p = subprocess.run(command, stdout=subprocess.PIPE, text=True, check=False)
    if p.returncode == 0:
        return p.stdout.strip()
    return None


def pip(*args):
    """Run a pip command with the given arguments, taking system
    into account.

    :param args: list of arguments to pass to pip
    """
    python_executable = [] if IS_LINUX else [path_file('python', 'python.exe'), '-m']
    command = [*python_executable, 'pip', *args]

    if IS_LINUX and args[0] == 'install':
        command.append('--user')
        command.append('--break-system-package')

    p = subprocess.run(command, stdout=subprocess.PIPE, check=False)
    if p.returncode == 0:
        return p.stdout.decode().strip()
    return None


def get_db_branch(server_url):
    """Get the current branch of the database.

    :param server_url: The URL of the connected Odoo database.
    :return: the current branch of the database
    """
    try:
        response = requests.post(server_url + "/web/webclient/version_info", json={}, timeout=5)
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        _logger.exception('Could not reach configured server to get the Odoo version')
        return
    try:
        return response.json()['result']['server_serie'].replace('~', '-')
    except ValueError:
        _logger.exception('Could not load JSON data: Received data is not valid JSON.\nContent:\n%s', response.content)
        return


@toggleable
@require_db
def check_git_branch(server_url=None):
    """Check if the local branch is the same as the connected Odoo DB and
    checkout to match it if needed.

    :param server_url: The URL of the connected Odoo database (provided by decorator).
    """
    db_branch = get_db_branch(server_url)

    try:
        if not git('ls-remote', 'origin', db_branch):
            db_branch = 'master'

        local_branch = git('symbolic-ref', '-q', '--short', 'HEAD')
        _logger.info("IoT Box git branch: %s / Associated Odoo db's git branch: %s", local_branch, db_branch)

        if db_branch != local_branch:
            with writable():
                # Repository updates
                checkout(db_branch)
                update_requirements()

                # System updates
                update_packages()

                # Miscellaneous updates (version migrations)
                misc_migration_updates()
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


def checkout(branch, remote=None, clean=True):
    """Checkout to the given branch of the given git remote.

    :param branch: The name of the branch to check out.
    :param remote: The name of the local git remote to use (usually ``origin`` but computed if not provided).
    :param clean: If True, clean the working directory after checking out.
    """
    _logger.info("Preparing local repository for checkout")
    git('branch', '-m', branch)  # Rename the current branch to the target branch name

    remote = remote or git('config', f'branch.{branch}.remote') or 'origin'
    _ensure_production_remote(remote)

    _logger.warning("Checking out %s/%s", remote, branch)
    git('remote', 'set-branches', remote, branch)
    git('fetch', remote, branch, '--depth=1', '--prune')  # refs/remotes to avoid 'unknown revision'
    git('reset', f'{remote}/{branch}', '--hard')

    if clean:
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

    _logger.warning("Updating pip requirements")
    pip('install', '-r', requirements_file)


@linux
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


@linux
def misc_migration_updates():
    """Run miscellaneous updates after the code update."""
    _logger.warning("Running version migration updates")
    if path_file('odoo', 'addons', 'point_of_sale').exists():
        # TODO: remove this when v18.0 is deprecated (point_of_sale/tools/posbox/ -> iot_box_image/)
        ramdisks_service = "/root_bypass_ramdisks/etc/systemd/system/ramdisks.service"
        subprocess.run(
            ['sudo', 'sed', '-i', "'s|iot_box_image|point_of_sale/tools/posbox|g'", ramdisks_service], check=False
        )

        # TODO: Remove this code when v16 is deprecated
        with open('addons/point_of_sale/tools/posbox/configuration/odoo.conf', 'r+', encoding='utf-8') as f:
            if "server_wide_modules" not in f.read():
                f.write("server_wide_modules=hw_drivers,hw_posbox_homepage,web\n")
