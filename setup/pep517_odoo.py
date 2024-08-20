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


@contextlib.contextmanager
def _symlink_addons():
    with contextlib.ExitStack() as stack:
        odoo_root = Path(__file__).parent.parent
        root_addons_path = odoo_root / "addons"

        if root_addons_path.is_dir():
            for target_addon_path in root_addons_path.iterdir():
                if not target_addon_path.is_dir():
                    continue
                symlink_path = odoo_root / "odoo" / "addons" / target_addon_path.name
                link_target = root_addons_path / target_addon_path.name
                if not symlink_path.exists() and (link_target / '__manifest__.py').exists():
                    symlink_path.symlink_to(link_target)
                    stack.callback(symlink_path.unlink)
        yield


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
