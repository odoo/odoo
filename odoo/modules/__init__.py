# Part of Odoo. See LICENSE file for full copyright and licensing details.
# ruff: noqa: F401

""" Modules (also called addons) management.

"""
import odoo.init  # import first for core setup

from . import db  # used directly during some migration scripts

from . import module
from .module import (
    Manifest,
    adapt_version,
    get_module_path,
    get_modules,
    get_modules_with_version,
    get_resource_from_path,
    initialize_sys_path,
    get_manifest,
    load_openerp_module,
    load_script
)

from . import registry
