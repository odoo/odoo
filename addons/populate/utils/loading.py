import importlib
import logging
import re
from pathlib import Path

from odoo.modules import get_module_path
from odoo.tools import convert_file, topological_sort

_loading_logger = logging.getLogger('odoo.addons.populate')

POPULATE_FOLDER_NAME = 'populate'
MODULE_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def load_populate(env):
    """
    Scan installed modules for 'populate' folders and load data files.
    If it's a valid python module, import it.

    :param env: Environment used to inspect installed modules and load XML files.
    """
    _loading_logger.info("Populate module was installed or upgraded - scanning modules for populate data...")

    modules_installed = env['ir.module.module'].search([('state', '=', 'installed')])

    modules_deps = {}
    populate_folder_by_module_name = {}

    for module in modules_installed:
        module_path = get_module_path(module.name)
        if not module_path:
            continue

        populate_folder = Path(module_path) / POPULATE_FOLDER_NAME
        if not populate_folder.is_dir():
            continue

        modules_deps[module.name] = module.dependencies_id.mapped('name')
        populate_folder_by_module_name[module.name] = populate_folder

    for module_name in topological_sort(modules_deps):
        populate_folder = populate_folder_by_module_name[module_name]

        # If it's a valid python module, import it.
        # Allows for modules to define custom generators.
        if (populate_folder / '__init__.py').exists():
            if MODULE_NAME_RE.fullmatch(module_name):
                populate_module = f'odoo.addons.{module_name}.{POPULATE_FOLDER_NAME}'
                _loading_logger.info("loading %s", populate_module)
                importlib.import_module(populate_module)
            else:
                _loading_logger.warning("skipping invalid populate module name %r", module_name)

        data_files = sorted(
            file for file in populate_folder.iterdir()
            if file.is_file() and file.suffix.lower() == '.xml'
        )

        for data_file in data_files:
            relative_path = Path(f"{POPULATE_FOLDER_NAME}/{data_file.name}")
            _loading_logger.info("loading %s", Path(f"{module_name}/{relative_path}"))
            convert_file(
                env,
                module_name,
                filename=str(relative_path),
                idref=None,
                mode='init',
                noupdate=False,
            )
