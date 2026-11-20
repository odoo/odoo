"""Specialized PEP 517 build backend for Odoo.

It is based on setuptools, and extends it to

- symlink all addons into odoo/addons before building, so setuptools discovers them
  automatically, and
- enforce the 'compat' editable mode, because the default mode for flat layout
  is not compatible with the Odoo addon import system.
"""
import contextlib
from pathlib import Path

from setuptools import build_meta
from setuptools.build_meta import *  # noqa: F403


@contextlib.contextmanager
def _symlink_addons():
    symlinks = []
    try:
        target_addons_path = Path("addons")
        addons_path = Path("odoo", "addons")
        link_target = Path("..", "..", "addons")
        if target_addons_path.is_dir():
            for target_addon_path in target_addons_path.iterdir():
                if not target_addon_path.is_dir():
                    continue
                addon_path = addons_path / target_addon_path.name
                if not addon_path.is_symlink():
                    addon_path.symlink_to(
                        link_target / target_addon_path.name, target_is_directory=True
                    )
                    symlinks.append(addon_path)
        yield
    finally:
        for symlink in symlinks:
            symlink.unlink()


def build_sdist(*args, **kwargs):
    with _symlink_addons():
        return build_meta.build_sdist(*args, **kwargs)


def build_wheel(*args, **kwargs):
    with _symlink_addons():
        return build_meta.build_wheel(*args, **kwargs)


if hasattr(build_meta, "build_editable"):

    def build_editable(
        wheel_directory, config_settings=None, metadata_directory=None, **kwargs
    ):
        if config_settings is None:
            config_settings = {}
        # Use setuptools's compat editable mode, because the default mode for
        # flat layout projects is not compatible with pkgutil.extend_path,
        # and the strict mode is too strict for the Odoo development workflow
        # where new files are added frequently. This is currently being discussed
        # by the setuptools maintainers.
        config_settings["editable-mode"] = "compat"
        return build_meta.build_editable(
            wheel_directory, config_settings, metadata_directory, **kwargs
        )
