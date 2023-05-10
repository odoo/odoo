import shutil
import subprocess
from pathlib import Path
import os
from rc_file_helpers import odoo_rc_enterprise_path


FILES_TO_COPY = {"_eslintignore" : ".eslintignore", "_eslintrc.json": ".eslintrc.json", "_jsconfig.json": "jsconfig.json", "_package.json": "package.json"}
FILES_TO_REMOVE = [".eslintignore", ".eslintrc.json", "jsconfig.json", "package.json", "package-lock.json", ".prettierignore", ".prettierrc.json"]
DIRS_TO_REMOVE = ["node_modules"]

def get_community_path():
    return Path(__file__).resolve().parents[3]

def get_tooling_path():
    return get_community_path() / "addons/web/tooling"


def set_git_config(directory: Path, tooling: Path):
    """
    Set git configuration `core.hooksPath` in the given directory.
    """
    hooks_path = os.path.relpath((tooling / "hooks").resolve(),directory.resolve())
    subprocess.run(["git", "-C", str(directory), "config", "core.hooksPath", str(hooks_path)], check=True)


def unset_git_config(directory: Path):
    """
    Unset git configuration `core.hooksPath` in the given directory.
    """
    try:
        subprocess.run(["git", "-C", str(directory), "config", "--unset", "core.hooksPath"], check=True)
    except subprocess.CalledProcessError:
        print(f"Failed to unset git config core.hooksPath in {directory}")


def copy_files(source_dir: Path, target_dir: Path):
    for from_name, to_name in FILES_TO_COPY.items():
        shutil.copy2(source_dir / from_name, target_dir / to_name)


def delete_files(directory: Path):
    for file in FILES_TO_REMOVE:
        file_path = directory / file
        if file_path.exists():
            file_path.unlink()


def delete_directories(directory: Path):
    for dir in DIRS_TO_REMOVE:
        dir_path = directory / dir
        if dir_path.exists():
            shutil.rmtree(dir_path)


def prompt_for_enterprise_action(community: Path):
    """
    If the enterprise directory path can be inferred from the odoorc file, prompt
    nothing and return the enterprise directory path and relative path directly.
    Ask the user whether to take action in the enterprise directory as well. 
    Returns the enterprise directory path if the user wants to take action, 
    and None otherwise.
    """
    if  odoo_rc_enterprise_path():
        print("Enterprise path inferred from odoorc file: ", odoo_rc_enterprise_path())
        return odoo_rc_enterprise_path(), os.path.relpath(odoo_rc_enterprise_path(), community)

    enterprise_action = input("Do you want to take action in enterprise too? [y, n]")
    if enterprise_action.lower() != "n":
        enterprise_path_input = input("What is the relative path from community to enterprise ? (../enterprise)")
        enterprise_relative_path = enterprise_path_input or "../enterprise"
        enterprise_dir = (community / enterprise_relative_path).resolve()
        return enterprise_dir, enterprise_relative_path
    return None


def enable_in_dir(directory: Path, tooling: Path, copy_mode=False):
    """
    Enable tooling in the given directory by setting git configuration and copying specified files.
    """
    set_git_config(directory, tooling)
    copy_files(tooling, directory)

    if copy_mode:
            # copy over node_modules and package-lock to avoid double "npm install"
            shutil.copy2(get_community_path() / "package-lock.json", directory / "package-lock.json")
            shutil.copytree(get_community_path() / "node_modules", directory / "node_modules", dirs_exist_ok=True)
    else:
        subprocess.run(["npm", "install"], cwd=directory, check=True)


def disable_in_dir(directory: Path):
    """
    Disable tooling in the given directory by unsetting git configuration and removing specified files and directories.
    """
    unset_git_config(directory)
    delete_files(directory)
    delete_directories(directory)


def refresh_in_dir(directory: Path, tooling: Path):
    """
    Refresh tooling in the given directory by copying specified files.
    """
    copy_files(tooling, directory)


def generate_jsconfig(for_community=False, for_enterprise=False, relative_enterprise_path="../enterprise"):
    """
    Generate _jsconfig.json by calling the external script with the provided parameters.
    """
    # Get the path of the script relative to this file
    script_path = get_tooling_path() / "jsconfig_generator.py"

    # Build the command
    command = ["python", str(script_path)]
    if for_community:
        command.append("--for_community")
    if for_enterprise:
        command.append("--for_enterprise")
    command.extend(["--relative_enterprise_path", relative_enterprise_path])

    # Call the script
    subprocess.run(command, check=True)
