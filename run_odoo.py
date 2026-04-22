#!/usr/bin/env python3
# Copyright (c) 2026 cloudunify FlexCo
# Author: cloudunify FlexCo <h.enzesberger@cloudunify.at>
# OPL-1
"""
PyCharm run wrapper that reads BTS Odoo Selector config from .idea/bts.xml
and launches odoo-bin with the selected database and modules.

Workaround for PyCharm 2026.1 where BTS plugin macros ($BTSDatabase$, $BTSModules$)
no longer expand in run configurations.

The script auto-detects the project root by scanning sys.path entries
(PyCharm adds content roots when 'Add content roots to PYTHONPATH' is enabled).
Falls back to BTS_PROJECT_DIR env var or current working directory.
"""
import html
import os
import sys
import xml.etree.ElementTree as ET


def _find_bts_xml():
    """Locate .idea/bts.xml by checking (in order):
    1. BTS_PROJECT_DIR env var (if set and not an unexpanded macro)
    2. sys.path entries that are NOT the current working directory
       (PyCharm adds content roots to PYTHONPATH — the project root
       e.g. will be there, distinct from the odoo
       working directory)
    3. Current working directory (last resort)
    """
    cwd = os.path.normcase(os.path.abspath(os.getcwd()))

    # 1. Explicit env var (skip if it looks like an unexpanded $MACRO$)
    project_dir = os.environ.get('BTS_PROJECT_DIR', '')
    if project_dir and '$' not in project_dir:
        candidate = os.path.join(project_dir, '.idea', 'bts.xml')
        if os.path.isfile(candidate):
            return candidate

    # 2. Scan sys.path, skipping cwd (the odoo dir may have its own bts.xml)
    for path_entry in sys.path:
        if not path_entry or not os.path.isdir(path_entry):
            continue
        normalized = os.path.normcase(os.path.abspath(path_entry))
        if normalized == cwd:
            continue
        candidate = os.path.join(path_entry, '.idea', 'bts.xml')
        if os.path.isfile(candidate):
            return candidate

    # 3. Current working directory (last resort)
    candidate = os.path.join(os.getcwd(), '.idea', 'bts.xml')
    if os.path.isfile(candidate):
        return candidate

    return None


def get_bts_config():
    """Read selected database and modules from .idea/bts.xml"""
    bts_file = _find_bts_xml()

    if not bts_file:
        print("ERROR: Could not find .idea/bts.xml", file=sys.stderr)
        print("Ensure 'Add content roots to PYTHONPATH' is checked in the run config,", file=sys.stderr)
        print("or set BTS_PROJECT_DIR to the PyCharm project root.", file=sys.stderr)
        sys.exit(1)

    print(f"BTS: using {bts_file}")

    tree = ET.parse(bts_file)
    root = tree.getroot()

    component = None
    for comp in root.findall('.//component'):
        if comp.get('name') == 'bts':
            component = comp
            break

    if component is None:
        print(f"ERROR: No <component name='bts'> found in {bts_file}", file=sys.stderr)
        sys.exit(1)

    database = None
    modules = []
    all_modules = []

    for option in component.findall('option'):
        name = option.get('name')

        if name == 'selectedDatabase':
            database = option.get('value')

        elif name == 'selectedModuleList':
            raw = option.get('value', '')
            decoded = html.unescape(raw)
            mod_root = ET.fromstring(decoded)
            for item in mod_root.findall('item'):
                mod_name = item.find('name')
                if mod_name is not None and mod_name.text:
                    modules.append(mod_name.text)

        elif name == 'moduleList':
            raw = option.get('value', '')
            decoded = html.unescape(raw)
            mod_root = ET.fromstring(decoded)
            for item in mod_root.findall('item'):
                mod_name = item.find('name')
                if mod_name is not None and mod_name.text:
                    all_modules.append(mod_name.text)

    if not database:
        print(f"ERROR: No selectedDatabase found in {bts_file}", file=sys.stderr)
        sys.exit(1)

    # Fall back to full moduleList when selectedModuleList is empty
    if not modules:
        modules = all_modules

    return database, ','.join(modules)


def main():
    database, modules = get_bts_config()
    print(f"BTS: database={database}, modules={modules}")

    sys.argv = [
        'odoo-bin',
        '-c', f'{database}.conf',
        '-d', database,
        '-i', modules,
        '-u', modules,
    ] + sys.argv[1:]

    import odoo.cli
    odoo.cli.main()


if __name__ == '__main__':
    main()
