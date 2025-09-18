"""Modules (also called addons) management."""

import odoo.init  # import first for core setup

from . import db  # used directly during some migration scripts

from . import module
from .module import (
    Manifest,
    adapt_version,
    get_module_path,
    get_modules,
    get_resource_from_path,
    initialize_sys_path,
    get_manifest,
    load_odoo_module,
    load_script,
)

from . import registry
