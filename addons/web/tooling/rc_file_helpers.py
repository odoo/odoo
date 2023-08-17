import os
from pathlib import Path
from configparser import RawConfigParser

def get_odoorc_path(): 
    return Path(os.path.abspath(os.path.expanduser('~/.odoorc')) or os.environ.get('ODOO_RC'))

def does_odoorc_exist():
    return os.path.exists(get_odoorc_path())

def get_addon_paths_from_odoorc():
    if not does_odoorc_exist():
        return None
    
    parser = RawConfigParser()
    parser.read(get_odoorc_path())

    if not parser.has_section('options') or not parser.has_option('options', 'addons_path'):
        return None

    addon_paths_string = parser.get('options', 'addons_path')
    paths =  list(map(lambda s: Path(s.strip()), addon_paths_string.split(',')))

    if not paths:
        return None
    
    return paths

def odoo_rc_enterprise_path():
    for path in get_addon_paths_from_odoorc():
        if path.parts[-1] == 'enterprise':
            return path
    return None

# This function is not used yet, it's for later use when we want to add custom addons paths to the jsconfig.
def odoo_rc_custom_addon_paths():
    paths = []
    for path in get_addon_paths_from_odoorc():
        if path.parts[-1] == 'enterprise':
            continue
        if path.parts[-1] == 'addons' and (path.parent / 'odoo-bin').exists():
            continue
        paths.append(path)
    return paths
