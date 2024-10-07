# Part of Odoo. See LICENSE file for full copyright and licensing details.
# ruff: noqa: F401

""" Modules (also called addons) management.

"""

from . import db  # used directly during some migration scripts

from . import module
from .module import (
    adapt_version,
    check_manifest_dependencies,
    get_module_path,
    get_module_resource,  # backward-compatibility
    get_modules,
    get_modules_with_version,
    get_resource_from_path,
    get_resource_path,
    check_resource_path,  # backward-compatibility
    initialize_sys_path,
    get_manifest,
    load_openerp_module,
)

from . import registry
